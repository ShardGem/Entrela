"""One notebook context, reusing execution annotations and the report composer."""
from PySide6.QtCore import Qt, Signal, QSignalBlocker
from PySide6.QtWidgets import QWidget, QVBoxLayout, QComboBox, QFormLayout, QPlainTextEdit, QLabel, QStackedWidget, QScrollArea, QFrame, QSplitter, QTextBrowser, QSizePolicy
from gui.pages.base import PageBase
from gui.widgets.content_tabs import ContentTabs
from gui.widgets.button import SecondaryButton
from gui.widgets.plot_canvas import MplCanvas, style_figure
from gui.design_system import Surface
from gui.theme import PALETTE
from html import escape


class NotebookPage(PageBase):
    project_save_requested = Signal(dict)
    export_requested = Signal()

    def __init__(self, annotations, documentation, parent=None):
        super().__init__("Caderno do projeto", parent=parent)
        self.setObjectName('PageSurface')
        self.project = object()
        self.project_drafts = {}
        layout = self.body()
        layout.setContentsMargins(20, 0, 20, 16)
        self.tabs = ContentTabs(); self.tabs.setDocumentMode(True)
        notes = QWidget(); body = QVBoxLayout(notes)
        self.scope = QComboBox()
        self.scope.addItems(['Projeto · pergunta e interpretação da investigação', 'Execução selecionada · identificação e anotações'])
        self.scope.setAccessibleName('Escopo das anotações')
        body.addWidget(self.scope)
        self.notes_stack = QStackedWidget()
        project_notes = QScrollArea(); project_notes.setWidgetResizable(True); project_notes.setFrameShape(QFrame.NoFrame)
        host = QWidget(); form = QFormLayout(host); form.setRowWrapPolicy(QFormLayout.WrapLongRows)
        self.scope_label = QLabel(); self.scope_label.setWordWrap(True); form.addRow(self.scope_label)
        self.fields = {}
        for key, label in [('objective', 'Objetivo científico'), ('hypothesis', 'Hipótese'), ('methodology', 'Metodologia'),
                           ('interpretation', 'Interpretação'), ('next_steps', 'Próximos passos')]:
            field = QPlainTextEdit(); field.setAccessibleName(label); field.setMaximumHeight(110)
            field.setPlaceholderText(label + ' da investigação; cite as execuções e evidências utilizadas.')
            form.addRow(label, field); self.fields[key] = field
            field.textChanged.connect(self._edited)
        self.save = SecondaryButton('Salvar anotações do projeto', icon='save')
        self.save.clicked.connect(lambda: self.project_save_requested.emit(self.payload()))
        form.addRow(self.save)
        self.message = QLabel(); self.message.setWordWrap(True); form.addRow(self.message)
        project_notes.setWidget(host)
        self.notes_stack.addWidget(project_notes); self.notes_stack.addWidget(annotations)
        body.addWidget(self.notes_stack, 1)
        self.scope.currentIndexChanged.connect(self.notes_stack.setCurrentIndex)
        self.tabs.addTab(notes, 'Anotações')
        self.tabs.addTab(documentation, 'Evidências')
        self.report = documentation.export_dialog
        self.report.setParent(self)
        self.report.setWindowFlags(Qt.Widget)
        documentation.close_setup.hide()
        self.report_workspace = QWidget()
        report_layout = QVBoxLayout(self.report_workspace)
        self.report_splitter = QSplitter(Qt.Horizontal)
        preview = Surface('Roteiro do relatório')
        self.report_preview = QTextBrowser()
        self.report_preview.setAccessibleName('Seções e fontes do relatório científico')
        preview.add(self.report_preview, 1)
        self.report_plot = MplCanvas()
        self.report_plot.setMinimumHeight(180)
        preview.add(self.report_plot, 1)
        self.report_splitter.addWidget(preview)
        self.report_splitter.addWidget(self.report)
        self.report_splitter.setStretchFactor(0, 1)
        self.report_splitter.setSizes([800, 460])
        report_layout.addWidget(self.report_splitter)
        self.tabs.addTab(self.report_workspace, 'Relatório')
        self.documentation = documentation
        self.preview_sources = []
        self.preview_annotations = {}
        for checkbox in documentation.report_sections.values():
            checkbox.toggled.connect(self._update_report_preview)
        documentation.embedded_export = lambda: self.tabs.setCurrentIndex(2)
        self.tabs.currentChanged.connect(lambda index: self.report.show() if index == 2 else None)
        layout.addWidget(self.tabs)
        self.notes_stack.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Ignored)
        self.tabs.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Ignored)
        self._scroll.takeWidget()
        self._scroll.hide()
        self._root.insertWidget(1, self._body_widget, 1)


    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, 'report_splitter'):
            self.report_splitter.setOrientation(Qt.Vertical if self.width() < 1180*max(1,self.font().pixelSize()/15) else Qt.Horizontal)

    def update_report_preview(self, sources, annotations):
        self.preview_sources = list(sources)
        self.preview_annotations = annotations
        self._update_report_preview()

    def _update_report_preview(self, *_):
        from data.workspace import experiment_title
        from gui.formatting import quantity
        from core.figures import draw_histograms
        sources = self.preview_sources
        if not sources:
            self.report_preview.setPlainText('Abra uma execução ou selecione duas fontes em Comparar para preparar um relatório. O PDF usa páginas A4 e os dados registrados.')
            self.report_plot.hide()
            return
        parts = ['<h2>' + escape(self.project or 'Relatório da execução') + '</h2>',
                 '<p>Roteiro do conteúdo selecionado. A geração usa o compositor científico A4, com fontes identificadas.</p>']
        for key, title in [('objective','Objetivo do projeto'), ('hypothesis','Hipótese'), ('methodology','Metodologia'), ('interpretation','Interpretação'), ('next_steps','Próximos passos')]:
            value = self.fields[key].toPlainText()
            if value: parts.append('<h3>' + title + '</h3><p>' + escape(value).replace('\n','<br>') + '</p>')
        for source in sources:
            r = source.result
            annotation = self.preview_annotations.get(source.id, {})
            title = experiment_title(source, self.preview_annotations)
            parts.append('<h3>Fonte: ' + escape(title) + '</h3>')
            parts.append('<p>' + escape(source.created_at.astimezone().strftime('%d/%m/%Y %H:%M')) +
                f" · {source.config.system.num_qubits} qubits · {source.config.shots} shots</p>")
            origin = 'Estado da execução de origem da ZNE' if r.mitigation else 'Estado global final'
            parts.append('<p>' + origin + ': pureza ' + quantity(r.purity) +
                '; fidelidade ao mesmo circuito sem ruído ' + quantity(r.fidelity) + '.</p>')
            if annotation.get('notes'): parts.append('<p>Anotações da execução: ' + escape(annotation['notes']) + '</p>')
        parts.append('<h3>Seções selecionadas</h3><ul>')
        parts.extend('<li>' + escape(box.text()) + '</li>' for box in self.documentation.report_sections.values() if box.isChecked())
        parts.append('</ul><p>Protocolo, semente efetiva e definições das referências acompanham a documentação. Figuras são geradas dos registros selecionados.</p>')
        self.report_preview.setHtml(''.join(parts))
        show_plot = self.documentation.report_sections['include_distribution'].isChecked()
        self.report_plot.setVisible(show_plot)
        if show_plot:
            draw_histograms(self.report_plot.fig, [s.result.counts for s in sources], frequency=True,
                labels=[experiment_title(s, self.preview_annotations) for s in sources], colors=(PALETTE.primary, PALETTE.q2))
            style_figure(self.report_plot.fig); self.report_plot.draw_idle()

    def payload(self): return {key: field.toPlainText() for key, field in self.fields.items()}

    def _edited(self):
        if self.project:
            self.project_drafts[self.project] = self.payload()
            self.project_save_requested.emit(self.payload())

    def set_project(self, name, data):
        if name == self.project: return
        self.project = name
        self.scope_label.setText('Projeto: ' + name if name else 'Crie ou abra um projeto para registrar sua investigação. As anotações de execuções anteriores continuam no seletor acima.')
        values = self.project_drafts.get(name, data)
        for key, field in self.fields.items():
            blocker = QSignalBlocker(field); field.setPlainText(values.get(key, '')); del blocker
            field.setEnabled(bool(name))
        self.save.setEnabled(bool(name))
