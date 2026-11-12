"""Recolor live Qt and Matplotlib components using the shared palette."""

from dataclasses import asdict
import re
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication, QWidget, QAbstractButton, QTextBrowser, QTableView, QLayout
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.colors import to_hex
from gui.theme import PALETTE, build_qss
from gui.palettes import DARK, LIGHT, NAVY, THEMES
from gui.icons import get_icon
from gui.widgets.data_table import table_row_height

ACCENTS = {
    "cyan": (("#58d6ff", "#7ee0ff", "#3fb8e6", "#0d2933"), ("#006e96", "#005779", "#00415c", "#d8eff9")),
    "blue": (("#8ab4ff", "#b0ceff", "#6895df", "#142641"), ("#2457ab", "#19478e", "#11376f", "#e1ebfd")),
    "violet": (("#c1a4ff", "#dac7ff", "#a182df", "#2a1c42"), ("#7340b6", "#60329c", "#4e2780", "#f0e5fb")),
    "green": (("#70dfa6", "#a0efc6", "#4abf88", "#123126"), ("#176b44", "#105838", "#09462b", "#def3e8")),
}


def resolve_theme(theme):
    """Resolve the system preference without changing experiment data."""
    if theme != "auto":
        return theme if theme in THEMES else "dark"
    app = QApplication.instance()
    return "light" if app and app.styleHints().colorScheme() == Qt.ColorScheme.Light else "dark"


def _rich_text_template(html, default_font, dpi, names):
    """Keep semantic HTML while making inherited Qt fonts relative to the UI.

    Serializing a document after changing its default font makes Qt insert the
    old font into every paragraph. Capture before the change and remove only
    the serialized body's inherited family/size. Explicit inline sizes retain
    their ratio, while headings, math, anchors and tables remain intact.
    """
    base = default_font.pixelSize()
    if base <= 0:
        base = default_font.pointSizeF() * dpi / 72
    base = max(1., base)

    def body(match):
        return re.sub(r"font-(?:family|size):[^;\"]*;?", "", match[0], flags=re.I)

    html = re.sub(r'<body\b[^>]*>', body, html, flags=re.I)

    def size(match):
        pixels = float(match[1]) * (dpi / 72 if match[2].lower() == 'pt' else 1)
        return 'font-size: @font:' + str(pixels / base) + '@px'

    html = re.sub(r'font-size:\s*([\d.]+)(pt|px)', size, html, flags=re.I)
    return re.sub(r'#[0-9a-fA-F]{6}', lambda match: '@' + names[match[0].lower()] + '@' if match[0].lower() in names else '@primary@' if match[0].lower() == '#0000ff' else match[0], html)


def apply_appearance(window, theme="dark", font_size=15, *, accent="theme", density="comfortable", reduce_motion=False, high_contrast=False):
    theme = resolve_theme(theme)
    before = asdict(PALETTE)
    after = dict(THEMES[theme])
    if accent in ACCENTS:
        primary, hover, pressed, muted = ACCENTS[accent][theme == "light"]
        after.update(primary=primary, primary_hover=hover, primary_pressed=pressed,
                     primary_muted=muted, primary_faint=muted)
    if high_contrast:
        after.update(text="#ffffff" if theme != "light" else "#000000",
                     text_muted="#d7e0ed" if theme != "light" else "#263b53",
                     text_dim="#c1d0e1" if theme != "light" else "#334d69",
                     border="#8295ad" if theme != "light" else "#657a92",
                     border_strong="#b6c6da" if theme != "light" else "#3d536e")
    app = QApplication.instance()
    if app:
        app.setProperty("entrelaReduceMotion", bool(reduce_motion))
        app.setProperty("entrelaDensity", density)
        app.setProperty("entrelaFontSize", int(font_size))
    window.setProperty("entrelaTheme", theme)
    # Capture before setFont/QSS can serialize the previous font into spans.
    browsers = {
        browser: (browser.toHtml(), browser.document().defaultFont(),
                  browser.verticalScrollBar().value(), browser.horizontalScrollBar().value())
        for browser in window.findChildren(QTextBrowser)
    }
    font = window.font()
    font.setPixelSize(int(font_size))
    font.setStyleStrategy(QFont.PreferAntialias)
    window.setFont(font)
    # Same singleton is imported throughout the GUI.
    names = {value.lower(): key for key, value in reversed(tuple(before.items()))}
    mapping = {value: after[key] for value, key in names.items()}
    for key, value in after.items():
        object.__setattr__(PALETTE, key, value)

    for widget in window.findChildren(QWidget):
        if isinstance(widget, QTableView):
            widget.verticalHeader().setDefaultSectionSize(table_row_height(widget, density, font_size))
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
            html, previous_font, vertical, horizontal = browsers[widget]
            if html != widget.property('entrelaHtmlApplied'):
                widget.setProperty('entrelaHtmlTemplate', _rich_text_template(html, previous_font, widget.logicalDpiY(), names))
            template = widget.property('entrelaHtmlTemplate') or html
            rendered = re.sub(r'@font:([\d.eE+-]+)@', lambda match: str(round(float(match[1]) * font_size, 3)), template)
            rendered = re.sub(r'@([a-z0-9_]+)@', lambda match: after.get(match[1], match[0]), rendered)
            document = widget.document()
            document_font = QFont(window.font())
            document_font.setPixelSize(font_size)
            document.setDefaultFont(document_font)
            document.setDefaultStyleSheet(f'body {{ color: {PALETTE.text}; }} a {{ color: {PALETTE.primary}; }}')
            widget.setHtml(rendered)
            widget.verticalScrollBar().setValue(vertical)
            widget.horizontalScrollBar().setValue(horizontal)
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
            if hasattr(widget, "set_interface_font_size"):
                widget.set_interface_font_size(font_size)
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
    spacing_scale = {"compact": .75, "comfortable": 1., "spacious": 1.25}.get(density, 1.)
    for layout in window.findChildren(QLayout):
        initial = layout.property("entrelaOriginalSpacing")
        if initial is None:
            initial = layout.spacing()
            layout.setProperty("entrelaOriginalSpacing", initial)
        if initial >= 0:
            layout.setSpacing(round(initial * spacing_scale))
    qss = build_qss(density=density)
    # Scale existing typography consistently, including inline widget styles.
    scale = font_size / 13

    def scale_fonts(text):
        return re.sub(
            r"font-size:\s*(\d+)px",
            lambda m: f"font-size: {round(int(m[1]) * scale)}px",
            text,
        )

    window.setStyleSheet(scale_fonts(qss))
    for browser in browsers:
        browser.setProperty('entrelaHtmlApplied', browser.toHtml())
