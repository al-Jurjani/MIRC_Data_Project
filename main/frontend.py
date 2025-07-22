# Bismillah
# Starting project on 07-01-1447 - 03-07-2025

# Bismillah
# Starting project on 07-01-1447 - 03-07-2025

import sys
import shutil
import os
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFileDialog, QProgressBar, QMessageBox, QTabWidget,
    QLineEdit, QTableWidget, QTableWidgetItem, QListWidget, QListWidgetItem,
    QSplitter, QHeaderView
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QMimeData
from PyQt5.QtGui import QDragEnterEvent, QDropEvent, QPixmap

from pipeline import process_video
from query_backend import search_similar
from chat_handler_service import rerank_top_matches
from db_browser_backend import fetch_all_entries, get_file_path

class VideoProcessingThread(QThread):
    progress_update = pyqtSignal(int)
    finished = pyqtSignal(str, str)  # guid, video_path
    failed = pyqtSignal(str, str)    # error_msg, video_path
    all_finished = pyqtSignal()
    video_started = pyqtSignal(str)  # video_path

    def __init__(self, video_paths, base_dir):
        super().__init__()
        self.video_paths = video_paths
        self.base_dir = base_dir

    def run(self):
        total_videos = len(self.video_paths)
        for i, video_path in enumerate(self.video_paths):
            try:
                self.video_started.emit(video_path)
                
                # Calculate base progress for this video
                base_progress = int((i / total_videos) * 100)
                
                # Create a progress callback that handles the pipeline's progress updates
                # The pipeline calls progress_callback.emit(value), so we need to create an object with emit method
                class ProgressCallback:
                    def __init__(self, thread_signal, base_prog, total_vids):
                        self.thread_signal = thread_signal
                        self.base_progress = base_prog
                        self.total_videos = total_vids
                    
                    def emit(self, progress):
                        # Individual video progress (0-100) mapped to overall progress
                        video_progress = int((progress / 100) * (100 / total_videos))
                        overall_progress = self.base_progress + video_progress
                        self.thread_signal.emit(min(overall_progress, 100))
                
                progress_callback = ProgressCallback(self.progress_update, base_progress, total_videos)
                
                # Set initial progress for this video
                self.progress_update.emit(base_progress)
                
                # Process the video - pass the progress callback directly
                guid = process_video(video_path, self.base_dir, progress_callback)
                
                # Ensure progress shows completion for this video
                completion_progress = int(((i + 1) / total_videos) * 100)
                self.progress_update.emit(completion_progress)
                
                self.finished.emit(guid, video_path)
                
            except Exception as e:
                self.failed.emit(str(e), video_path)
        
        self.all_finished.emit()

class VideoUploadTab(QWidget):
    def __init__(self):
        super().__init__()
        self.setAcceptDrops(True)
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout()

        # Title
        title_label = QLabel("Upload MP4 Videos for Processing")
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("font-size: 16px; font-weight: bold; margin: 10px;")

        # Instructions
        instructions = QLabel("Drag and drop MP4 files here or click 'Add Videos' to select files")
        instructions.setAlignment(Qt.AlignCenter)
        instructions.setStyleSheet("color: #666; margin: 5px;")

        # Drop zone (list of selected files)
        self.file_list = QListWidget()
        self.file_list.setMinimumHeight(200)
        self.file_list.setStyleSheet("""
            QListWidget {
                border: 2px dashed #ccc;
                border-radius: 8px;
                background-color: #f9f9f9;
                padding: 10px;
            }
            QListWidget::item {
                padding: 5px;
                margin: 2px;
                background-color: white;
                border: 1px solid #ddd;
                border-radius: 4px;
            }
        """)

        # Buttons
        button_layout = QHBoxLayout()
        self.add_btn = QPushButton("Add Videos")
        self.add_btn.clicked.connect(self.add_videos)
        
        self.clear_btn = QPushButton("Clear All")
        self.clear_btn.clicked.connect(self.clear_files)
        
        self.process_btn = QPushButton("Process Videos")
        self.process_btn.clicked.connect(self.process_videos)
        self.process_btn.setEnabled(False)

        button_layout.addWidget(self.add_btn)
        button_layout.addWidget(self.clear_btn)
        button_layout.addWidget(self.process_btn)

        # Progress bar
        self.progress = QProgressBar()
        self.progress.setValue(0)

        # Status label
        self.status_label = QLabel("Ready")
        self.status_label.setAlignment(Qt.AlignCenter)

        # Results area
        self.results_list = QListWidget()
        self.results_list.setMaximumHeight(100)

        layout.addWidget(title_label)
        layout.addWidget(instructions)
        layout.addWidget(self.file_list)
        layout.addLayout(button_layout)
        layout.addWidget(self.progress)
        layout.addWidget(self.status_label)
        layout.addWidget(QLabel("Processing Results:"))
        layout.addWidget(self.results_list)

        self.setLayout(layout)

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.accept()
        else:
            event.ignore()

    def dropEvent(self, event: QDropEvent):
        files = [url.toLocalFile() for url in event.mimeData().urls()]
        mp4_files = [f for f in files if f.lower().endswith('.mp4')]
        
        if mp4_files:
            self.add_files_to_list(mp4_files)
        else:
            QMessageBox.warning(self, "Warning", "Please drop only MP4 files.")

    def add_videos(self):
        file_paths, _ = QFileDialog.getOpenFileNames(
            self, "Select MP4 Videos", "", "Video Files (*.mp4)"
        )
        if file_paths:
            self.add_files_to_list(file_paths)

    def add_files_to_list(self, file_paths):
        for file_path in file_paths:
            # Check if file is already in the list
            existing_items = [self.file_list.item(i).text() for i in range(self.file_list.count())]
            if file_path not in existing_items:
                item = QListWidgetItem(file_path)
                self.file_list.addItem(item)
        
        self.process_btn.setEnabled(self.file_list.count() > 0)

    def clear_files(self):
        self.file_list.clear()
        self.results_list.clear()
        self.process_btn.setEnabled(False)
        self.progress.setValue(0)
        self.status_label.setText("Ready")

    def process_videos(self):
        if self.file_list.count() == 0:
            QMessageBox.warning(self, "Warning", "Please add some videos first.")
            return

        video_paths = [self.file_list.item(i).text() for i in range(self.file_list.count())]
        base_dir = os.path.abspath("processed_videos")

        self.process_btn.setEnabled(False)
        self.add_btn.setEnabled(False)
        self.clear_btn.setEnabled(False)
        self.progress.setValue(0)
        self.status_label.setText(f"Starting processing of {len(video_paths)} videos...")
        self.results_list.clear()

        self.thread = VideoProcessingThread(video_paths, base_dir)
        self.thread.progress_update.connect(self.progress.setValue)
        self.thread.finished.connect(self.on_video_success)
        self.thread.failed.connect(self.on_video_failure)
        self.thread.all_finished.connect(self.on_all_finished)
        self.thread.video_started.connect(self.on_video_started)
        self.thread.start()

    def on_video_started(self, video_path):
        filename = os.path.basename(video_path)
        self.status_label.setText(f"Processing: {filename}")

    def on_video_success(self, guid, video_path):
        filename = os.path.basename(video_path)
        self.results_list.addItem(f"✓ {filename} - GUID: {guid}")
        self.status_label.setText(f"Completed: {filename}")

    def on_video_failure(self, error_msg, video_path):
        filename = os.path.basename(video_path)
        self.results_list.addItem(f"✗ {filename} - Error: {error_msg}")
        self.status_label.setText(f"Failed: {filename}")

    def on_all_finished(self):
        self.process_btn.setEnabled(True)
        self.add_btn.setEnabled(True)
        self.clear_btn.setEnabled(True)
        self.progress.setValue(100)
        self.status_label.setText("All videos processed!")
        QMessageBox.information(self, "Complete", "All videos have been processed!")

class QueryTab(QWidget):
    def __init__(self):
        super().__init__()
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout()

        # Title
        title_label = QLabel("Query Video Knowledge Base")
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("font-size: 16px; font-weight: bold; margin: 10px;")

        # Query input
        query_layout = QHBoxLayout()
        self.query_input = QLineEdit()
        self.query_input.setPlaceholderText("Enter your question here...")
        self.query_input.returnPressed.connect(self.run_query)

        self.search_btn = QPushButton("Search")
        self.search_btn.clicked.connect(self.run_query)

        query_layout.addWidget(QLabel("Question:"))
        query_layout.addWidget(self.query_input)
        query_layout.addWidget(self.search_btn)

        # Results table
        self.results_table = QTableWidget()
        self.results_table.setColumnCount(4)
        self.results_table.setHorizontalHeaderLabels([
            "Score", "Title", "Video Path", "Best Match"
        ])

        layout.addWidget(title_label)
        layout.addLayout(query_layout)
        layout.addWidget(QLabel("Search Results:"))
        layout.addWidget(self.results_table)

        self.setLayout(layout)

    def run_query(self):
        query = self.query_input.text().strip()
        if not query:
            QMessageBox.warning(self, "Warning", "Please enter a query.")
            return

        self.results_table.setRowCount(0)

        try:
            matches = search_similar(query, top_k=10)
            ranked_results = rerank_top_matches(query, matches)

            self.results_table.setRowCount(len(ranked_results))
            for row, item in enumerate(ranked_results):
                self.results_table.setItem(row, 0, QTableWidgetItem(f"{item['score']:.2f}"))
                self.results_table.setItem(row, 1, QTableWidgetItem(item['title']))
                self.results_table.setItem(row, 2, QTableWidgetItem(item['video_path']))
                self.results_table.setItem(row, 3, QTableWidgetItem(item['sentence']))

            self.results_table.resizeRowsToContents()
            self.results_table.resizeColumnsToContents()

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Search failed:\n{str(e)}")



# def create_database_browser_tab(self):
#     widget = QWidget()
#     layout = QVBoxLayout()

#     # Search bar
#     search_bar = QLineEdit()
#     search_bar.setPlaceholderText("Search by GUID or Title")
#     layout.addWidget(search_bar)

#     # Table
#     table = QTableWidget()
#     table.setColumnCount(6)
#     table.setHorizontalHeaderLabels([
#         "GUID", "Title", "Video", "Transcript", "Translation", "Summary"
#     ])
#     table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
#     layout.addWidget(table)

#     def populate_table(data):
#         table.setRowCount(len(data))
#         for row, item in enumerate(data):
#             table.setItem(row, 0, QTableWidgetItem(item["guid"]))
#             table.setItem(row, 1, QTableWidgetItem(item["title"]))

#             for col_idx, key in enumerate(["video_path", "transcript_path", "translation_path", "summary_path"], start=2):
#                 button = QPushButton("Download")
#                 path = item[key]
#                 button.clicked.connect(lambda _, p=path: self.download_file(p))
#                 table.setCellWidget(row, col_idx, button)

#     def filter_table():
#         term = search_bar.text().lower()
#         filtered = [item for item in all_data if term in item["guid"].lower() or term in item["title"].lower()]
#         populate_table(filtered)

#     search_bar.textChanged.connect(filter_table)

#     all_data = fetch_all_entries()
#     populate_table(all_data)

#     widget.setLayout(layout)
#     return widget

# For Third tab of Database Browser
class DatabaseBrowserTab(QWidget):
    def __init__(self):
        super().__init__()
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        # --- Search Bar ---
        search_layout = QHBoxLayout()
        self.search_bar = QLineEdit()
        self.search_bar.setPlaceholderText("Search by GUID or Title...")
        search_button = QPushButton("Search")
        search_button.clicked.connect(self.perform_search)
        search_layout.addWidget(self.search_bar)
        search_layout.addWidget(search_button)
        layout.addLayout(search_layout)

        # --- Table Display ---
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(["GUID", "Title", "Transcript", "Translation", "Summary", "Video"])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.table)

        self.setLayout(layout)
        self.load_data()

    def load_data(self, filter_text=""):
        # from db_browser_backend import get_all_records
        # records = get_all_records()
        records = fetch_all_entries()

        if filter_text:
            filter_text = filter_text.lower()
            records = [r for r in records if filter_text in r["guid"].lower() or filter_text in r["title"].lower()]

        self.table.setRowCount(len(records))
        for row, item in enumerate(records):
            self.table.setItem(row, 0, QTableWidgetItem(item["guid"]))
            self.table.setItem(row, 1, QTableWidgetItem(item["title"]))

            for i, key in enumerate(["transcript_path", "translation_path", "summary_path", "video_path"], start=2):
                button = QPushButton("Download")
                button.clicked.connect(lambda _, path=item[key]: self.download_file(path))
                self.table.setCellWidget(row, i, button)

    def perform_search(self):
        query = self.search_bar.text()
        self.load_data(query)

    def download_file(self, path):
        import shutil
        from PyQt5.QtWidgets import QFileDialog, QMessageBox
        if not os.path.exists(path):
            QMessageBox.critical(self, "File Not Found", f"Path does not exist:\n{path}")
            return
        save_path, _ = QFileDialog.getSaveFileName(self, "Save File", os.path.basename(path))
        if save_path:
            try:
                shutil.copy(path, save_path)
                QMessageBox.information(self, "Success", f"Saved to {save_path}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to save:\n{str(e)}")


# Helper function to download files
def download_file(self, source_path):
    if not os.path.exists(source_path):
        QMessageBox.critical(self, "Error", f"File not found:\n{source_path}")
        return

    save_path, _ = QFileDialog.getSaveFileName(self, "Save File As", os.path.basename(source_path))
    if save_path:
        try:
            shutil.copy(source_path, save_path)
            QMessageBox.information(self, "Success", "File downloaded successfully!")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to download file:\n{e}")

class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Video Processing & Query System")
        self.resize(800, 600)
        self.setup_ui()

    def create_header(self):
        """Create the logo and title header that stays visible across all tabs"""
        header_widget = QWidget()
        header_layout = QVBoxLayout()
        header_layout.setContentsMargins(20, 10, 20, 10)
        
        # Logo
        logo_label = QLabel()
        logo_label.setAlignment(Qt.AlignCenter)
        
        # Try to load logo from file, fallback to placeholder text
        logo_path = "main/mirc_logo.jpg"  # Change this to your logo file path
        if os.path.exists(logo_path):
            pixmap = QPixmap(logo_path)
            # Scale logo to reasonable size (max 100px height)
            scaled_pixmap = pixmap.scaledToHeight(100, Qt.SmoothTransformation)
            logo_label.setPixmap(scaled_pixmap)
        else:
            # Fallback: styled text logo
            logo_label.setText("🎥 VIDEO PROCESSOR")
            logo_label.setStyleSheet("""
                font-size: 24px; 
                font-weight: bold; 
                color: #2c3e50; 
                padding: 10px;
                background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 0, 
                    stop: 0 #3498db, stop: 1 #2980b9);
                color: white;
                border-radius: 8px;
                margin: 5px;
            """)
        
        # Title
        title_label = QLabel("MIRC Video Processing & Query System")
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("""
            font-size: 20px; 
            font-weight: bold; 
            color: #34495e; 
            margin: 5px 0 15px 0;
            padding: 5px;
        """)
        
        header_layout.addWidget(logo_label)
        header_layout.addWidget(title_label)
        header_widget.setLayout(header_layout)
        
        return header_widget

    def setup_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Add header (logo + title)
        header = self.create_header()
        layout.addWidget(header)
        
        # Add separator line
        separator = QLabel()
        separator.setFixedHeight(2)
        separator.setStyleSheet("background-color: #bdc3c7; margin: 0 20px;")
        layout.addWidget(separator)

        # Create tab widget
        self.tabs = QTabWidget()
        self.tabs.setContentsMargins(10, 10, 10, 10)
        
        # Create tabs
        self.upload_tab = VideoUploadTab()
        self.query_tab = QueryTab()

        # Add tabs
        self.tabs.addTab(self.upload_tab, "Upload Videos")
        self.tabs.addTab(self.query_tab, "Query Database")
        self.tabs.addTab(DatabaseBrowserTab(), "Database Browser")

        layout.addWidget(self.tabs)
        self.setLayout(layout)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())