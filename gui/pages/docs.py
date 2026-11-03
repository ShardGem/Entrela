"""Searchable scientific concepts beside the platform's operational manual."""
from __future__ import annotations

import unicodedata

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QListWidget,
    QListWidgetItem, QTextBrowser, QPushButton, QLabel, QSplitter,
)

from core.learning import CONCEPTS, CONCEPT_BY_KEY
from gui.pages.base import PageBase


def _search_key(text):
    return "".join(
        char for char in unicodedata.normalize("NFKD", str(text).casefold())
        if not unicodedata.combining(char)
    )


class DocsPage(PageBase):
    demonstration_requested = Signal(object)

    def __init__(self, html: str, parent=None):
        super().__init__(
            "Aprender e consultar",
            "Conceitos, circuitos demonstrativos e um manual para interpretar suas simulações.",
            parent,
        )
        self._manual_html = html
        self._selected_key = "manual"
        # Both panes own their scrolling. The page itself must not add a second
        # vertical scroll area around the same content.
        self._scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.splitter = QSplitter(Qt.Horizontal)
        self.splitter.setHandleWidth(6)
        self.splitter.setChildrenCollapsible(False)
        master = QWidget()
        master.setMinimumWidth(210)
        left = QVBoxLayout(master)
        left.setContentsMargins(0, 0, 0, 0)
        left.setSpacing(10)
        self.search = QLineEdit()
        self.search.setPlaceholderText("Buscar conceito ou assunto…")
        self.search.setAccessibleName("Buscar conceitos e manual")
        self.search.setClearButtonEnabled(True)
        left.addWidget(self.search)
        self.concept_list = QListWidget()
        self.concept_list.setAccessibleName("Conceitos científicos")
        self.concept_list.setWordWrap(True)
        self.concept_list.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.concept_list.setMinimumHeight(130)
        left.addWidget(self.concept_list, 1)
        self.empty_label = QLabel("Nenhum conceito encontrado. Tente outra palavra.")
        self.empty_label.setWordWrap(True)
        self.empty_label.hide()
        left.addWidget(self.empty_label)
        self.splitter.addWidget(master)
        detail = QWidget()
        detail.setMinimumWidth(230)
        right = QVBoxLayout(detail)
        right.setContentsMargins(0, 0, 0, 0)
        right.setSpacing(10)
        self.browser = QTextBrowser()
        self.browser.setAccessibleName("Explicação do conceito selecionado")
        self.browser.setOpenExternalLinks(False)
        self.browser.setMinimumHeight(180)
        right.addWidget(self.browser, 1)
        action = QHBoxLayout()
        self.demo_button = QPushButton("Abrir circuito demonstrativo")
        self.demo_button.setObjectName("PrimaryButton")
        self.demo_button.setToolTip(
            "Abre um circuito no editor. Execute-o para produzir seus próprios resultados."
        )
        action.addWidget(self.demo_button)
        action.addStretch(1)
        right.addLayout(action)
        self.splitter.addWidget(detail)
        self.splitter.setSizes([270, 740])
        self.body().addWidget(self.splitter, 1)
        self.search.textChanged.connect(self._filter)
        self.concept_list.currentItemChanged.connect(self._select)
        self.demo_button.clicked.connect(self._open_demonstration)
        self._filter("")

    def _filter(self, query):
        selected = self._selected_key
        needle = _search_key(query.strip())
        self.concept_list.blockSignals(True)
        self.concept_list.clear()
        entries = [("manual", "Manual da plataforma", "Uso e interpretação", "manual ajuda plataforma exportacao configuracao comparacoes")]
        entries.extend(
            (concept.key, concept.title, concept.category, concept.search_text())
            for concept in CONCEPTS
        )
        current = None
        for key, title, category, searchable in entries:
            if needle and needle not in _search_key(searchable + " " + title):
                continue
            item = QListWidgetItem(f"{title}\n{category}")
            item.setData(Qt.UserRole, key)
            item.setToolTip(title + " — " + category)
            self.concept_list.addItem(item)
            if key == selected:
                current = item
        if current is None and self.concept_list.count():
            current = self.concept_list.item(0)
        self.concept_list.setCurrentItem(current)
        self.concept_list.blockSignals(False)
        self.empty_label.setVisible(current is None)
        self._select(current)

    def _select(self, item, previous=None):
        if item is None:
            self._selected_key = ""
            self.browser.setHtml("<h1>Nenhum conceito encontrado</h1><p>Limpe a busca para consultar todos os assuntos.</p>")
            self.demo_button.hide()
            return
        self._selected_key = item.data(Qt.UserRole)
        concept = CONCEPT_BY_KEY.get(self._selected_key)
        self.browser.setHtml(concept.to_html() if concept else self._manual_html)
        self.demo_button.setVisible(bool(concept and concept.demonstration is not None))

    def _open_demonstration(self):
        concept = CONCEPT_BY_KEY.get(self._selected_key)
        if concept is not None and concept.demonstration is not None:
            self.demonstration_requested.emit(concept.demonstration)

    def scroll_to(self, anchor: str):
        """Preserve contextual manual navigation used by previous versions."""
        self.search.clear()
        self.concept_list.setCurrentRow(0)
        self.browser.scrollToAnchor(anchor)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        direction = Qt.Vertical if self.width() < 820 else Qt.Horizontal
        if self.splitter.orientation() != direction:
            self.splitter.setOrientation(direction)
            self.splitter.setSizes([190, 450] if direction == Qt.Vertical else [270, 740])
