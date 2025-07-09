# Bismillah
# Starting project on 07-01-1447 - 03-07-2025

# This file contains the frontend for Part A (transcription, translation, summarization, embedding)

import sys
import os
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QLabel,
    QPushButton, QFileDialog, QProgressBar, QMessageBox
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from pipeline import process_video

class VideoProcessingThread(QThread):
    progress_update = pyqtSignal(int)
    finished = pyqtSignal(str)
    failed = pyqtSignal(str)

    def __init__(self, video_path, base_dir):
        super().__init__()
        self.video_path = video_path
        self.base_dir = base_dir

    def run(self):
        try:
            self.progress_update.emit(10)
            guid = process_video(self.video_path, self.base_dir, self.progress_update)
            self.progress_update.emit(100)
            self.finished.emit(guid)
        except Exception as e:
            self.failed.emit(str(e))

class VideoUploader(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Video Uploader")
        self.resize(400, 150)

        self.layout = QVBoxLayout()

        self.label = QLabel("Upload an MP4 video for processing")
        self.label.setAlignment(Qt.AlignCenter)

        self.upload_btn = QPushButton("Upload Video")
        self.upload_btn.clicked.connect(self.upload_video)

        self.progress = QProgressBar()
        self.progress.setValue(0)

        self.layout.addWidget(self.label)
        self.layout.addWidget(self.upload_btn)
        self.layout.addWidget(self.progress)

        self.setLayout(self.layout)

    def upload_video(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Select MP4 Video", "", "Video Files (*.mp4)")
        if file_path:
            self.upload_btn.setEnabled(False)
            self.progress.setValue(5)
            base_dir = os.path.abspath("processed_videos")

            self.thread = VideoProcessingThread(file_path, base_dir)
            self.thread.progress_update.connect(self.progress.setValue)
            self.thread.finished.connect(self.on_success)
            self.thread.failed.connect(self.on_failure)
            self.thread.start()

    def on_success(self, guid):
        QMessageBox.information(self, "Success", f"Video processed successfully. GUID: {guid}")
        self.upload_btn.setEnabled(True)
        self.progress.setValue(100)

    def on_failure(self, error_msg):
        QMessageBox.critical(self, "Error", f"Failed to process video:\n{error_msg}")
        self.upload_btn.setEnabled(True)
        self.progress.setValue(0)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = VideoUploader()
    window.show()
    sys.exit(app.exec_())