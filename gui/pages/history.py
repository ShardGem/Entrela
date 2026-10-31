from PySide6.QtCore import Signal,Qt
from PySide6.QtWidgets import QTableWidget,QTableWidgetItem,QHeaderView,QLineEdit
from gui.pages.base import PageBase
class HistoryPage(PageBase):
    experiment_selected=Signal(str)
    experiment_deleted=Signal(str)
    def __init__(self,parent=None):
        super().__init__("Histórico","Duplo clique para reabrir configuração, estados e resultados.",parent)
        self.search=QLineEdit()
        self.search.setPlaceholderText("Buscar identificador, modelo, ruído ou estado…")
        self.body().addWidget(self.search)
        self.table=QTableWidget(0,7)
        self.table.setHorizontalHeaderLabels(["Data / fuso","Identificador","Modelo","Qubits","Ruído","Fidelidade","Estado"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.cellDoubleClicked.connect(self._open)
        self.body().addWidget(self.table,1)
        self.records=[]
        self.search.textChanged.connect(self._filter)
    def load(self,experiments):
        self.records=list(experiments)
        self._filter()
    def _filter(self,*_):
        query=self.search.text().casefold()
        self.table.setRowCount(0)
        for exp in self.records:
            status="Falhou" if exp.result.error else ("ZNE" if exp.result.mitigation else "Concluído")
            values=[exp.created_at.strftime("%d/%m/%Y %H:%M %z"),exp.id,exp.config.system.hamiltonian,
                    str(exp.config.system.num_qubits),exp.config.noise.kind if exp.config.noise.enabled else "Ideal",
                    "—" if exp.result.fidelity is None else f"{exp.result.fidelity:.4f}",status]
            if query not in " ".join(values).casefold():continue
            row=self.table.rowCount()
            self.table.insertRow(row)
            for col,text in enumerate(values):
                item=QTableWidgetItem(text)
                if col==0:item.setData(Qt.UserRole,exp.id)
                self.table.setItem(row,col,item)
    def _open(self,row,column):
        item=self.table.item(row,0)
        if item:self.experiment_selected.emit(item.data(Qt.UserRole))
