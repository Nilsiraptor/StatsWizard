import sys

from PyQt6.QtWidgets import QApplication

from gui import MainWindow


app = QApplication(sys.argv)

with open("style.css", "r") as file:
    StyleSheet = file.read()

app.setStyleSheet(StyleSheet)

window = MainWindow()

sys.exit(app.exec())
