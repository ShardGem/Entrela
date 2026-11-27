"""Busca do laboratório com seleção por teclado e ações na ordem de relevância."""

from PySide6.QtCore import QEvent, QRect, QSize, Qt, Signal
from PySide6.QtGui import QColor, QFont, QFontMetrics
from PySide6.QtWidgets import (
    QDialog, QHBoxLayout, QLabel, QLineEdit, QListWidget, QListWidgetItem,
    QStyle, QStyledItemDelegate, QVBoxLayout,
)

from gui.icons import get_icon
from gui.navigation import NAV_ICONS, NAV_LABELS
from gui.pages.examples import normalized
from gui.theme import PALETTE


_CATEGORY_ROLE = Qt.UserRole + 1
_ICON_ROLE = Qt.UserRole + 2
_CATEGORIES = {
    "page": ("Área", "arrow-right"),
    "project": ("Projeto", "project-folder"),
    "run": ("Execução", "history"),
    "example": ("Exemplo", "book-stack"),
    "model": ("Modelo", "layers"),
    "help": ("Conceito", "help"),
    "concept": ("Conceito", "help"),
}


class _CommandRow(QStyledItemDelegate):
    def sizeHint(self, option, index):
        return QSize(0, max(36, option.fontMetrics.height() + 14))

    def paint(self, painter, option, index):
        selected = bool(option.state & QStyle.State_Selected)
        hovered = bool(option.state & QStyle.State_MouseOver)
        rect = option.rect.adjusted(3, 1, -3, -1)
        painter.save()
        painter.setClipRect(rect, Qt.IntersectClip)
        if selected or hovered:
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor(PALETTE.primary_faint if selected else PALETTE.surface_hover))
            painter.drawRoundedRect(rect, 6, 6)

        color = PALETTE.primary if selected else PALETTE.text_muted
        glyph = get_icon(index.data(_ICON_ROLE), color)
        glyph.paint(painter, QRect(rect.x() + 10, rect.center().y() - 8, 16, 16))
        category = index.data(_CATEGORY_ROLE)
        category_font = QFont(option.font)
        category_font.setPixelSize(max(11, option.fontMetrics.height() - 6))
        category_width = QFontMetrics(category_font).horizontalAdvance(category)
        right = rect.right() - 11
        painter.setFont(category_font)
        painter.setPen(QColor(PALETTE.text_muted))
        painter.drawText(QRect(right - category_width, rect.y(), category_width + 1, rect.height()),
                         Qt.AlignVCenter, category)

        title_rect = QRect(rect.x() + 36, rect.y(), max(0, rect.width() - category_width - 60), rect.height())
        title = option.fontMetrics.elidedText(index.data(Qt.DisplayRole), Qt.ElideRight, title_rect.width())
        painter.setFont(option.font)
        painter.setPen(QColor(PALETTE.text))
        painter.drawText(title_rect, Qt.AlignVCenter, title)
        painter.restore()


class CommandPalette(QDialog):
    command_requested = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("CommandPalette")
        self.setWindowTitle("Busca e comandos")
        self.setWindowModality(Qt.WindowModal)
        self.resize(602, 448)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 10)
        layout.setSpacing(8)

        self.search = QLineEdit()
        self.search.setObjectName("CommandQuery")
        self.search.setPlaceholderText("Buscar áreas, ações ou experimentos…")
        self.search.setAccessibleName("Buscar áreas, ações e experimentos")
        self.search.setClearButtonEnabled(True)
        self.search.installEventFilter(self)
        layout.addWidget(self.search)

        self.list = QListWidget()
        self.list.setObjectName("CommandResults")
        self.list.setAccessibleName("Resultados da busca")
        self.list.setMouseTracking(True)
        self.list.setItemDelegate(_CommandRow(self.list))
        layout.addWidget(self.list, 1)
        self.empty = QLabel("Nenhum resultado para esta busca.")
        self.empty.setObjectName("FieldHint")
        self.empty.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.empty, 1)

        footer = QHBoxLayout()
        footer.addStretch()
        for keys, label in (("↑ ↓", "Navegar"), ("Enter", "Abrir"), ("Esc", "Fechar")):
            shortcut = QLabel(keys)
            shortcut.setObjectName("CommandKey")
            footer.addWidget(shortcut)
            hint = QLabel(label)
            hint.setObjectName("FieldHint")
            footer.addWidget(hint)
            footer.addSpacing(6)
        layout.addLayout(footer)

        self._index = []
        self._recent = []
        self.search.textChanged.connect(self._filter)
        self.search.returnPressed.connect(self._activate)
        self.list.itemActivated.connect(self._activate_item)

    def open_commands(self, commands):
        self._index = [(identifier, title, normalized(title), normalized(keywords))
                       for identifier, title, keywords in commands]
        self.search.clear()
        self._filter()
        self.show()
        self.raise_()
        self.activateWindow()
        self.search.setFocus()

    def _filter(self, *_):
        query = normalized(self.search.text()).strip()
        words = query.split()
        matches = []
        for order, (identifier, title, name, keywords) in enumerate(self._index):
            terms = name + " " + keywords
            if not all(word in terms for word in words):
                continue
            if not query:
                rank = self._recent.index(identifier) if identifier in self._recent else len(self._recent)
            elif name == query:
                rank = 0
            elif name.startswith(query):
                rank = 1
            else:
                rank = 2 if all(word in name for word in words) else 3
            matches.append((rank, order, identifier, title))

        self.list.clear()
        for _, _, identifier, title in sorted(matches):
            kind, _, key = identifier.partition(":")
            category, icon = _CATEGORIES.get(kind, ("Ação", "ellipsis"))
            if kind == "page" and key in NAV_LABELS:
                icon = NAV_ICONS.get(key, key)
            item = QListWidgetItem(title)
            item.setData(Qt.UserRole, identifier)
            item.setData(_CATEGORY_ROLE, "" if not query and kind == "page" else category)
            item.setData(_ICON_ROLE, icon)
            item.setData(Qt.AccessibleDescriptionRole, category)
            self.list.addItem(item)
        self.list.setVisible(bool(matches))
        self.empty.setVisible(not matches)
        if matches:
            self.list.setCurrentRow(0)

    def eventFilter(self, watched, event):
        if watched is self.search and event.type() == QEvent.KeyPress and self.list.count():
            if event.key() in (Qt.Key_Down, Qt.Key_Up):
                step = 1 if event.key() == Qt.Key_Down else -1
                self.list.setCurrentRow((self.list.currentRow() + step) % self.list.count())
                self.list.scrollToItem(self.list.currentItem())
                return True
        return super().eventFilter(watched, event)

    def _activate(self):
        if self.list.currentItem() is not None:
            self._activate_item(self.list.currentItem())

    def _activate_item(self, item):
        identifier = item.data(Qt.UserRole)
        if identifier.startswith(("page:", "project:", "run:", "help:", "concept:")):
            self._recent = [identifier, *(key for key in self._recent if key != identifier)][:8]
        self.accept()
        self.command_requested.emit(identifier)
