"""Card e componentes relacionados."""
from __future__ import annotations

from PySide6.QtCore import Qt, QEvent, QTimer
from PySide6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QWidget, QPushButton
)

from gui.icons import get_pixmap
from gui.theme import PALETTE


class Card(QFrame):
    def __init__(self, title: str | None = None, subtitle: str | None = None,
                 parent=None, padding: int = 20):
        super().__init__(parent)
        self.setObjectName("Card")
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(padding, padding, padding, padding)
        self._layout.setSpacing(16)

        if title:
            header = QVBoxLayout()
            header.setSpacing(2)
            t = QLabel(title)
            t.setWordWrap(True)
            t.setObjectName("SectionTitle")
            header.addWidget(t)
            if subtitle:
                s = QLabel(subtitle)
                s.setWordWrap(True)
                s.setObjectName("SectionSubtitle")
                header.addWidget(s)
            self._layout.addLayout(header)

    def add(self, widget: QWidget, stretch: int = 0):
        self._layout.addWidget(widget, stretch)
        return widget

    def add_layout(self, layout):
        self._layout.addLayout(layout)
        return layout

    def body(self) -> QVBoxLayout:
        return self._layout


class MetricCard(QFrame):
    def __init__(self, label: str, value: str = "—", unit: str = "",
                 accent: str | None = None, parent=None):
        super().__init__(parent)
        self.setObjectName("Card")
        self._accent = accent

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(6)

        self._label = QLabel(label)
        self._label.setWordWrap(True)
        self._label.setObjectName("MetricLabel")

        value_row = QHBoxLayout()
        value_row.setSpacing(4)

        self._value = QLabel(value)
        self._value.setObjectName("MetricValue")
        if accent:
            self._value.setStyleSheet(
                f"color: {accent};"
                "font-size: 26px;"
                "font-weight: 600;"
                "font-family: 'JetBrains Mono', 'Cascadia Code', Consolas, monospace;"
                "letter-spacing: -0.5px;"
            )

        value_row.addWidget(self._value)

        self._unit = QLabel(unit)
        self._unit.setStyleSheet(f"color: {PALETTE.text_dim}; font-size: 12px;")
        value_row.addWidget(self._unit, alignment=Qt.AlignBottom)
        value_row.addStretch()

        layout.addWidget(self._label)
        layout.addLayout(value_row)

    def set_value(self, value: str, unit: str = ""):
        self._value.setText(value)
        self._unit.setText(unit)


class MetricGrid(QWidget):
    """Distribui métricas em 4, 2 ou 1 colunas conforme espaço e tipografia."""

    def __init__(self, cards, parent=None):
        super().__init__(parent)
        self.cards = tuple(cards)
        self._columns = 0
        self._grid = QGridLayout(self)
        self._grid.setContentsMargins(0, 0, 0, 0)
        self._grid.setSpacing(16)
        self._reflow_timer = QTimer(self)
        self._reflow_timer.setSingleShot(True)
        self._reflow_timer.setInterval(0)
        self._reflow_timer.timeout.connect(self._reflow)
        self._reflow()

    def _reflow(self):
        card_width = max(200, self.fontMetrics().horizontalAdvance('Fidelidade ao circuito') + 48)
        gap = self._grid.spacing()
        columns = next((n for n in (len(self.cards), 2, 1)
                        if self.width() >= n * card_width + (n - 1) * gap), 1)
        if columns == self._columns:
            return
        while self._grid.count():
            self._grid.takeAt(0)
        for column in range(4):
            self._grid.setColumnStretch(column, 1 if column < columns else 0)
        for index, card in enumerate(self.cards):
            self._grid.addWidget(card, index // columns, index % columns)
        self._columns = columns
        self.updateGeometry()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._reflow_timer.start()

    def changeEvent(self, event):
        super().changeEvent(event)
        if event.type() in (QEvent.FontChange, QEvent.StyleChange) and hasattr(self, '_reflow_timer'):
            self._reflow_timer.start()


class EmptyState(QWidget):
    def __init__(self, icon: str, title: str, description: str = "",
                 action_text: str | None = None, parent=None):
        super().__init__(parent)

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)
        layout.setSpacing(16)
        layout.setContentsMargins(40, 40, 40, 40)

        icon_lbl = QLabel()
        icon_lbl.setFixedSize(40, 40)
        icon_lbl.setPixmap(get_pixmap(icon, color=PALETTE.text_dim, size=40))
        icon_lbl.setAlignment(Qt.AlignCenter)
        layout.addWidget(icon_lbl, alignment=Qt.AlignCenter)

        t = QLabel(title)
        t.setStyleSheet(f"color: {PALETTE.text}; font-size: 15px; font-weight: 600;")
        t.setAlignment(Qt.AlignCenter)
        layout.addWidget(t)

        if description:
            d = QLabel(description)
            d.setStyleSheet(f"color: {PALETTE.text_muted}; font-size: 13px;")
            d.setAlignment(Qt.AlignCenter)
            d.setWordWrap(True)
            d.setMaximumWidth(360)
            layout.addWidget(d, alignment=Qt.AlignCenter)

        if action_text:
            btn = QPushButton(action_text)
            btn.setObjectName("PrimaryButton")
            layout.addWidget(btn, alignment=Qt.AlignCenter)
            self.action_button = btn
