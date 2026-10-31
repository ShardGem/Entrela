"""Botões com hierarquia visual clara."""
from __future__ import annotations

from PySide6.QtCore import QSize, Qt
from PySide6.QtWidgets import QPushButton

from gui.icons import get_icon
from gui.theme import PALETTE


class _BaseButton(QPushButton):
    def __init__(self, text: str = "", icon: str | None = None, parent=None):
        super().__init__(text, parent)
        self.setCursor(Qt.PointingHandCursor)
        self._icon_name = icon
        self.setIconSize(QSize(16, 16))
        if icon:
            self.setIcon(get_icon(icon, color=self._icon_color(), size=16))
            self.setIconSize(QSize(16, 16))

    def _icon_color(self) -> str:
        return PALETTE.text


class PrimaryButton(_BaseButton):
    def __init__(self, text="", icon=None, parent=None):
        super().__init__(text, icon, parent)
        self.setObjectName("PrimaryButton")

    def _icon_color(self) -> str:
        return PALETTE.text_on_primary


class SecondaryButton(_BaseButton):
    def __init__(self, text="", icon=None, parent=None):
        super().__init__(text, icon, parent)


class GhostButton(_BaseButton):
    def __init__(self, text="", icon=None, parent=None):
        super().__init__(text, icon, parent)
        self.setObjectName("GhostButton")


class DangerButton(_BaseButton):
    def __init__(self, text="", icon=None, parent=None):
        super().__init__(text, icon, parent)
        self.setObjectName("DangerButton")

    def _icon_color(self) -> str:
        return PALETTE.danger
