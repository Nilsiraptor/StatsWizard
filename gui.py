import sys

from PyQt6.QtWidgets import QApplication, QMainWindow, QWidget, QHBoxLayout
from PyQt6.QtGui import QFont, QFontDatabase, QIcon
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from matplotlib import font_manager, rcParams


class MainWindow(QMainWindow):

    def __init__(self):
        super().__init__()
        self.setWindowTitle("StatsWizard")
        self.setWindowIcon(QIcon("my_icon.ico"))

        self.resize(600, 400)

        self.loadFont("Inter.ttc")
        self.setFont(self.font)

        self.statusBar().setFont(self.font)
        self.statusBar().showMessage("Test Wizard tf ff 031.2384 Island")

        self.setCentralWidget(QWidget())
        self.layout = QHBoxLayout(self.centralWidget())

        self.graph = LiveGraph()
        self.layout.addWidget(self.graph)

        self.show()

    def loadFont(self, path):
        font_id = QFontDatabase.addApplicationFont(path)

        if font_id == -1:
            raise Exception()

        # Get the actual family name recognized by the system (usually "Inter")
        font_families = QFontDatabase.applicationFontFamilies(font_id)
        self.font_family = font_families[0]

        self.font = QFont(self.font_family)
        # self.font.setPointSize(24)
        self.font.setWeight(QFont.Weight.Medium)
        self.enableFontFeatures(["calt", "tnum", "dlig",
                                 "cv01", "cv03", "cv04",
                                 "cv05", "cv08", "cv09"])

    def enableFontFeatures(self, features):
        for feat in features:
            self.font.setFeature(QFont.Tag.fromString(feat), 1)

class LiveGraph(FigureCanvasQTAgg):

    def __init__(self, parent=None):
        font_manager.fontManager.addfont("Inter.ttc")
        rcParams["font.family"] = "Inter"
        rcParams["font.weight"] = "medium"

        rcParams["figure.frameon"] = False
        rcParams["figure.constrained_layout.use"] = True

        self.fig = Figure()
        self.ax = self.fig.add_subplot()
        super().__init__(self.fig)

        self.ax.plot([1, 2, 3], [10, 20, 30])

        self.ax.set_ylim(0, 1)

        self.fontFeatures = ["calt", "tnum", "dlig",
                             "cv01", "cv03", "cv04",
                             "cv05", "cv08", "cv09"]

        # Enable tabular numbers (tnum) and contextual alternates (calt)
        self.ax.set_title("Metrics 2026", fontfeatures=self.fontFeatures, fontsize=14)
        self.ax.set_xlabel("Timeline", fontfeatures=self.fontFeatures)
        self.ax.set_ylabel("Win Probability", fontfeatures=self.fontFeatures)
