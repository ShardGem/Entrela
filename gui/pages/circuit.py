from PySide6.QtWidgets import QPlainTextEdit
from PySide6.QtGui import QFont
from gui.pages.base import PageBase
class CircuitPage(PageBase):
    def __init__(self,parent=None):
        super().__init__("Circuito","Preparação, evolução e medições da execução.",parent)
        self.viewer=QPlainTextEdit()
        self.viewer.setReadOnly(True)
        self.viewer.setLineWrapMode(QPlainTextEdit.NoWrap)
        self.viewer.setFont(QFont("monospace",10))
        self.body().addWidget(self.viewer,1)
        self.show_circuit("")
    def show_circuit(self,text):
        self.viewer.setPlainText(text or "Execute ou abra um experimento para ver o circuito.")
