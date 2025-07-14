# Bismillah
# Starting project on 07-01-1447 - 03-07-2025

import sys
import os
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFileDialog, QProgressBar, QMessageBox, QTabWidget,
    QLineEdit, QTableWidget, QTableWidgetItem, QListWidget, QListWidgetItem,
    QSplitter
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QMimeData
from PyQt5.QtGui import QDragEnterEvent, QDropEvent
from pipeline import process_video
from query_backend import search_similar
from chat_handler_service import rerank_top_matches

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

class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Video Processing & Query System")
        self.resize(800, 600)
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout()

        # Create tab widget
        self.tabs = QTabWidget()
        
        # Create tabs
        self.upload_tab = VideoUploadTab()
        self.query_tab = QueryTab()

        # Add tabs
        self.tabs.addTab(self.upload_tab, "Upload Videos")
        self.tabs.addTab(self.query_tab, "Query Database")

        layout.addWidget(self.tabs)
        self.setLayout(layout)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())