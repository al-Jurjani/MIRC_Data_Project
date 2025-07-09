# Bismillah
# Starting project on 07-01-1447 - 03-07-2025

# import sys
# from PyQt5.QtWidgets import (
#     QApplication, QWidget, QVBoxLayout, QLabel, QLineEdit,
#     QPushButton, QTextEdit, QTableWidget, QTableWidgetItem
# )

# from query_backend import search_similar

# class QueryWindow(QWidget):
#     def __init__(self):
#         super().__init__()
#         self.setWindowTitle("Query Video Knowledge Base")
#         self.resize(600, 400)

#         self.layout = QVBoxLayout()

#         self.label = QLabel("Enter your question:")
#         self.query_input = QLineEdit()

#         self.search_btn = QPushButton("Search")
#         self.search_btn.clicked.connect(self.run_query)

#         self.results_table = QTableWidget()
#         self.results_table.setColumnCount(5)
#         self.results_table.setHorizontalHeaderLabels([
#             "GUID", "Video Path", "Transcript", "Translation", "Summary"])

#         self.layout.addWidget(self.label)
#         self.layout.addWidget(self.query_input)
#         self.layout.addWidget(self.search_btn)
#         self.layout.addWidget(self.results_table)

#         self.setLayout(self.layout)

#     def run_query(self):
#         query = self.query_input.text()
#         if not query.strip():
#             return

#         self.results_table.setRowCount(0)  # Clear previous results
#         results = search_similar(query, top_k=3)

#         self.results_table.setRowCount(len(results))
#         for row, res in enumerate(results):
#             self.results_table.setItem(row, 0, QTableWidgetItem(res["guid"]))
#             self.results_table.setItem(row, 1, QTableWidgetItem(res["video_path"]))
#             self.results_table.setItem(row, 2, QTableWidgetItem(res["transcript_path"]))
#             self.results_table.setItem(row, 3, QTableWidgetItem(res["translation_path"]))
#             self.results_table.setItem(row, 4, QTableWidgetItem(res["summary_path"]))

# if __name__ == '__main__':
#     app = QApplication(sys.argv)
#     window = QueryWindow()
#     window.show()
#     sys.exit(app.exec_())

import sys
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QLabel, QLineEdit,
    QPushButton, QTableWidget, QTableWidgetItem, QMessageBox
)
from langcodes import best_match
from query_backend import search_similar
from chat_handler_service import rerank_top_matches

class QueryWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Query Video Knowledge Base")
        self.resize(600, 400)

        self.layout = QVBoxLayout()

        self.label = QLabel("Enter your question:")
        self.query_input = QLineEdit()

        self.search_btn = QPushButton("Search")
        self.search_btn.clicked.connect(self.run_query)

        self.results_table = QTableWidget()
        # self.results_table.setColumnCount(3)
        # self.results_table.setHorizontalHeaderLabels([
        #     "Score", "Title", "Video Path"])
        self.results_table.setColumnCount(4)
        self.results_table.setHorizontalHeaderLabels([
            "Score", "Title", "Video Path", "Best Match"
        ])

        self.layout.addWidget(self.label)
        self.layout.addWidget(self.query_input)
        self.layout.addWidget(self.search_btn)
        self.layout.addWidget(self.results_table)

        self.setLayout(self.layout)

    def run_query(self):
        query = self.query_input.text().strip()
        if not query:
            QMessageBox.warning(self, "Warning", "Please enter a query.")
            return

        self.results_table.setRowCount(0)

        matches = search_similar(query, top_k=10)
        ranked_results = rerank_top_matches(query, matches)

        self.results_table.setRowCount(len(ranked_results))
        for row, item in enumerate(ranked_results):
        #     # self.results_table.setItem(row, 0, QTableWidgetItem(f"{item['score']:.2f}"))
        #     # self.results_table.setItem(row, 1, QTableWidgetItem(item['title']))
        #     # self.results_table.setItem(row, 2, QTableWidgetItem(item['video_path']))
        #     best_match = item["matches"][0] if item["matches"] else {"score": 0.0, "sentence": "N/A"}

            self.results_table.setItem(row, 0, QTableWidgetItem(f"{item['score']:.2f}"))
            self.results_table.setItem(row, 1, QTableWidgetItem(item['title']))
            self.results_table.setItem(row, 2, QTableWidgetItem(item['video_path']))
            self.results_table.setItem(row, 3, QTableWidgetItem(item['sentence']))

        # total_rows = sum(len(item["matches"]) for item in ranked_results)
        # self.results_table.setRowCount(total_rows)

        # row = 0
        # for item in ranked_results:
        #     title = item["title"]
        #     video_path = item["video_path"]
            
        #     for match in item["matches"]:
        #         score_str = f"{match['score']:.2f}"
        #         sentence = match['sentence']
                
        #         self.results_table.setItem(row, 0, QTableWidgetItem(score_str))
        #         self.results_table.setItem(row, 1, QTableWidgetItem(title))
        #         self.results_table.setItem(row, 2, QTableWidgetItem(video_path))
        #         self.results_table.setItem(row, 3, QTableWidgetItem(sentence))
                
        #         row += 1

        self.results_table.resizeRowsToContents()
        self.results_table.resizeColumnsToContents()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = QueryWindow()
    window.show()
    sys.exit(app.exec_())