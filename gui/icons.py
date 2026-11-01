"""Ícones SVG (estilo Lucide, 24x24)."""

from __future__ import annotations
from functools import lru_cache

from PySide6.QtCore import QByteArray, QRectF, Qt
from PySide6.QtGui import QIcon, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer


_BODIES = {
    "undo": '<path d="M3 7h11a6 6 0 1 1 0 12M3 7l5-5M3 7l5 5"/>',
    "redo": '<path d="M21 7H10a6 6 0 1 0 0 12M21 7l-5-5M21 7l-5 5"/>',
    "examples": '<path d="M3 3h7v7H3V3zM14 3h7v7h-7V3zM3 14h7v7H3v-7zM14 14h7v7h-7v-7z"/>',
    "comparison": '<path d="M4 20V9h5v11M15 20V4h5v16M2 20h21"/>',
    "analysis": '<path d="M3 21h18M5 17l4-6 4 3 6-10"/>',
    "library": '<path d="M3 5h7l2 3h9v12H3V5z"/>',
    "dashboard": (
        '<rect x="3" y="3" width="7.5" height="9" rx="1.5"/>'
        '<rect x="13.5" y="3" width="7.5" height="5.5" rx="1.5"/>'
        '<rect x="13.5" y="12" width="7.5" height="9" rx="1.5"/>'
        '<rect x="3" y="15.5" width="7.5" height="5.5" rx="1.5"/>'
    ),
    "simulation": (
        '<circle cx="12" cy="12" r="2"/>'
        '<ellipse cx="12" cy="12" rx="9" ry="3.8"/>'
        '<ellipse cx="12" cy="12" rx="9" ry="3.8" transform="rotate(60 12 12)"/>'
        '<ellipse cx="12" cy="12" rx="9" ry="3.8" transform="rotate(120 12 12)"/>'
    ),
    "circuit": (
        '<circle cx="5" cy="6" r="1.6"/>'
        '<circle cx="5" cy="12" r="1.6"/>'
        '<circle cx="5" cy="18" r="1.6"/>'
        '<path d="M7 6h14M7 12h5M14 12h7M7 18h14"/>'
        '<rect x="11.5" y="9.5" width="3" height="5" rx="0.5"/>'
    ),
    "results": '<path d="M4 20V10M10 20V4M16 20v-7M22 20H2"/>',
    "bloch": (
        '<circle cx="12" cy="12" r="9"/>'
        '<ellipse cx="12" cy="12" rx="9" ry="3.8"/>'
        '<ellipse cx="12" cy="12" rx="3.8" ry="9"/>'
        '<path d="M12 12l5-5"/>'
    ),
    "mitigation": (
        '<path d="M12 3l8 3v5c0 5-3.5 9.2-8 10-4.5-.8-8-5-8-10V6l8-3z"/>'
        '<path d="M9 12l2 2 4-4"/>'
    ),
    "history": '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
    "docs": (
        '<path d="M4 4a2 2 0 0 1 2-2h11a2 2 0 0 1 2 2v15l-6-3-6 3V6"/>'
        '<path d="M8 7h7M8 11h7"/>'
    ),
    "settings": (
        '<circle cx="12" cy="12" r="3"/>'
        '<path d="M19.4 15a1.7 1.7 0 0 0 .3 1.9l.1.1a2 2 0 1 1-2.8 2.8l-.1-.1a1.7 1.7 0 0 0-1.9-.3 1.7 1.7 0 0 0-1 1.5V21a2 2 0 1 1-4 0v-.1a1.7 1.7 0 0 0-1.1-1.5 1.7 1.7 0 0 0-1.9.3l-.1.1a2 2 0 1 1-2.8-2.8l.1-.1a1.7 1.7 0 0 0 .3-1.9 1.7 1.7 0 0 0-1.5-1H3a2 2 0 1 1 0-4h.1a1.7 1.7 0 0 0 1.5-1.1 1.7 1.7 0 0 0-.3-1.9l-.1-.1a2 2 0 1 1 2.8-2.8l.1.1a1.7 1.7 0 0 0 1.9.3h.1a1.7 1.7 0 0 0 1-1.5V3a2 2 0 1 1 4 0v.1a1.7 1.7 0 0 0 1 1.5 1.7 1.7 0 0 0 1.9-.3l.1-.1a2 2 0 1 1 2.8 2.8l-.1.1a1.7 1.7 0 0 0-.3 1.9v.1a1.7 1.7 0 0 0 1.5 1H21a2 2 0 1 1 0 4h-.1a1.7 1.7 0 0 0-1.5 1z"/>'
    ),
    "play": '<path d="M7 4l12 8-12 8V4z" fill="{color}" stroke="none"/>',
    "pause": (
        '<rect x="6" y="4" width="4" height="16" rx="1" fill="{color}" stroke="none"/>'
        '<rect x="14" y="4" width="4" height="16" rx="1" fill="{color}" stroke="none"/>'
    ),
    "stop": '<rect x="6" y="6" width="12" height="12" rx="1.5" fill="{color}" stroke="none"/>',
    "prev": '<path d="M15 4l-8 8 8 8"/>',
    "next": '<path d="M9 4l8 8-8 8"/>',
    "chevron-down": '<path d="M6 9l6 6 6-6"/>',
    "plus": '<path d="M12 5v14M5 12h14"/>',
    "trash": (
        '<path d="M3 6h18M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>'
        '<path d="M6 6l1 14a2 2 0 0 0 2 2h6a2 2 0 0 0 2-2l1-14"/>'
    ),
    "download": '<path d="M12 3v12M6 11l6 6 6-6M4 21h16"/>',
    "sun": (
        '<circle cx="12" cy="12" r="4"/>'
        '<path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4'
        'M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/>'
    ),
    "moon": '<path d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8z"/>',
    "info": '<circle cx="12" cy="12" r="9"/><path d="M12 11v5M12 8h.01"/>',
    "check": '<path d="M4 12l5 5L20 6"/>',
    "alert": '<path d="M12 3l10 17H2L12 3z"/><path d="M12 10v4M12 17h.01"/>',
    "close": '<path d="M6 6l12 12M6 18L18 6"/>',
}


@lru_cache(maxsize=256)
def _build_svg(name: str, color: str) -> str:
    body = _BODIES.get(name, "").format(color=color)
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" '
        f'fill="none" stroke="{color}" stroke-width="1.8" '
        f'stroke-linecap="round" stroke-linejoin="round">{body}</svg>'
    )


def get_pixmap(name: str, color: str = "#8b8b90", size: int = 20) -> QPixmap:
    """Renderiza o ícone em QPixmap do tamanho exato, com DPR=2 para HiDPI."""
    if name not in _BODIES:
        return QPixmap()

    svg = _build_svg(name, color)
    renderer = QSvgRenderer(QByteArray(svg.encode("utf-8")))

    dpr = 2.0
    physical = max(1, int(size * dpr))
    pixmap = QPixmap(physical, physical)
    pixmap.setDevicePixelRatio(dpr)
    pixmap.fill(Qt.transparent)

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing, True)
    painter.setRenderHint(QPainter.SmoothPixmapTransform, True)
    renderer.render(painter, QRectF(0, 0, size, size))
    painter.end()

    return pixmap


def get_icon(name: str, color: str = "#8b8b90", size: int = 20) -> QIcon:
    if name not in _BODIES:
        return QIcon()
    return QIcon(get_pixmap(name, color, size))
