from PySide6.QtCore import Signal,Qt
from PySide6.QtWidgets import QDialog,QVBoxLayout,QLineEdit,QListWidget,QListWidgetItem,QLabel
from gui.pages.examples import normalized
class CommandPalette(QDialog):
    command_requested=Signal(str)
    def __init__(self,parent=None):
        super().__init__(parent)
        self.setWindowTitle("Comandos e conceitos")
        self.resize(620,430)
        layout=QVBoxLayout(self)
        self.search=QLineEdit()
        self.search.setPlaceholderText("Buscar comando, exemplo ou conceito…")
        self.search.setAccessibleName("Buscar comandos e conceitos")
        self.list=QListWidget()
        self.empty=QLabel("Nenhum resultado. Tente Bell ou fidelidade.")
        for w in (self.search,self.list,self.empty):layout.addWidget(w)
        self.commands=[]
        self.search.textChanged.connect(self._filter)
        self.search.returnPressed.connect(self._activate)
        self.list.itemActivated.connect(lambda _:self._activate())
    def open_commands(self,commands):
        self.commands=commands
        self.search.clear()
        self._filter()
        self.show()
        self.raise_()
        self.activateWindow()
        self.search.setFocus()
    def _filter(self,*_):
        query=normalized(self.search.text())
        self.list.clear()
        for identifier,title,keywords in self.commands:
            if all(word in normalized(title+" "+keywords) for word in query.split()):
                item=QListWidgetItem(title)
                item.setData(Qt.UserRole,identifier)
                self.list.addItem(item)
        self.empty.setVisible(not self.list.count())
        if self.list.count():self.list.setCurrentRow(0)
    def _activate(self):
        item=self.list.currentItem()
        if item:
            self.accept()
            self.command_requested.emit(item.data(Qt.UserRole))
