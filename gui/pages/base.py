"""Base para todas as páginas do app."""

from __future__ import annotations

from PySide6.QtCore import Qt, QEvent
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QFrame,
)

from gui.theme import SPACING
from gui.widgets.flow_layout import FlowLayout


class PageBase(QWidget):
    def __init__(self, title: str, subtitle: str = "", parent=None):
        super().__init__(parent)
        self.setObjectName("PageSurface")
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
        self._title.setWordWrap(True)
        self._title.setObjectName("PageTitle")
        self._subtitle = QLabel(subtitle)
        self._subtitle.setWordWrap(True)
        self._subtitle.setObjectName("PageSubtitle")
        self._subtitle.setVisible(bool(subtitle))
        text_col.addWidget(self._title)
        text_col.addWidget(self._subtitle)

        header_layout.addLayout(text_col, 1)
        self._actions_slot = FlowLayout()
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

    def use_window_heading(self):
        """O título fica na barra comum; preserva descrição e ações locais."""
        self._title.hide()
        self._header.layout().setContentsMargins(20, 10, 20, 8)

    def use_workspace_context(self):
        """A seção fornece título e contexto; aqui ficam somente ações locais."""
        self._title.hide()
        self._subtitle.hide()
        self._header.layout().setContentsMargins(20, 0, 20, 6)
        self._header.setVisible(self._actions_slot.count() > 0)
        self._embedded_heading = True

    def set_title(self, title: str, subtitle: str = ""):
        self._title.setText(title)
        self._subtitle.setText(subtitle)
        self._subtitle.setVisible(bool(subtitle))

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._arrange_header()

    def showEvent(self, event):
        super().showEvent(event)
        self._arrange_header()

    def changeEvent(self, event):
        super().changeEvent(event)
        if event.type() in (QEvent.FontChange, QEvent.StyleChange) and hasattr(self, "_actions_slot"):
            self._arrange_header()

    def _arrange_header(self):
        actions = [item for item in self._actions_slot.items if not item.isEmpty()]
        action_width = sum(item.sizeHint().width() for item in actions)
        action_width += max(0, len(actions)-1) * self._actions_slot.spacing()
        narrow = self.width() < 360 * max(1,self.font().pixelSize()/15) + action_width + 72
        self._header.layout().setDirection(
            QHBoxLayout.TopToBottom if narrow else QHBoxLayout.LeftToRight
        )
        self._header.layout().setContentsMargins(20, 0 if getattr(self, '_embedded_heading', False) else 16, 20, 6 if getattr(self, '_embedded_heading', False) else 12)
        self._body.setContentsMargins(20, 8, 20, 24)
