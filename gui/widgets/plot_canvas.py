from gui.widgets.figure_canvas import StableFigureCanvas
from matplotlib.figure import Figure
from matplotlib.backends.backend_qtagg import NavigationToolbar2QT
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QCursor
from PySide6.QtWidgets import QMenu, QToolButton, QToolTip
from gui.icons import get_icon
from gui.theme import PALETTE


def style_axes(ax):
    ax.set_facecolor(PALETTE.bg_elevated)
    ax.tick_params(colors=PALETTE.text_muted)
    for spine in ax.spines.values():
        spine.set_color(PALETTE.border)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.xaxis.label.set_color(PALETTE.text_muted)
    ax.yaxis.label.set_color(PALETTE.text_muted)
    ax.title.set_color(PALETTE.text)
    return ax


def style_figure(fig):
    """Apply the live palette after a shared scientific renderer draws data."""
    fig.set_facecolor(PALETTE.bg_elevated)
    for axes in fig.axes:
        style_axes(axes)
        for label in axes.texts:
            label.set_color(PALETTE.text)
        legend = axes.get_legend()
        if legend is not None:
            legend.get_frame().set_facecolor(PALETTE.surface)
            legend.get_frame().set_edgecolor(PALETTE.border)
            for label in legend.get_texts():
                label.set_color(PALETTE.text)
    for label in fig.texts:
        label.set_color(PALETTE.text)


class MplCanvas(StableFigureCanvas):
    interface_surface = "bg_elevated"

    def __init__(self, parent=None, width=5, height=4, dpi=100):
        self.fig = Figure(
            figsize=(width, height), dpi=dpi, facecolor=PALETTE.bg_elevated, layout="constrained"
        )
        super().__init__(self.fig, parent, preferred=(500, 320))
        self._navigation = None
        self._value_lookup = None
        self.mpl_connect("motion_notify_event", self._show_values)
        self.mpl_connect("figure_leave_event", lambda _: QToolTip.hideText())

    def reset_axes(self):
        if self._navigation is not None:
            self._navigation.update()
        self.fig.clear()
        ax = self.fig.add_subplot(111)
        return style_axes(ax)

    def draw(self, *args, **kwargs):
        axes = tuple(self.fig.axes)
        navigation = getattr(self, "_navigation", None)
        if navigation is not None and axes != getattr(self, "_navigation_axes", None):
            navigation.update()
            self._navigation_axes = axes
        return super().draw(*args, **kwargs)

    def exploration_button(self, parent=None):
        """Compact access to Matplotlib navigation; exports keep their own flow."""
        if self._navigation is None:
            self._navigation = NavigationToolbar2QT(self, self, coordinates=False)
            self._navigation.hide()
        button = QToolButton(parent)
        button.setText("Explorar gráfico")
        button.setAccessibleName("Explorar gráfico")
        button.setToolTip("Ampliar, mover ou restaurar a escala do gráfico. Passe o mouse sobre os dados para ler valores.")
        button.setIcon(get_icon("search", color=PALETTE.text_muted))
        button.setIconSize(QSize(20, 20))
        button.setToolButtonStyle(Qt.ToolButtonIconOnly)
        button.setPopupMode(QToolButton.InstantPopup)
        menu = QMenu(button)
        pan = menu.addAction("Mover eixos com o mouse")
        pan.setCheckable(True)
        pan.triggered.connect(lambda _: self._navigation.pan())
        zoom = menu.addAction("Ampliar uma região")
        zoom.setCheckable(True)
        zoom.triggered.connect(lambda _: self._navigation.zoom())
        menu.addSeparator()
        menu.addAction("Restaurar escala inicial", self._navigation.home)
        menu.aboutToShow.connect(lambda: pan.setChecked(self._navigation.mode.name == "PAN"))
        menu.aboutToShow.connect(lambda: zoom.setChecked(self._navigation.mode.name == "ZOOM"))
        button.setMenu(menu)
        return button

    def set_value_lookup(self, lookup):
        self._value_lookup = lookup

    def _show_values(self, event):
        if self._value_lookup is None or (self._navigation is not None and self._navigation.mode):
            return
        text = self._value_lookup(event) if event.inaxes else None
        if text:
            QToolTip.showText(QCursor.pos(), text, self)
        else:
            QToolTip.hideText()
