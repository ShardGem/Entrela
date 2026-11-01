"""Qt canvas with logical layout hints independent of its rendered buffer.

Matplotlib's default sizeHint follows the figure's last resize. Feeding that
back into a resizable scroll area can grow the layout again on every pass.
"""

from PySide6.QtCore import QSize
from PySide6.QtWidgets import QSizePolicy
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg


class StableFigureCanvas(FigureCanvasQTAgg):
    def __init__(self, figure, parent=None, preferred=(640, 400), minimum=(240, 220)):
        self._layout_preferred = QSize(*preferred)
        self._layout_minimum = QSize(*minimum)
        super().__init__(figure)
        self.setParent(parent)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setMinimumSize(self._layout_minimum)

    def sizeHint(self):
        return QSize(self._layout_preferred)

    def minimumSizeHint(self):
        return QSize(self._layout_minimum)
