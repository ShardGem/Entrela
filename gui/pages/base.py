"""Base para todas as páginas do app."""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QScrollArea, QFrame
)

from gui.theme import PALETTE, SPACING


class PageBase(QWidget):
    def __init__(self, title: str, subtitle: str = "", parent=None):
        super().__init__(parent)
        self._root = QVBoxLayout(self)
        self._root.setContentsMargins(0, 0, 0, 0)
        self._root.setSpacing(0)

        # Header
        self._header = QWidget()
        header_layout = QHBoxLayout(self._header)
        header_layout.setContentsMargins(32, 24, 32, 16)
        header_layout.setSpacing(16)

        text_col = QVBoxLayout()
        text_col.setSpacing(2)
        self._title = QLabel(title)
        self._title.setObjectName("PageTitle")
        self._subtitle = QLabel(subtitle)
        self._subtitle.setObjectName("PageSubtitle")
        self._subtitle.setVisible(bool(subtitle))
        text_col.addWidget(self._title)
        text_col.addWidget(self._subtitle)

        header_layout.addLayout(text_col)
        header_layout.addStretch()
        self._actions_slot = QHBoxLayout()
        self._actions_slot.setSpacing(SPACING.sm)
        header_layout.addLayout(self._actions_slot)

        self._root.addWidget(self._header)

        # Body
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QFrame.NoFrame)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self._body_widget = QWidget()
        self._body = QVBoxLayout(self._body_widget)
        self._body.setContentsMargins(32, 8, 32, 32)
        self._body.setSpacing(SPACING.xl)
        self._scroll.setWidget(self._body_widget)

        self._root.addWidget(self._scroll, 1)

    def add_action(self, widget: QWidget):
        self._actions_slot.addWidget(widget)

    def body(self) -> QVBoxLayout:
        return self._body

    def set_title(self, title: str, subtitle: str = ""):
        self._title.setText(title)
        self._subtitle.setText(subtitle)
        self._subtitle.setVisible(bool(subtitle))
