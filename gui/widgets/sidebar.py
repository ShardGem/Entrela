"""Sidebar de navegação principal."""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal, QSize
from PySide6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QPushButton, QLabel
)

from gui.icons import get_icon, get_pixmap
from gui.theme import PALETTE


class NavButton(QPushButton):
    def __init__(self, icon_name: str, label: str, parent=None):
        super().__init__(parent)
        self.icon_name = icon_name
        self.setObjectName("NavButton")
        self.setCheckable(True)
        self.setAutoExclusive(False)
        self.setCursor(Qt.PointingHandCursor)
        self.setMinimumHeight(34)
        self.setIconSize(QSize(16, 16))
        self.setText(f"   {label}")
        self._refresh_icon()

    def _refresh_icon(self):
        color = PALETTE.primary if self.isChecked() else PALETTE.text_muted
        self.setIcon(get_icon(self.icon_name, color=color, size=16))
        self.setIconSize(QSize(16, 16))

    def setChecked(self, checked: bool):
        super().setChecked(checked)
        self._refresh_icon()


class Sidebar(QFrame):
    navigate = Signal(str)

    ITEMS = [
        ("dashboard",  "Início"),
        ("examples",   "Exemplos"),
        ("simulation", "Simulação"),
        ("circuit",    "Circuito"),
        ("results",    "Resultados"),
        ("bloch",      "Evolução 3D"),
        ("mitigation", "Mitigação"),
        ("comparison", "Comparações"),
        ("history",    "Histórico"),
        ("docs",       "Aprender"),
        ("settings",   "Configurações"),
    ]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("Sidebar")
        self.setFixedWidth(200)
        self.buttons: dict[str, NavButton] = {}
        self._build()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 16, 12, 16)
        layout.setSpacing(2)

        logo_row = QHBoxLayout()
        logo_row.setContentsMargins(8, 0, 8, 20)
        logo_row.setSpacing(10)

        logo = QLabel()
        logo.setFixedSize(20, 20)
        logo.setPixmap(get_pixmap("simulation", color=PALETTE.primary, size=20))

        title = QLabel("Entrela")
        title.setObjectName("SidebarLogo")

        logo_row.addWidget(logo)
        logo_row.addWidget(title)
        logo_row.addStretch()
        layout.addLayout(logo_row)

        for key, label in self.ITEMS:
            btn = NavButton(key, label)
            btn.clicked.connect(lambda _=False, k=key: self._on_click(k))
            layout.addWidget(btn)
            self.buttons[key] = btn

        layout.addStretch()

    def _on_click(self, key: str):
        self.set_active(key)
        self.navigate.emit(key)

    def set_active(self, key: str):
        for k, btn in self.buttons.items():
            btn.setChecked(k == key)
