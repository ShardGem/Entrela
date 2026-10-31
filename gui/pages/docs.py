"""Manual integrado."""
from __future__ import annotations

from PySide6.QtWidgets import QTextBrowser

from gui.pages.base import PageBase


class DocsPage(PageBase):
    def __init__(self, html: str, parent=None):
        super().__init__(
            "Manual",
            "Documentação integrada do Entrela.",
        )
        self.browser = QTextBrowser()
        self.browser.setOpenExternalLinks(True)
        self.browser.setHtml(html)
        self.body().addWidget(self.browser, 1)

    def scroll_to(self, anchor: str):
        self.browser.scrollToAnchor(anchor)
