"""Qt canvas with logical layout hints independent of its rendered buffer.

Matplotlib's default sizeHint follows the figure's last resize. Feeding that
back into a resizable scroll area can grow the layout again on every pass.
"""

from PySide6.QtCore import QSize
from PySide6.QtWidgets import QApplication, QSizePolicy
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.text import Text


class StableFigureCanvas(FigureCanvasQTAgg):
    def __init__(self, figure, parent=None, preferred=(640, 400), minimum=(240, 220)):
        self._layout_preferred = QSize(*preferred)
        self._layout_minimum = QSize(*minimum)
        app = QApplication.instance()
        self._interface_font_size = float(app.property("entrelaFontSize") or 15) if app else 15.
        super().__init__(figure)
        self.setParent(parent)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setMinimumSize(self._layout_minimum)

    def sizeHint(self):
        return QSize(self._layout_preferred)

    def minimumSizeHint(self):
        return QSize(self._layout_minimum)

    def set_interface_font_size(self, size):
        """Scale live charts with the UI, without changing Matplotlib defaults.

        Original artist sizes are retained so changing themes or redrawing a
        figure cannot accumulate scaling. Portable Agg exports remain independent.
        """
        self._interface_font_size = float(size)
        self._apply_font_scale()

    def _apply_font_scale(self):
        scale = self._interface_font_size / 15.
        # Future tick labels inherit tick_params. Keep their unscaled baseline
        # on the axis rather than treating inherited scaled sizes as originals.
        for axes in self.figure.axes:
            for name in ("xaxis", "yaxis", "zaxis"):
                axis = getattr(axes, name, None)
                if axis is None:
                    continue
                for which in ("major", "minor"):
                    ticks = (axis.get_major_ticks() if which == "major" else axis.get_minor_ticks())
                    if not ticks:
                        continue
                    key = f"_entrela_{which}_font"
                    base = getattr(axis, key, ticks[0].label1.get_fontsize())
                    first = ticks[0].label1
                    last = getattr(first, "_entrela_font_last", None)
                    if last is not None and abs(first.get_fontsize() - last) > 1e-8:
                        base = first.get_fontsize()
                    setattr(axis, key, base)
                    axis.set_tick_params(which=which, labelsize=base * scale)
                    for tick in ticks:
                        for label in (tick.label1, tick.label2):
                            label._entrela_font_base = base
                            label._entrela_font_last = base * scale
        for text in self.figure.findobj(match=Text):
            current = text.get_fontsize()
            last = getattr(text, "_entrela_font_last", None)
            if last is None or abs(current - last) > 1e-8:
                text._entrela_font_base = current
            size = text._entrela_font_base * scale
            text.set_fontsize(size)
            text._entrela_font_last = size

    def draw(self, *args, **kwargs):
        self._apply_font_scale()
        return super().draw(*args, **kwargs)

    def draw_idle(self, *args, **kwargs):
        self._apply_font_scale()
        return super().draw_idle(*args, **kwargs)
