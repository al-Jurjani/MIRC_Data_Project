# Bismillah
# Starting project on 07-01-1447 - 03-07-2025

import sys
import shutil
import os
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFileDialog, QProgressBar, QMessageBox, QTabWidget,
    QLineEdit, QTableWidget, QTableWidgetItem, QListWidget, QListWidgetItem,
    QSplitter, QHeaderView, QScrollArea, QFrame
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QMimeData
from PyQt5.QtGui import QDragEnterEvent, QDropEvent, QPixmap, QImage
import cv2
import numpy as np
import torch
import subprocess
import platform
from PyQt5.QtCore import QUrl
from PyQt5.QtGui import QDesktopServices, QCursor

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

        # Results scroll area
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        
        # Container widget for results
        self.results_container = QWidget()
        self.results_layout = QVBoxLayout()
        self.results_layout.setSpacing(10)
        self.results_container.setLayout(self.results_layout)
        self.scroll_area.setWidget(self.results_container)

        layout.addWidget(title_label)
        layout.addLayout(query_layout)
        layout.addWidget(QLabel("Search Results:"))
        layout.addWidget(self.scroll_area)

        self.setLayout(layout)

    def get_video_thumbnail(self, video_path):
        """Extract a frame from the video to use as thumbnail"""
        try:
            # Check if video file exists
            if not os.path.exists(video_path):
                return self.create_placeholder_thumbnail("File Not Found")
            
            # Open video file
            cap = cv2.VideoCapture(video_path)
            
            if not cap.isOpened():
                return self.create_placeholder_thumbnail("Cannot Open Video")
            
            # Get video properties
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            fps = cap.get(cv2.CAP_PROP_FPS)
            
            # Seek to 10% into the video (usually gives a good representative frame)
            # Avoid the very beginning which might be black or logos
            target_frame = min(int(total_frames * 0.1), int(fps * 5))  # Max 5 seconds in
            cap.set(cv2.CAP_PROP_POS_FRAMES, target_frame)
            
            # Read the frame
            ret, frame = cap.read()
            cap.release()
            
            if not ret or frame is None:
                return self.create_placeholder_thumbnail("No Frame Available")
            
            # Convert BGR to RGB (OpenCV uses BGR, Qt uses RGB)
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
            # Get frame dimensions
            height, width, channels = frame_rgb.shape
            bytes_per_line = channels * width
            
            # Create QImage from the frame
            q_image = QImage(frame_rgb.data, width, height, bytes_per_line, QImage.Format_RGB888)
            
            # Convert to QPixmap and scale
            pixmap = QPixmap.fromImage(q_image)
            scaled_pixmap = pixmap.scaled(120, 80, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            
            return scaled_pixmap
            
        except Exception as e:
            print(f"Error extracting thumbnail from {video_path}: {str(e)}")
            return self.create_placeholder_thumbnail("Extraction Error")
    
    def create_placeholder_thumbnail(self, message="No Preview"):
        """Create a placeholder thumbnail with a message"""
        pixmap = QPixmap(120, 80)
        pixmap.fill(Qt.lightGray)
        
        # You could add text to the placeholder here if needed
        # This creates a simple gray rectangle placeholder
        return pixmap

    def create_result_card(self, item):
        """Create a card widget for each search result"""
        card = QFrame()
        card.setFrameStyle(QFrame.StyledPanel)
        card.setStyleSheet("""
            QFrame {
                border: 1px solid #ddd;
                border-radius: 8px;
                background-color: white;
                margin: 2px;
            }
            QFrame:hover {
                border: 2px solid #3498db;
                background-color: #f8f9fa;
            }
        """)
        
        card_layout = QHBoxLayout()
        card_layout.setContentsMargins(10, 10, 10, 10)
        card_layout.setSpacing(15)
        
        # Thumbnail - Make it clickable
        thumbnail_label = QLabel()
        thumbnail_pixmap = self.get_video_thumbnail(item['video_path'])
        thumbnail_label.setPixmap(thumbnail_pixmap)
        thumbnail_label.setFixedSize(120, 80)
        thumbnail_label.setStyleSheet("""
            border: 1px solid #ccc; 
            border-radius: 4px;
            cursor: pointer;
        """)
        thumbnail_label.setScaledContents(True)
        
        # Make thumbnail clickable - capture video_path in closure
        video_path = item['video_path']
        thumbnail_label.mousePressEvent = lambda event, path=video_path: self.open_video(path)
        thumbnail_label.setCursor(QCursor(Qt.PointingHandCursor))
        
        # Content area
        content_layout = QVBoxLayout()
        content_layout.setSpacing(5)
        
        # Title and Score
        title_score_layout = QHBoxLayout()
        title_label = QLabel(item['title'])
        title_label.setStyleSheet("""
            font-weight: bold; 
            font-size: 14px; 
            color: #2c3e50;
            cursor: pointer;
        """)
        title_label.setWordWrap(True)
        title_label.setCursor(QCursor(Qt.PointingHandCursor))
        
        # Make title clickable
        title_label.mousePressEvent = lambda event, path=video_path: self.open_video(path)
        
        score_label = QLabel(f"Score: {item['score']:.2f}")
        score_label.setStyleSheet("font-weight: bold; color: #e74c3c; font-size: 12px;")
        score_label.setAlignment(Qt.AlignRight | Qt.AlignTop)
        score_label.setFixedWidth(80)
        
        title_score_layout.addWidget(title_label, 1)
        title_score_layout.addWidget(score_label, 0)
        
        # Best match text
        match_label = QLabel("Best Match:")
        match_label.setStyleSheet("font-weight: bold; font-size: 11px; color: #7f8c8d; margin-top: 5px;")
        
        sentence_label = QLabel(item['sentence'])
        sentence_label.setWordWrap(True)
        sentence_label.setStyleSheet("font-size: 11px; color: #34495e; background-color: #ecf0f1; padding: 5px; border-radius: 3px;")
        sentence_label.setMaximumHeight(60)
        
        # Video path with play button
        path_layout = QHBoxLayout()
        path_label = QLabel(f"📁 {os.path.basename(item['video_path'])}")
        path_label.setStyleSheet("font-size: 10px; color: #95a5a6; margin-top: 3px;")
        
        # Add a small play button
        play_button = QPushButton("▶️ Play")
        play_button.setStyleSheet("""
            QPushButton {
                background-color: #3498db;
                color: white;
                border: none;
                border-radius: 3px;
                padding: 3px 8px;
                font-size: 10px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
            QPushButton:pressed {
                background-color: #21618c;
            }
        """)
        play_button.setMaximumSize(60, 25)
        play_button.clicked.connect(lambda checked, path=video_path: self.open_video(path))
        
        path_layout.addWidget(path_label)
        path_layout.addStretch()
        path_layout.addWidget(play_button)
        
        content_layout.addLayout(title_score_layout)
        content_layout.addWidget(match_label)
        content_layout.addWidget(sentence_label)
        content_layout.addLayout(path_layout)
        content_layout.addStretch()
        
        card_layout.addWidget(thumbnail_label)
        card_layout.addLayout(content_layout, 1)
        
        card.setLayout(card_layout)
        return card

    def open_video(self, video_path):
        """Open the video file using the default system video player"""
        try:
            if not os.path.exists(video_path):
                QMessageBox.warning(self, "File Not Found", f"Video file not found:\n{video_path}")
                return
            
            # Get the system platform
            system = platform.system()
            
            if system == "Windows":
                # Windows: use start command
                os.startfile(video_path)
            elif system == "Darwin":  # macOS
                # macOS: use open command
                subprocess.run(["open", video_path])
            else:  # Linux and other Unix-like systems
                # Linux: use xdg-open
                subprocess.run(["xdg-open", video_path])
                
            print(f"Opening video: {video_path}")
            
        except Exception as e:
            # Fallback: try using Qt's QDesktopServices
            try:
                QDesktopServices.openUrl(QUrl.fromLocalFile(video_path))
            except:
                QMessageBox.critical(self, "Error", f"Could not open video file:\n{str(e)}")

    def run_query(self):
        query = self.query_input.text().strip()
        if not query:
            QMessageBox.warning(self, "Warning", "Please enter a query.")
            return

        # Clear previous results
        while self.results_layout.count():
            child = self.results_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        try:
            matches = search_similar(query, top_k=10)
            ranked_results = rerank_top_matches(query, matches)

            if not ranked_results:
                no_results_label = QLabel("No results found for your query.")
                no_results_label.setAlignment(Qt.AlignCenter)
                no_results_label.setStyleSheet("color: #7f8c8d; font-style: italic; padding: 20px;")
                self.results_layout.addWidget(no_results_label)
            else:
                for item in ranked_results:
                    result_card = self.create_result_card(item)
                    self.results_layout.addWidget(result_card)
            
            # Add stretch to push results to top
            self.results_layout.addStretch()

        except Exception as e:
            error_label = QLabel(f"Search failed: {str(e)}")
            error_label.setStyleSheet("color: #e74c3c; padding: 10px; background-color: #fadbd8; border-radius: 4px;")
            self.results_layout.addWidget(error_label)


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
        self.setWindowTitle("MIRC Video Processing & Query System")
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
        # logo_path = "main/mirc_logo.jpg"  # Change this to your logo file path

        def resource_path(relative_path):
            """ Get absolute path to resource, works for dev and for PyInstaller """
            if hasattr(sys, '_MEIPASS'):
                return os.path.join(sys._MEIPASS, relative_path)
            return os.path.join(os.path.dirname(__file__), relative_path)
        logo_path = resource_path("mirc_logo.jpg")
        
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

        # Add GPU status indicator - INSERT THIS LINE
        gpu_status = self.create_gpu_status_widget()
        layout.addWidget(gpu_status)
        
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

    def create_gpu_status_widget(self):
        """Create a widget that shows GPU/CPU status"""
        status_widget = QWidget()
        status_layout = QHBoxLayout()
        status_layout.setContentsMargins(10, 5, 10, 5)
        
        # Check GPU availability
        gpu_available = torch.cuda.is_available()
        device_count = torch.cuda.device_count() if gpu_available else 0
        
        # Status icon and text
        status_icon = QLabel()
        status_text = QLabel()
        
        if gpu_available:
            # GPU available
            gpu_name = torch.cuda.get_device_name(0) if device_count > 0 else "Unknown GPU"
            status_icon.setText("🔥")  # Fire emoji for GPU
            status_text.setText(f"GPU Acceleration: {gpu_name}")
            status_text.setStyleSheet("""
                color: #27ae60; 
                font-weight: bold; 
                font-size: 12px;
                padding: 3px;
            """)
            status_icon.setStyleSheet("font-size: 16px;")
        else:
            # CPU only
            status_icon.setText("🔧")  # Wrench emoji for CPU
            status_text.setText("CPU Processing Only")
            status_text.setStyleSheet("""
                color: #f39c12; 
                font-weight: bold; 
                font-size: 12px;
                padding: 3px;
            """)
            status_icon.setStyleSheet("font-size: 16px;")
        
        # Memory info (if GPU available)
        memory_info = QLabel()
        if gpu_available and device_count > 0:
            try:
                memory_total = torch.cuda.get_device_properties(0).total_memory / 1024**3  # GB
                memory_info.setText(f"VRAM: {memory_total:.1f}GB")
                memory_info.setStyleSheet("color: #7f8c8d; font-size: 10px; margin-left: 10px;")
            except:
                memory_info.setText("")
        
        status_layout.addWidget(status_icon)
        status_layout.addWidget(status_text)
        status_layout.addWidget(memory_info)
        status_layout.addStretch()  # Push everything to the left
        
        status_widget.setLayout(status_layout)
        status_widget.setStyleSheet("""
            QWidget {
                background-color: #ecf0f1;
                border-radius: 6px;
                margin: 5px;
            }
        """)
        
        return status_widget

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())