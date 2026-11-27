"""Superfícies e hierarquia do estúdio científico, sem estado de experimento."""
from dataclasses import dataclass
from PySide6.QtWidgets import QFrame, QVBoxLayout, QLabel


@dataclass(frozen=True)
class LayoutTokens:
    page_margin: int = 26
    section_gap: int = 16
    control_gap: int = 8
    panel_padding: int = 16
    handle_width: int = 8
    frame_margin: int = 9


LAYOUT = LayoutTokens()


class Surface(QFrame):
    """Uma superfície de trabalho; não cria caixas para cada campo."""
    def __init__(self, title=None, description=None, *, role='StudioPanel', parent=None):
        super().__init__(parent)
        self.setObjectName(role)
        self._body = QVBoxLayout(self)
        self._body.setContentsMargins(LAYOUT.panel_padding, LAYOUT.section_gap,
                                      LAYOUT.panel_padding, LAYOUT.section_gap)
        self._body.setSpacing(LAYOUT.control_gap)
        if title:
            heading = QLabel(title)
            heading.setObjectName('PanelTitle')
            heading.setWordWrap(True)
            self._body.addWidget(heading)
        if description:
            hint = QLabel(description)
            hint.setObjectName('FieldHint')
            hint.setWordWrap(True)
            self._body.addWidget(hint)

    def body(self):
        return self._body

    def add(self, widget, stretch=0):
        self._body.addWidget(widget, stretch)
        return widget
