from PySide6.QtCore import Signal, Qt
from PySide6.QtWidgets import QLabel,QCheckBox,QSpinBox,QFormLayout,QHBoxLayout,QTableWidget,QTableWidgetItem,QHeaderView,QProgressBar
from gui.pages.base import PageBase
from gui.widgets.button import PrimaryButton,SecondaryButton


class DocumentationPage(PageBase):
    export_requested=Signal(str)
    cancel_requested=Signal()
    comparison_changed=Signal()
    analysis_selected=Signal(str,str)

    def __init__(self,parent=None):
        super().__init__("Documentação e evidências","Exporte dados, figuras, animações e a origem de cada resultado.",parent)
        self.context=QLabel("Abra uma execução para documentar.")
        self.context.setWordWrap(True)
        self.body().addWidget(self.context)
        self.use_comparison=QCheckBox("Documentar as duas execuções da página Comparações")
        self.use_comparison.toggled.connect(lambda *_:self.comparison_changed.emit())
        self.include_analyses=QCheckBox("Incluir todas as análises salvas das fontes")
        self.include_analyses.setChecked(True)
        self.include_gif=QCheckBox("Incluir GIF e sequência PNG de Bloch quando houver snapshots compatíveis")
        self.include_gif.setChecked(True)
        for widget in (self.use_comparison,self.include_analyses,self.include_gif):
            self.body().addWidget(widget)
        form=QFormLayout()
        self.max_frames=QSpinBox()
        self.max_frames.setRange(2,80)
        self.max_frames.setValue(30)
        self.frame_ms=QSpinBox()
        self.frame_ms.setRange(100,3000)
        self.frame_ms.setValue(350)
        self.frame_ms.setSuffix(" ms")
        form.addRow("Máximo de snapshots no GIF",self.max_frames)
        form.addRow("Duração didática de cada quadro",self.frame_ms)
        self.body().addLayout(form)
        note=QLabel("O pacote contém JSON com estados completos, CSV, tabelas LaTeX, gráficos PNG/SVG/PDF, esferas de Bloch, PDF e manifesto com hashes. GIFs usam somente snapshots reais e enquadramento padronizado; a vista atual da página 3D pode ser exportada separadamente. Imagens não demonstram sozinhas emaranhamento nem substituem os dados brutos.")
        note.setWordWrap(True)
        self.body().addWidget(note)
        buttons=QHBoxLayout()
        self.buttons=[]
        for text,kind in (("Pacote completo ZIP","zip"),("Relatório PDF","pdf"),("Animação GIF","gif")):
            button=PrimaryButton(text) if kind=="zip" else SecondaryButton(text)
            button.clicked.connect(lambda checked=False,kind=kind:self.export_requested.emit(kind))
            buttons.addWidget(button)
            self.buttons.append(button)
        self.cancel=SecondaryButton("Cancelar exportação")
        self.cancel.clicked.connect(self.cancel_requested.emit)
        buttons.addWidget(self.cancel)
        self.body().addLayout(buttons)
        self.progress=QProgressBar()
        self.body().addWidget(self.progress)
        self.message=QLabel()
        self.message.setWordWrap(True)
        self.body().addWidget(self.message)
        self.table=QTableWidget(0,5)
        self.table.setHorizontalHeaderLabels(["Origem","Resultado / protocolo","Tipo","Referência no TCC","Data"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setMinimumHeight(220)
        self.table.cellDoubleClicked.connect(self._open)
        self.body().addWidget(self.table)
        self.set_running(False)

    def _open(self,row,column):
        data=self.table.item(row,0).data(Qt.UserRole)
        if data:
            self.analysis_selected.emit(*data)

    def set_lineage(self,sources,analyses,protocols):
        self.context.setText("Fontes: "+" · ".join(f"{e.id} ({e.config.system.num_qubits} qubits)" for e in sources) if sources else "Abra uma execução ou carregue uma comparação com estados completos.")
        self.table.setRowCount(0)
        records=[]
        for source in sources:
            parent=(source.result.mitigation or {}).get("source_experiment_id") or source.result.metadata.get("reproduced_from_id") or source.result.metadata.get("imported_from_id") or "original"
            records.append(([parent,source.id,"Execução","",source.created_at.isoformat()],None))
        for data,path in analyses:
            records.append(([data.get("source_id",""),data.get("analysis_id",_path_name(path)),data["kind"],data.get("protocol",{}).get("fields",{}).get("evidence_ref",""),data.get("created_at","")],(data["source_id"],str(path))))
        for data in protocols:
            records.append(([data["source_id"],data["fields"]["title"]+" · "+data["protocol_id"],"Protocolo",data["fields"].get("evidence_ref",""),data["created_at"]],None))
        for values,payload in records:
            row=self.table.rowCount()
            self.table.insertRow(row)
            for col,value in enumerate(values):
                item=QTableWidgetItem(str(value))
                if col==0:
                    item.setData(Qt.UserRole,payload)
                self.table.setItem(row,col,item)

    def set_running(self,running):
        for widget in (*self.buttons,self.use_comparison,self.include_analyses,self.include_gif,self.max_frames,self.frame_ms):
            widget.setEnabled(not running)
        self.cancel.setVisible(running)
        self.progress.setVisible(running)
        if running:
            self.progress.setValue(0)


def _path_name(path):
    from pathlib import Path
    return Path(path).stem
