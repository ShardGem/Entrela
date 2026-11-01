from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from gui.theme import PALETTE


class MplCanvas(FigureCanvas):
    def __init__(self, parent=None, width=5, height=4, dpi=100):
        self.fig = Figure(
            figsize=(width, height), dpi=dpi, facecolor=PALETTE.bg, layout="constrained"
        )
        super().__init__(self.fig)
        self.setParent(parent)
        self.setMinimumSize(240, 220)

    def reset_axes(self):
        self.fig.clear()
        ax = self.fig.add_subplot(111)
        ax.set_facecolor(PALETTE.bg)
        ax.tick_params(colors=PALETTE.text_muted)
        for spine in ax.spines.values():
            spine.set_color(PALETTE.border_strong)
        ax.xaxis.label.set_color(PALETTE.text_muted)
        ax.yaxis.label.set_color(PALETTE.text_muted)
        ax.title.set_color(PALETTE.text)
        return ax
