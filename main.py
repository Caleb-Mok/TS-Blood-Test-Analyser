import sys
# import numpy

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QPushButton, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QLineEdit, QSizePolicy)
from PySide6.QtCore import Qt

class BloodAnalyzerApp(QMainWindow):
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Blood Test Analyser")
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        # layout
        main_layout = QVBoxLayout(central_widget)

        # Menu Buttons
        open_button = QPushButton("Open")
        clear_button = QPushButton("Clear All")
        submit_button = QPushButton("Submit")
        export_button = QPushButton("Export")

        menu_layout = QHBoxLayout()
        menu_layout.addWidget(open_button)
        menu_layout.addWidget(clear_button)
        menu_layout.addWidget(submit_button)
        menu_layout.addWidget(export_button)
        main_layout.addLayout(menu_layout)

        # Table Grid
        grid = QGridLayout()
        grid.setHorizontalSpacing(20)
        grid.setVerticalSpacing(8)

        # set how wide each column becomes
        grid.setColumnStretch(0, 1)   # Parameter (small)
        grid.setColumnStretch(1, 2)   # Result (larger)
        grid.setColumnStretch(2, 1)   # Range (small)
        grid.setColumnStretch(3, 1)   # Status (small)

       
        grid.addWidget(QLabel("<b>Parameter</b>"), 0, 0, Qt.AlignTop | Qt.AlignLeft)
        grid.addWidget(QLabel("<b>Result</b>"), 0, 1, Qt.AlignTop | Qt.AlignLeft)
        grid.addWidget(QLabel("<b>Range</b>"), 0, 2, Qt.AlignTop | Qt.AlignLeft)
        grid.addWidget(QLabel("<b>Status</b>"), 0, 3, Qt.AlignTop | Qt.AlignLeft)

        # Sample demo row
        grid.addWidget(QLabel("Haemoglobin"), 1, 0)
        grid.addWidget(QLineEdit(), 1, 1)
        grid.addWidget(QLabel("120–150 g/L"), 1, 2)
        grid.addWidget(QLabel("Healthy"), 1, 3)

        main_layout.addLayout(grid)
        main_layout.addStretch() # Move everything to top



if __name__ == "__main__":
    app = QApplication(sys.argv)

    window = BloodAnalyzerApp()
    window.resize(700, 700)
    window.show()

    app.exec()