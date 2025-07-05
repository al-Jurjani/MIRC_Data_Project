# Bismillah
# Starting project on 07-01-1447 - 03-07-2025

# This file contains the frontend for Part A (transcription, translation, summarization, embedding)

import sys
import threading
from PyQt5.QtWidgets import (
    QApplication, QWidget, QPushButton, QLabel,
    QVBoxLayout, QFileDialog, QProgressBar, QMessageBox
)
from PyQt5.QtCore import Qt
from pipeline import process_video

class VideoUploader(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        self.setWindowTitle('Video Uploader and Processor')

        layout = QVBoxLayout()

        self.label = QLabel('Select a video to process:', self)
        layout.addWidget(self.label)

        self.upload_btn = QPushButton('Choose Video')
        self.upload_btn.clicked.connect(self.choose_video)
        layout.addWidget(self.upload_btn)

        self.progress = QProgressBar(self)
        self.progress.setValue(0)
        layout.addWidget(self.progress)

        self.status_label = QLabel('', self)
        layout.addWidget(self.status_label)

        self.setLayout(layout)
        self.resize(300, 150)

    def choose_video(self):
        file_path, _ = QFileDialog.getOpenFileName(self, 'Open Video File', '', 'MP4 Files (*.mp4)')
        if file_path:
            self.progress.setValue(0)
            self.status_label.setText("Processing...")
            thread = threading.Thread(target=self.process_in_background, args=(file_path,))
            thread.start()

    def process_in_background(self, video_path):
        try:
            self.update_progress(10)
            guid = process_video(video_path, "processed_videos")
            self.update_progress(100)
            self.status_label.setText(f"Done! GUID: {guid}")
        except Exception as e:
            self.status_label.setText("Error during processing.")
            QMessageBox.critical(self, "Error", str(e))

    def update_progress(self, value):
        self.progress.setValue(value)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = VideoUploader()
    window.show()
    sys.exit(app.exec_())