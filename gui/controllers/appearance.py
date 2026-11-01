"""Recolor live Qt and Matplotlib components using the shared palette."""

from dataclasses import asdict
import re
from PySide6.QtWidgets import QWidget, QAbstractButton, QTextBrowser
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.colors import to_hex
from gui.theme import PALETTE, Palette, build_qss
from gui.icons import get_icon

DARK = asdict(Palette())
LIGHT = {
    **DARK,
    "bg": "#f3f6fb",
    "bg_elevated": "#ffffff",
    "surface": "#ffffff",
    "surface_hover": "#e7eef7",
    "surface_active": "#dce8f5",
    "border": "#d1dce9",
    "border_strong": "#8093ac",
    "primary": "#006e96",
    "primary_hover": "#005779",
    "primary_pressed": "#00415c",
    "primary_muted": "#d8eff9",
    "primary_faint": "#d8eff9",
    "primary_on": "#ffffff",
    "text_on_primary": "#ffffff",
    "text": "#172b46",
    "text_muted": "#49617d",
    "text_dim": "#526b88",
    "success": "#11763f",
    "success_bg": "#e0f4e8",
    "warning": "#925400",
    "warning_bg": "#fff0ce",
    "danger": "#bb293e",
    "danger_bg": "#ffe7eb",
    "info": "#006e96",
    "info_bg": "#d8eff9",
    "q1": "#006e96",
    "q2": "#7043c5",
    "q3": "#11763f",
    "q4": "#925400",
    "q5": "#bb293e",
    "q6": "#2258bc",
}


def apply_appearance(window, theme="dark", font_size=13):
    before = asdict(PALETTE)
    after = LIGHT if theme == "light" else DARK
    # Same singleton is imported throughout the GUI.
    mapping = {value.lower(): after[key] for key, value in before.items()}
    names = {value.lower(): key for key, value in before.items()}
    for key, value in after.items():
        object.__setattr__(PALETTE, key, value)

    def recolor(text):
        return re.sub(
            r"#[0-9a-fA-F]{6}", lambda m: mapping.get(m[0].lower(), m[0]), text
        )

    for widget in window.findChildren(QWidget):
        if widget.styleSheet():
            current = widget.styleSheet()
            if widget.property("entrelaAppliedStyle") != current:
                template = re.sub(
                    r"#[0-9a-fA-F]{6}",
                    lambda m: (
                        "@" + names[m[0].lower()] + "@"
                        if m[0].lower() in names
                        else m[0]
                    ),
                    current,
                )
                widget.setProperty("entrelaStyleTemplate", template)
            template = widget.property("entrelaStyleTemplate") or current
            style = re.sub(r"@([a-z0-9_]+)@", lambda m: after[m[1]], template)
            style = re.sub(
                r"font-size:\s*(\d+)px",
                lambda m: f"font-size: {round(int(m[1]) * font_size / 13)}px",
                style,
            )
            widget.setStyleSheet(style)
            widget.setProperty("entrelaAppliedStyle", style)
        if isinstance(widget, QTextBrowser):
            widget.setHtml(recolor(widget.toHtml()))
        if isinstance(widget, QAbstractButton) and hasattr(widget, "icon_name"):
            widget.setIcon(
                get_icon(
                    widget.icon_name,
                    color=PALETTE.primary if widget.isChecked() else PALETTE.text_muted,
                )
            )
        if isinstance(widget, QAbstractButton) and getattr(widget, "_icon_name", None):
            widget.setIcon(get_icon(widget._icon_name, color=widget._icon_color()))
        if hasattr(widget, "refresh_theme"):
            widget.refresh_theme()
        if isinstance(widget, FigureCanvasQTAgg):
            for artist in widget.figure.findobj():
                for getter, setter in [
                    ("get_color", "set_color"),
                    ("get_facecolor", "set_facecolor"),
                    ("get_edgecolor", "set_edgecolor"),
                ]:
                    if not hasattr(artist, getter) or not hasattr(artist, setter):
                        continue
                    try:
                        value = getattr(artist, getter)()
                        color = to_hex(value, keep_alpha=False).lower()
                        if color in mapping:
                            getattr(artist, setter)(mapping[color])
                    except (ValueError, TypeError, AttributeError):
                        pass
            widget.figure.set_facecolor(PALETTE.bg)
            for ax in widget.figure.axes:
                ax.set_facecolor(PALETTE.bg)
                legend = ax.get_legend()
                if legend:
                    legend.get_frame().set_facecolor(PALETTE.surface)
                    for text in legend.get_texts():
                        text.set_color(PALETTE.text)
            if widget.isVisible():
                widget.draw_idle()
    qss = build_qss()
    # Scale existing typography consistently, including inline widget styles.
    scale = font_size / 13

    def scale_fonts(text):
        return re.sub(
            r"font-size:\s*(\d+)px",
            lambda m: f"font-size: {round(int(m[1]) * scale)}px",
            text,
        )

    window.setStyleSheet(scale_fonts(qss))
