from PySide6.QtCore import Signal, Qt
from PySide6.QtWidgets import QLabel,QCheckBox,QSpinBox,QFormLayout,QHBoxLayout,QTableWidget,QTableWidgetItem,QHeaderView,QProgressBar,QComboBox,QGroupBox,QVBoxLayout,QWidget,QDialog,QScrollArea,QFrame
from gui.pages.base import PageBase
from gui.widgets.button import PrimaryButton,SecondaryButton
from gui.formatting import timestamp


class DocumentationPage(PageBase):
    import_requested=Signal()
    export_requested=Signal(str)
    cancel_requested=Signal()
    comparison_changed=Signal()
    analysis_selected=Signal(str,str)

    def __init__(self,parent=None):
        super().__init__("Documentação e evidências","Exporte dados, figuras, animações e a origem de cada resultado.",parent)
        self.context=QLabel("Abra uma execução para documentar.")
        self.import_button=SecondaryButton("Importar estudo ZIP")
        self.import_button.setToolTip("Verifica os hashes do pacote completo e importa execuções, análises, protocolos e anotações como cópias independentes.")
        self.import_button.clicked.connect(self.import_requested.emit)
        self.add_action(self.import_button)
        self.context.setWordWrap(True)
        self.body().addWidget(self.context)
        self.prepare_export = PrimaryButton('Exportar ou gerar relatório…')
        self.prepare_export.clicked.connect(lambda: self.open_export())
        self.add_action(self.prepare_export)
        self.export_dialog = QDialog(self)
        self.export_dialog.setWindowTitle('Documentar a seleção · Entrela')
        self.export_dialog.resize(850, 680)
        outer = QVBoxLayout(self.export_dialog)
        self.format = QComboBox()
        for label, key in [('Relatório científico PDF', 'pdf'), ('Pacote completo de evidências ZIP', 'zip'), ('Animação dos snapshots GIF', 'gif')]:
            self.format.addItem(label, key)
        self.format.setAccessibleName('Formato e finalidade da exportação')
        self.dialog_context = QLabel()
        self.dialog_context.setWordWrap(True)
        outer.addWidget(self.dialog_context)
        outer.addWidget(self.format)
        area = QScrollArea()
        area.setFrameShape(QFrame.NoFrame)
        area.setWidgetResizable(True)
        area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        content_widget = QWidget()
        options = QVBoxLayout(content_widget)
        area.setWidget(content_widget)
        outer.addWidget(area, 1)
        self.use_comparison=QCheckBox("Documentar as duas execuções da página Comparações")
        self.use_comparison.toggled.connect(lambda *_:self.comparison_changed.emit())
        self.include_analyses=QCheckBox("Incluir todas as análises salvas das fontes")
        self.include_analyses.setChecked(True)
        self.include_gif=QCheckBox("Incluir GIF e sequência PNG de Bloch quando houver snapshots compatíveis")
        self.include_gif.setChecked(True)
        for widget in (self.use_comparison,self.include_analyses,self.include_gif):
            options.addWidget(widget)
        content=QGroupBox("Conteúdo do relatório PDF")
        self.report_group=content
        content_layout=QVBoxLayout(content)
        self.report_template=QComboBox()
        self.report_template.addItem("Completo · metodologia, resultados e reprodução","complete")
        self.report_template.addItem("Resumido · principais resultados","summary")
        content_layout.addWidget(self.report_template)
        self.report_sections={}
        for key,label in (("include_distribution","Distribuição das medições"),
                          ("include_temporal","Curvas dos snapshots registrados"),
                          ("include_bloch","Estados locais de Bloch"),
                          ("include_circuit","Diagrama do circuito"),
                          ("include_configuration","Configuração e proveniência técnica"),
                          ("include_analyses","Gráficos e tabelas dos estudos")):
            checkbox=QCheckBox(label)
            checkbox.setChecked(True)
            self.report_sections[key]=checkbox
            content_layout.addWidget(checkbox)
        self.report_template.currentIndexChanged.connect(self._apply_template)
        options.addWidget(content)
        animation=QWidget()
        self.animation_options=animation
        form=QFormLayout(animation)
        self.max_frames=QSpinBox()
        self.max_frames.setRange(2,80)
        self.max_frames.setValue(30)
        self.frame_ms=QSpinBox()
        self.frame_ms.setRange(100,3000)
        self.frame_ms.setValue(350)
        self.frame_ms.setSuffix(" ms")
        form.addRow("Máximo de snapshots no GIF",self.max_frames)
        form.addRow("Duração didática de cada quadro",self.frame_ms)
        options.addWidget(animation)
        note=QLabel("O pacote contém JSON com estados completos, CSV, tabelas LaTeX, gráficos PNG/SVG/PDF, esferas de Bloch, PDF e manifesto com hashes. GIFs usam somente snapshots reais e enquadramento padronizado; a vista atual da página 3D pode ser exportada separadamente. Imagens não demonstram sozinhas emaranhamento nem substituem os dados brutos.")
        note.setWordWrap(True)
        options.addWidget(note)
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
        self.generate = PrimaryButton('Gerar relatório PDF…')
        self.generate.clicked.connect(self._generate)
        options.addWidget(self.generate)
        for button in self.buttons:
            button.setParent(self)
            button.hide()
        options.addWidget(self.cancel)
        self.progress=QProgressBar()
        self.body().addWidget(self.progress)
        self.message=QLabel()
        self.message.setWordWrap(True)
        self.body().addWidget(self.message)
        self.close_setup = SecondaryButton('Fechar')
        self.close_setup.clicked.connect(self.export_dialog.reject)
        outer.addWidget(self.close_setup)
        self.table=QTableWidget(0,5)
        self.table.setHorizontalHeaderLabels(["Origem","Resultado / protocolo","Tipo","Referência no TCC","Data"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setMinimumHeight(220)
        self.table.cellDoubleClicked.connect(self._open)
        self.body().addWidget(self.table)
        self.format.currentIndexChanged.connect(self._format_changed)
        self.include_gif.toggled.connect(self._format_changed)
        self._format_changed()
        self.set_running(False)

    def open_export(self, kind=None):
        if kind is not None:
            self.format.setCurrentIndex(max(0, self.format.findData(kind)))
        self.export_dialog.open()

    def _format_changed(self, *_):
        kind = self.format.currentData()
        self.report_group.setVisible(kind in ('pdf', 'zip'))
        self.include_analyses.setVisible(kind != 'gif')
        self.include_gif.setVisible(kind == 'zip')
        self.animation_options.setVisible(kind == 'gif' or (kind == 'zip' and self.include_gif.isChecked()))
        self.generate.setText({'pdf':'Gerar relatório PDF…', 'zip':'Exportar pacote completo ZIP…', 'gif':'Gerar animação GIF…'}[kind])

    def _generate(self):
        kind = self.format.currentData()
        self.export_dialog.hide()
        self.export_requested.emit(kind)

    def _open(self,row,column):
        data=self.table.item(row,0).data(Qt.UserRole)
        if data:
            self.analysis_selected.emit(*data)

    def _apply_template(self):
        complete=self.report_template.currentData()=="complete"
        for key,widget in self.report_sections.items():
            widget.setChecked(complete or key not in ("include_circuit","include_configuration"))

    def report_options(self):
        return dict(template=self.report_template.currentData(),
                    **{key:widget.isChecked() for key,widget in self.report_sections.items()})

    def apply_report_options(self,mapping):
        from PySide6.QtCore import QSignalBlocker
        from core.pdf_layout import report_options
        from dataclasses import asdict
        resolved=asdict(report_options(mapping))
        blockers=[QSignalBlocker(widget) for widget in (self.report_template,*self.report_sections.values())]
        self.report_template.setCurrentIndex(self.report_template.findData(resolved["template"]))
        for key,widget in self.report_sections.items():
            widget.setChecked(resolved[key])
        del blockers

    def set_lineage(self,sources,analyses,protocols,annotations=None):
        from data.workspace import experiment_title
        titles={source.id:experiment_title(source,annotations or {}) for source in sources}
        self.context.setText("Fontes: "+" · ".join(f"{titles[e.id]} ({e.config.system.num_qubits} qubits)" for e in sources) if sources else "Abra uma execução ou carregue uma comparação com estados completos.")
        self.dialog_context.setText(self.context.text())
        self.table.setRowCount(0)
        records=[]
        for source in sources:
            parent=(source.result.mitigation or {}).get("source_experiment_id") or source.result.metadata.get("reproduced_from_id") or source.result.metadata.get("imported_from_id")
            origin=titles.get(parent,"Execução anterior") if parent else "Registro original"
            records.append(([origin,titles[source.id],"Execução","",source.created_at.isoformat()],None))
        for data,path in analyses:
            fields=data.get("protocol",{}).get("fields",{})
            records.append(([titles.get(data.get("source_id"),"Experimento"),fields.get("title") or _kind_name(data["kind"]),_kind_name(data["kind"]),fields.get("evidence_ref",""),data.get("created_at","")],(data["source_id"],str(path))))
        for data in protocols:
            records.append(([titles.get(data["source_id"],"Experimento"),data["fields"]["title"],"Protocolo",data["fields"].get("evidence_ref",""),data["created_at"]],None))
        for values,payload in records:
            row=self.table.rowCount()
            self.table.insertRow(row)
            for col,value in enumerate(values):
                item=QTableWidgetItem(timestamp(value) if col==4 else str(value))
                item.setToolTip(str(value))
                if col==0:
                    item.setData(Qt.UserRole,payload)
                self.table.setItem(row,col,item)

    def set_running(self,running):
        self.import_button.setEnabled(not running)
        self.prepare_export.setEnabled(not running)
        self.generate.setEnabled(not running)
        self.format.setEnabled(not running)
        for widget in (*self.buttons,self.use_comparison,self.include_analyses,self.include_gif,self.max_frames,self.frame_ms,self.report_template,*self.report_sections.values()):
            widget.setEnabled(not running)
        self.cancel.setVisible(running)
        self.progress.setVisible(running)
        if running:
            self.progress.setValue(0)


def _path_name(path):
    from pathlib import Path
    return Path(path).stem


def _kind_name(kind):
    return {"temporal":"Evolução temporal","convergence":"Convergência de Trotter",
            "trotter_noise":"Trotterização e ruído","sweep":"Varredura de parâmetros",
            "mitigation_benchmark":"Benchmark de mitigação","heatmap":"Mapa de parâmetros",
            "zne_stability":"Estabilidade da ZNE","equal_budget":"Comparação com orçamento igual"}.get(kind,kind)
