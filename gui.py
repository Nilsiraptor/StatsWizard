import sys

from PyQt6.QtWidgets import QApplication, QMainWindow, QWidget, QGroupBox, QLabel
from PyQt6.QtWidgets import QHBoxLayout, QGridLayout
from PyQt6.QtGui import QFont, QFontDatabase, QIcon
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from matplotlib import font_manager, rcParams
from matplotlib.ticker import MultipleLocator, MaxNLocator, AutoMinorLocator, PercentFormatter
from PyQt6.QtCore import Qt
from scipy.interpolate import Akima1DInterpolator

# for testing
import numpy as np
import opensimplex

FONT_SIZE = 12
FONT_FEATURES = ["calt", "tnum", "dlig",
                 "cv01", "cv03", "cv04",
                 "cv05", "cv08", "cv09"]


class MainWindow(QMainWindow):

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Stats Wizard")
        self.setWindowIcon(QIcon("my_icon.ico"))

        # self.resize(600, 400)

        self.loadFont("Inter.ttc")
        self.setFont(self.font)

        self.statusBar().setFont(self.font)
        self.statusBar().showMessage("Statusbar")

        self.setCentralWidget(QWidget())
        self.layout = QHBoxLayout(self.centralWidget())
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)

        self.graph = LiveGraph(dpi=self.screen().logicalDotsPerInch())
        self.layout.addWidget(self.graph, stretch=1)

        self.statsBox = StatDisplay(self.font)
        self.layout.addWidget(self.statsBox, stretch=0)

        self.show()

        self.windowHandle().screenChanged.connect(self.graph.syncMatplotlibDPI)

    def loadFont(self, path):
        font_id = QFontDatabase.addApplicationFont(path)

        if font_id == -1:
            raise Exception()

        # Get the actual family name recognized by the system (usually "Inter")
        font_families = QFontDatabase.applicationFontFamilies(font_id)
        self.font_family = font_families[0]

        self.font = QFont(self.font_family)
        self.font.setPointSize(10)
        self.font.setWeight(QFont.Weight.Medium)
        self.enableFontFeatures(FONT_FEATURES)

    def enableFontFeatures(self, features):
        for feat in features:
            self.font.setFeature(QFont.Tag.fromString(feat), 1)


class LiveGraph(FigureCanvasQTAgg):

    def __init__(self, parent=None, dpi=96):
        font_manager.fontManager.addfont("Inter.ttc")
        rcParams["font.family"] = "Inter"
        rcParams["font.weight"] = "medium"
        rcParams["font.size"] = FONT_SIZE

        rcParams["figure.frameon"] = False
        rcParams["figure.constrained_layout.use"] = True

        self.fig = Figure(dpi=dpi, figsize=(5, 1))
        self.ax = self.fig.add_subplot()
        super().__init__(self.fig)

        # show example curve
        x = np.linspace(-120, 0, 121, True)
        y = opensimplex.OpenSimplex(np.random.randint(0, 1024)).noise2array(np.array([1]), x/50)
        y[0:20] = np.zeros(20).reshape(-1, 1)

        interp = Akima1DInterpolator(x, 50*y+50, method="makima")
        show_x = np.linspace(-120, 0, 501, True)

        self.line = self.ax.plot(show_x, interp(show_x), c="darkorchid")

        # Setting up Axis
        self.ax.grid()

        # self.ax.set_ylabel("Win Probability", fontfeatures=FONT_FEATURES)
        self.ax.set_ylim(0, 100)
        self.ax.yaxis.set_minor_locator(AutoMinorLocator(2))
        self.ax.yaxis.set_major_locator(MaxNLocator("auto", steps=[1, 2, 2.5, 5, 10], integer=True))
        self.ax.yaxis.set_major_formatter(PercentFormatter(xmax=100))
        self.ax.xaxis.set_minor_locator(AutoMinorLocator(2))
        self.ax.xaxis.set_major_locator(MaxNLocator("auto", steps=[1, 2, 3, 4, 5, 6], integer=True))

        # self.ax.set_xlabel("Timeline", fontfeatures=FONT_FEATURES)
        self.ax.set_xlim(-120, 0)

        self.updateFontFeatures()
        # self.mpl_connect("draw_event", self.updateFontFeatures)

    def syncMatplotlibDPI(self, new_screen):
        new_dpi = new_screen.logicalDotsPerInch()
        self.fig.set_dpi(new_dpi)
        self.draw_idle()

    def updateFontFeatures(self, *args):
        for label in self.ax.get_xticklabels() + self.ax.get_yticklabels():
            label.set_fontfeatures(FONT_FEATURES)


class StatDisplay(QWidget):

    def __init__(self, font):
        super().__init__()
        # self.setObjectName("StatDisplay")
        # self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        self.layout = QGridLayout()
        self.setLayout(self.layout)

        self.statNames = ["level", "kills", "deaths", "assists", "minions", "wards", "item_gold", "turrets", "inhibs", "heralds", "dragons", "barons", "aces"]

        self.stats = []
        for r, stat in enumerate(self.statNames):
            redText = QLabel()
            nameText = QLabel()
            blueText = QLabel()

            self.layout.addWidget(redText, r, 0)
            self.layout.addWidget(nameText, r, 1)
            self.layout.addWidget(blueText, r, 2)

            redText.setText("0")
            nameText.setText(self.title(stat))
            blueText.setText("0")

            redText.setAlignment(Qt.AlignmentFlag.AlignRight)
            nameText.setAlignment(Qt.AlignmentFlag.AlignCenter)
            blueText.setAlignment(Qt.AlignmentFlag.AlignLeft)

            redText.setFont(font)
            nameText.setFont(font)
            blueText.setFont(font)

            minWidth = 25
            redText.setMinimumWidth(minWidth)
            blueText.setMinimumWidth(minWidth)

            self.stats.append((redText, nameText, blueText))

    def title(self, string):
        return string.replace("_", " ").title()
