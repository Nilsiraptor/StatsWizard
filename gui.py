import sys

from PyQt6.QtWidgets import QApplication, QMainWindow, QWidget, QLabel
from PyQt6.QtWidgets import QHBoxLayout, QGridLayout
from PyQt6.QtGui import QFont, QFontDatabase, QIcon
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from matplotlib import font_manager, rcParams
from matplotlib.ticker import MultipleLocator, MaxNLocator, AutoMinorLocator, PercentFormatter
from PyQt6.QtCore import Qt
from scipy.interpolate import Akima1DInterpolator

from thread_worker import ThreadWorker

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

        self.load_font("Inter.ttc")
        self.setFont(self.font)

        self.statusBar().setFont(self.font)
        self.statusBar().showMessage("Searching for League Client...")

        self.setCentralWidget(QWidget())
        self.layout = QHBoxLayout(self.centralWidget())
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)

        self.graph = LiveGraph(parent=self, dpi=self.screen().logicalDotsPerInch())
        self.layout.addWidget(self.graph, stretch=1)

        self.stats_box = StatDisplay(self.font)
        self.layout.addWidget(self.stats_box, stretch=0)

        self.worker = ThreadWorker()
        self.worker.state_changed.connect(self.change_status)
        self.worker.data_updated.connect(self.stats_box.update_data)

        self.worker.start()

        self.show()
        self.setMinimumSize(self.size())

        self.windowHandle().screenChanged.connect(self.graph.sync_matplotlib_dpi)

    def load_font(self, path):
        font_id = QFontDatabase.addApplicationFont(path)

        if font_id == -1:
            raise FileNotFoundError("Could not load inter.ttc")

        # Get the actual family name recognized by the system (usually "Inter")
        font_families = QFontDatabase.applicationFontFamilies(font_id)
        self.font_family = font_families[0]

        self.font = QFont(self.font_family)
        self.font.setPointSize(10)
        self.font.setWeight(QFont.Weight.Medium)
        self.enable_font_features(FONT_FEATURES)

    def enable_font_features(self, features):
        for feat in features:
            self.font.setFeature(QFont.Tag.fromString(feat), 1)

    def get_graph(self):
        return self.graph

    def get_stats(self):
        return self.stats_box.get_stats()

    def change_status(self, new_status):
        self.statusBar().showMessage(str(new_status))


class LiveGraph(FigureCanvasQTAgg):

    def __init__(self, parent=None, dpi=96):
        font_manager.fontManager.addfont("Inter.ttc")
        rcParams["font.family"] = "Inter"
        rcParams["font.weight"] = "medium"
        rcParams["font.size"] = FONT_SIZE

        rcParams["figure.frameon"] = False
        rcParams["figure.constrained_layout.use"] = True

        self.fig = Figure(dpi=dpi, figsize=(4, 1))
        self.ax = self.fig.add_subplot()
        super().__init__(self.fig)
        self.setParent(parent)

        # show example curve
        x = np.linspace(-120, 0, 121, True)
        y = opensimplex.OpenSimplex(np.random.randint(0, 1024)).noise2array(np.array([1]), x/50)
        y[0:20] = np.zeros(20).reshape(-1, 1)

        interp = Akima1DInterpolator(x, 50*y+50, method="makima")
        show_x = np.linspace(-120, 0, 1001, True)

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

        self.update_font_features()
        # self.mpl_connect("draw_event", self.update_font_features)

    def sync_matplotlib_dpi(self, new_screen):
        new_dpi = new_screen.logicalDotsPerInch()
        self.fig.set_dpi(new_dpi)
        self.draw_idle()

    def update_font_features(self, *args):
        for label in self.ax.get_xticklabels() + self.ax.get_yticklabels():
            label.set_fontfeatures(FONT_FEATURES)


class StatDisplay(QWidget):

    def __init__(self, font):
        super().__init__()
        # self.setObjectName("StatDisplay")
        # self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        self.layout = QGridLayout()
        self.setLayout(self.layout)

        self.stat_names = ["level", "kills", "deaths", "assists", "minions", "wards", "item_gold", "turrets", "inhibs", "heralds", "dragons", "barons", "aces"]

        self.stats = {}
        for r, stat in enumerate(self.stat_names):
            red_text = QLabel()
            name_text = QLabel()
            blue_text = QLabel()

            self.layout.addWidget(red_text, r, 0)
            self.layout.addWidget(name_text, r, 1)
            self.layout.addWidget(blue_text, r, 2)

            red_text.setText("0")
            name_text.setText(self.title(stat))
            blue_text.setText("0")

            red_text.setAlignment(Qt.AlignmentFlag.AlignRight)
            name_text.setAlignment(Qt.AlignmentFlag.AlignHCenter)
            blue_text.setAlignment(Qt.AlignmentFlag.AlignLeft)

            red_text.setFont(font)
            name_text.setFont(font)
            blue_text.setFont(font)

            min_width = 25
            red_text.setMinimumWidth(min_width)
            blue_text.setMinimumWidth(min_width)

            self.stats[stat] = red_text, name_text, blue_text

        self.layout.setRowStretch(len(self.stats), 1)

    def title(self, string):
        return string.replace("_", " ").title()

    def get_stats(self):
        return self.stats

    def update_data(self, data):
        for key, value in data.items():
            key = key.split("_")
            if 1 >= len(key):
                return

            team, stat = key

            labels = self.stats[stat]

            if "ally" == team:
                labels[0].setText(value)
            elif "enemy" == team:
                labels[2].setText(value)
