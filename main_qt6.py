import sys

from PyQt6.QtWidgets import QApplication

from gui import MainWindow


app = QApplication(sys.argv)

app.setStyleSheet("""
    QWidget {
        background-color: white;
        padding: 0px;
        margin: 0px;
    }

    QStatusBar {
        border-top: 1px solid grey;
        background-color: whitesmoke;
    }
""")

window = MainWindow()

graph = window.get_graph()
stats = window.get_stats()


sys.exit(app.exec())
