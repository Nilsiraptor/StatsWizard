"""Launches the Stats Wizard application.

This module initializes the PyQt6 application, applies global styling,
and creates the main window with its graph and statistics display.
"""
import sys
import subprocess
import atexit

from PyQt6.QtWidgets import QApplication

from gui import MainWindow


score_process = subprocess.Popen(
    [sys.executable, "score.py"],
    creationflags=subprocess.CREATE_NO_WINDOW
)

atexit.register(score_process.terminate)


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
