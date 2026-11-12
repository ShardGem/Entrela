"""Abas dimensionadas pelo conteúdo aberto, sem reservar outras páginas."""

from PySide6.QtCore import QSize
from PySide6.QtWidgets import QTabWidget, QSizePolicy, QStyle, QStyleOptionTabWidgetFrame


class ContentTabs(QTabWidget):
    """Evita que um texto longo oculto estique gráficos e formulários."""

    def __init__(self, parent=None):
        super().__init__(parent)
        policy = QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        policy.setHeightForWidth(True)
        self.setSizePolicy(policy)
        self.setUsesScrollButtons(True)
        self.currentChanged.connect(lambda *_: self.updateGeometry())

    def _with_chrome(self, size, minimum=False):
        bar = self.tabBar().minimumSizeHint() if minimum else self.tabBar().sizeHint()
        if not self.tabBar().isHidden():
            if self.tabPosition() in (QTabWidget.West, QTabWidget.East):
                size = QSize(size.width() + bar.width(), max(size.height(), bar.height()))
            else:
                size = QSize(max(size.width(), bar.width()), size.height() + bar.height())
        option = QStyleOptionTabWidgetFrame()
        self.initStyleOption(option)
        return self.style().sizeFromContents(QStyle.CT_TabWidget, option, size, self)

    def sizeHint(self):
        page = self.currentWidget()
        return self._with_chrome(page.sizeHint() if page else QSize(0, 0))

    def minimumSizeHint(self):
        page = self.currentWidget()
        size = page.minimumSizeHint().expandedTo(page.minimumSize()) if page else QSize(0, 0)
        return self._with_chrome(size, minimum=True)

    def heightForWidth(self, width):
        page = self.currentWidget()
        if page is None:
            return self.minimumSizeHint().height()
        height = page.heightForWidth(width) if page.hasHeightForWidth() else page.sizeHint().height()
        return self._with_chrome(QSize(width, max(page.minimumSizeHint().height(), height))).height()
