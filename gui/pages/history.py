"""Searchable experiment catalogue and a lazy, read-only detail inspector."""

from dataclasses import asdict
from html import escape
import json

from core.types import system_label
from data.workspace import experiment_title
from PySide6.QtCore import Signal, Qt, QTimer
from PySide6.QtWidgets import (
    QTableWidget, QTableWidgetItem, QHeaderView, QLineEdit, QHBoxLayout,
    QLabel, QPushButton, QComboBox, QSplitter, QWidget, QVBoxLayout,
    QTabWidget, QTextBrowser, QPlainTextEdit, QToolButton, QMenu,
)
from gui.pages.base import PageBase
from gui.widgets.button import SecondaryButton
from gui.widgets.data_table import configure_table, DataTableItem
from gui.widgets.plot_canvas import MplCanvas
from gui.widgets.circuit_inspector import CircuitInspector
from gui.widgets.flow_layout import FlowLayout
from gui.theme import PALETTE
from gui.widgets.card import EmptyState
from gui.formatting import quantity


class HistoryPage(PageBase):
    configure_requested = Signal()
    compare_requested = Signal(str, str)
    experiment_selected = Signal(str)
    experiment_deleted = Signal(str)
    detail_requested = Signal(str)
    edit_requested = Signal(str)

    def __init__(self, parent=None):
        super().__init__(
            "Histórico de experimentos",
            "Encontre uma execução, visualize seus detalhes ou reabra os resultados.",
            parent,
        )
        filters = QHBoxLayout()
        self.search = QLineEdit()
        self.search.setPlaceholderText("Buscar nome, projeto, etiquetas ou anotações…")
        self.search.setAccessibleName("Buscar experimentos")
        self.status_filter = QComboBox()
        for label, value in (("Todos os estados", "all"), ("Concluídos", "ok"), ("Com ZNE", "zne"), ("Falhas", "error")):
            self.status_filter.addItem(label, value)
        self.status_filter.setAccessibleName("Filtrar estado da execução")
        filters.addWidget(self.search, 1)
        filters.addWidget(self.status_filter)
        self.columns = QToolButton()
        self.columns.setText("Colunas")
        self.columns.setPopupMode(QToolButton.InstantPopup)
        self.columns.setAccessibleName("Escolher colunas do histórico")
        filters.addWidget(self.columns)
        self.body().addLayout(filters)
        self.project_filter_bar = QWidget()
        project_row = QHBoxLayout(self.project_filter_bar)
        project_row.setContentsMargins(0, 0, 0, 0)
        self.project_filter_label = QLabel()
        self.project_filter_label.setTextFormat(Qt.PlainText)
        self.project_filter_label.setWordWrap(True)
        self.project_filter_label.setToolTip("Mostra apenas execuções vinculadas a este projeto. A busca refina esse conjunto.")
        self.clear_project_filter = SecondaryButton("Todos os projetos")
        self.clear_project_filter.setToolTip("Remover o filtro de projeto e manter os demais filtros.")
        self.clear_project_filter.setAccessibleName("Remover filtro de projeto")
        self.clear_project_filter.clicked.connect(lambda: self.set_project_filter(None))
        project_row.addWidget(self.project_filter_label, 1)
        project_row.addWidget(self.clear_project_filter)
        self.project_filter_bar.hide()
        self.body().addWidget(self.project_filter_bar)

        splitter = QSplitter(Qt.Vertical)
        self.splitter = splitter
        splitter.setChildrenCollapsible(False)
        splitter.setHandleWidth(6)
        self.table = QTableWidget(0, 10)
        self.table.setHorizontalHeaderLabels([
            "Data / fuso", "Experimento", "Modelo", "Qubits", "Ruído",
            "Fidelidade", "Estado", "Projeto", "Etiquetas", "Ação",
        ])
        configure_table(self.table, sortable=True)
        self.table.setSelectionMode(QTableWidget.ExtendedSelection)
        self.table.horizontalHeader().moveSection(1, 0)
        self.compare_selected = SecondaryButton('Comparar selecionadas', icon='comparison')
        self.compare_selected.setToolTip('Selecione duas linhas com Ctrl ou Shift para comparar as execuções.')
        self.compare_selected.setEnabled(False)
        self.compare_selected.clicked.connect(self._compare_selected)
        self.table.itemSelectionChanged.connect(self._selection_changed)
        self.add_action(self.compare_selected)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setDefaultAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.table.horizontalHeader().setStretchLastSection(False)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(9, QHeaderView.ResizeToContents)
        column_menu = QMenu(self.columns)
        self.column_actions = {}
        for index in range(self.table.columnCount()):
            if index == 9:
                continue
            action = column_menu.addAction(self.table.horizontalHeaderItem(index).text())
            action.setCheckable(True)
            visible = index in (0, 1, 5, 6)
            action.setChecked(visible)
            action.setEnabled(index != 1)
            self.table.setColumnHidden(index, not visible)
            action.toggled.connect(lambda checked, column=index: self.table.setColumnHidden(column, not checked))
            self.column_actions[index] = action
        self.columns.setMenu(column_menu)
        self.table.setMinimumHeight(240)
        self.table.cellDoubleClicked.connect(self._open)
        splitter.addWidget(self.table)

        details = QWidget()
        self.detail_panel = details
        details.setObjectName("InspectorPanel")
        details.setAttribute(Qt.WA_StyledBackground, True)
        detail_layout = QVBoxLayout(details)
        detail_layout.setContentsMargins(18, 16, 18, 16)
        bar = FlowLayout()
        self.detail_title = QLabel("Selecione Visualizar em uma execução")
        self.detail_title.setObjectName("PanelTitle")
        self.detail_title.setWordWrap(True)
        self.detail_title.setTextFormat(Qt.PlainText)
        detail_layout.addWidget(self.detail_title)
        self.open_result = QPushButton("Abrir resultados")
        self.edit_annotation = QPushButton("Editar identificação")
        bar.addWidget(self.open_result)
        bar.addWidget(self.edit_annotation)
        self.expand_details = SecondaryButton("Ampliar detalhes")
        self.expand_details.setCheckable(True)
        self.expand_details.setEnabled(False)
        self.expand_details.setAccessibleName("Ampliar ou restaurar os detalhes do experimento")
        self.expand_details.setToolTip("Oculta a lista temporariamente para consultar gráficos, circuito e anotações com mais espaço.")
        self.expand_details.toggled.connect(self._set_detail_expanded)
        bar.addWidget(self.expand_details)
        detail_layout.addLayout(bar)
        self.detail_tabs = QTabWidget()
        self.summary = QTextBrowser()
        self.summary.setOpenExternalLinks(False)
        self.chart = MplCanvas()
        self.circuit = CircuitInspector()
        self.technical = QPlainTextEdit()
        self.technical.setReadOnly(True)
        self.detail_tabs.addTab(self.summary, "Resumo e anotações")
        self.detail_tabs.addTab(self.chart, "Resultados")
        self.detail_tabs.addTab(self.circuit, "Circuito")
        self.detail_tabs.addTab(self.technical, "Metadados técnicos")
        self.detail_tabs.setMinimumHeight(260)
        detail_layout.addWidget(self.detail_tabs)
        splitter.addWidget(details)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 1)
        self.body().addWidget(splitter, 1)
        self.empty = EmptyState("history", "Nenhuma execução para exibir", "Revise os filtros ou configure uma simulação para registrar seus resultados.", "Configurar simulação")
        self.empty.action_button.clicked.connect(self.configure_requested.emit)
        self.empty.hide()
        self.body().addWidget(self.empty, 1)
        self.selected_identifier = None
        self._detail_experiment = None
        self.detail_panel.hide()
        self._auto_detail_focus = False
        self._was_wide = False
        self._layout_timer = QTimer(self)
        self._layout_timer.setSingleShot(True)
        self._layout_timer.setInterval(0)
        self._layout_timer.timeout.connect(self._arrange_details)
        self.expand_details.clicked.connect(lambda *_: setattr(self, '_auto_detail_focus', False))
        self.open_result.setEnabled(False)
        self.edit_annotation.setEnabled(False)
        self.open_result.clicked.connect(lambda: self.experiment_selected.emit(self.selected_identifier) if self.selected_identifier else None)
        self.edit_annotation.clicked.connect(lambda: self.edit_requested.emit(self.selected_identifier) if self.selected_identifier else None)

        pagination = QHBoxLayout()
        self.previous = QPushButton("Anterior")
        self.next = QPushButton("Próxima")
        self.page_label = QLabel()
        self.page_label.setWordWrap(True)
        pagination.addWidget(self.previous)
        pagination.addWidget(self.page_label, 1)
        pagination.addWidget(self.next)
        self.body().addLayout(pagination)
        self.previous.clicked.connect(lambda: self._paginate(-1))
        self.next.clicked.connect(lambda: self._paginate(1))
        self.offset, self.page_size = 0, 100
        self.records, self.annotations = [], {}
        self.project_filter = None
        self.search.textChanged.connect(self._search_changed)
        self.status_filter.currentIndexChanged.connect(self._search_changed)
        self.table.horizontalHeader().sortIndicatorChanged.connect(self._sort_changed)

    def load(self, experiments):
        self.records = list(experiments)
        if self.selected_identifier and not any(e.id == self.selected_identifier for e in self.records):
            self.selected_identifier = None
            self._detail_experiment = None
            self.expand_details.setChecked(False)
            self.expand_details.setEnabled(False)
            self.detail_title.setText("Selecione Visualizar em uma execução")
            self.summary.clear()
            self.circuit.clear()
            self.technical.clear()
            self.chart.reset_axes()
            self.chart.draw_idle()
            self.open_result.setEnabled(False)
            self.edit_annotation.setEnabled(False)
        if self.selected_identifier and self._detail_experiment is not None and self._detail_experiment.id == self.selected_identifier:
            self.set_detail(self._detail_experiment)
        self._filter()

    def _filter(self, *_):
        query = self.search.text().casefold().strip()
        matches = []
        for exp in self.records:
            status_key = "error" if exp.result.error else ("zne" if exp.result.mitigation else "ok")
            status = {"error": "Falhou", "zne": "ZNE", "ok": "Concluído"}[status_key]
            annotation = self.annotations.get(exp.id, {})
            if self.project_filter is not None and annotation.get("project", "") != self.project_filter:
                continue
            values = [
                exp.created_at.astimezone().strftime("%d/%m/%Y %H:%M %z"),
                experiment_title(exp, self.annotations), system_label(exp.config),
                str(exp.config.system.num_qubits),
                exp.config.noise.kind if exp.config.noise.enabled else "Ideal",
                quantity(exp.result.fidelity), status,
                annotation.get("project", ""), ", ".join(annotation.get("tags", [])),
            ]
            search_text = " ".join(values) + " " + exp.id + " " + json.dumps(annotation, ensure_ascii=False)
            status_filter = self.status_filter.currentData()
            if query not in search_text.casefold() or (status_filter != "all" and status_key != status_filter):
                continue
            matches.append((exp, values))
        section = self.table.horizontalHeader().sortIndicatorSection()
        if 0 <= section < 9:
            def sort_key(record):
                exp, values = record
                if section == 0:
                    return exp.created_at.timestamp()
                if section == 3:
                    return exp.config.system.num_qubits
                if section == 5:
                    return exp.result.fidelity if exp.result.fidelity is not None else -1.0
                return values[section].casefold()
            matches.sort(key=sort_key, reverse=self.table.horizontalHeader().sortIndicatorOrder() == Qt.DescendingOrder)
        self.offset = min(self.offset, max(0, ((len(matches) - 1) // self.page_size) * self.page_size))
        self.table.setSortingEnabled(False)
        self.table.setRowCount(0)
        for exp, values in matches[self.offset:self.offset + self.page_size]:
            row = self.table.rowCount()
            self.table.insertRow(row)
            sort_values = {0: exp.created_at.timestamp(), 3: exp.config.system.num_qubits, 5: exp.result.fidelity if exp.result.fidelity is not None else -1.0}
            for col, value in enumerate(values):
                item = DataTableItem(value, sort_values.get(col))
                item.setData(Qt.UserRole, exp.id)
                item.setToolTip(str(exp.result.fidelity) if col == 5 and exp.result.fidelity is not None else str(value))
                if col in (3, 5):
                    item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.table.setItem(row, col, item)
            button = SecondaryButton(icon="eye")
            button.setToolTip("Visualizar")
            button.setAccessibleName("Visualizar")
            button.setAccessibleDescription(f"Abrir detalhes do experimento {values[1]}")
            button.setFocusPolicy(Qt.StrongFocus)
            button.setMinimumSize(40, 38)
            button.clicked.connect(lambda checked=False, identifier=exp.id: self._view(identifier))
            self.table.setCellWidget(row, 9, button)
        self.table.setSortingEnabled(True)
        self.page_label.setText(
            f"{len(matches)} registro(s) · página {self.offset // self.page_size + 1}"
            if matches else "Nenhum experimento encontrado. Execute uma simulação ou ajuste os filtros."
        )
        self.empty.setVisible(not bool(matches))
        self.splitter.setVisible(bool(matches))
        self.previous.setEnabled(self.offset > 0)
        self.next.setEnabled(self.offset + self.page_size < len(matches))

    def set_project_filter(self, project):
        """Filter the project field exactly, independently of free-text search."""
        if project is not None and not isinstance(project, str):
            raise TypeError("O filtro de projeto deve ser um nome ou None.")
        self.project_filter = project.strip() if project and project.strip() else None
        self.project_filter_label.setText(f"Projeto: {self.project_filter}" if self.project_filter else "")
        self.project_filter_bar.setVisible(self.project_filter is not None and not self.expand_details.isChecked())
        self.offset = 0
        self._filter()

    def _view(self, identifier):
        record = next((record for record in self.records if record.id == identifier), None)
        if record is None:
            return
        self.selected_identifier = identifier
        self.set_detail(record)
        self.detail_requested.emit(identifier)

    def _selection_changed(self):
        self.compare_selected.setEnabled(len(self.table.selectionModel().selectedRows()) == 2)

    def _compare_selected(self):
        rows = self.table.selectionModel().selectedRows()
        if len(rows) == 2:
            ids = [self.table.item(index.row(), 0).data(Qt.UserRole) for index in rows]
            self.compare_requested.emit(*ids)

    def _arrange_details(self):
        scale = max(1, self.font().pixelSize() / 15)
        wide = self.width() >= 1050 * scale
        # O mestre precisa acomodar nome, data, métricas e a ação de consulta.
        # Abaixo dessa largura o cabeçalho Stretch pode reter a largura anterior
        # e deixar o olho e até o título da coluna fora da área visível.
        self.table.setMinimumWidth(round(700 * scale) if wide else 0)
        self.splitter.setOrientation(Qt.Horizontal if wide else Qt.Vertical)
        if wide and self._auto_detail_focus:
            self.expand_details.setChecked(False)
            self._auto_detail_focus = False
        elif not wide and self._was_wide and self._detail_experiment is not None:
            self._auto_detail_focus = True
            self.expand_details.setChecked(True)
        self._was_wide = wide

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, '_layout_timer'):
            self._layout_timer.start()

    def _set_detail_expanded(self, expanded):
        for widget in (self._header, self.table, self.search, self.status_filter, self.columns,
                       self.previous, self.next, self.page_label):
            widget.setVisible(not expanded)
        self.project_filter_bar.setVisible(self.project_filter is not None and not expanded)
        self.expand_details.setText("Voltar à lista" if expanded else "Ampliar detalhes")

    def set_detail(self, experiment, files=None):
        """Accept summaries immediately and replace them with loaded scientific data."""
        if (self.selected_identifier is not None and experiment.id != self.selected_identifier) or not any(record.id == experiment.id for record in self.records):
            return
        self.selected_identifier = experiment.id
        self._detail_experiment = experiment
        self.detail_panel.show()
        if self.width() < 1050 * max(1, self.font().pixelSize() / 15):
            self._auto_detail_focus = True
            self.expand_details.setChecked(True)
        name = experiment_title(experiment, self.annotations)
        self.detail_title.setText(name)
        self.open_result.setEnabled(True)
        self.edit_annotation.setEnabled(True)
        self.expand_details.setEnabled(True)
        annotation = self.annotations.get(experiment.id, {})
        result, config = experiment.result, experiment.config
        def paragraph(label, value):
            return f"<p><b>{escape(label)}</b><br>{escape(str(value)).replace(chr(10), '<br>')}</p>" if value else ""
        text = paragraph("Descrição", annotation.get("description"))
        for label, key in (("Objetivo científico", "objective"), ("Hipótese", "hypothesis"), ("Metodologia", "methodology"), ("Anotações", "notes")):
            text += paragraph(label, annotation.get(key))
        text += paragraph("Execução", f"{experiment.created_at.astimezone():%d/%m/%Y %H:%M:%S %z} · {system_label(config)} · {config.system.num_qubits} qubits · {config.shots} shots · {experiment.duration_s:.4g} s")
        text += paragraph("Organização", " · ".join(filter(None, [annotation.get("project"), ", ".join(annotation.get("categories", [])), ", ".join(annotation.get("tags", []))])))
        for label, value in (("Fidelidade ao próprio circuito ideal", result.fidelity), ("Pureza global", result.purity), ("Energia ⟨H⟩", result.energy)):
            text += paragraph(label, "indisponível" if value is None else f"{value:.12g}")
        if result.mitigation:
            text += paragraph("Mitigação", "ZNE extrapola observáveis. Fidelidade, pureza e estado deste registro pertencem à simulação de origem; não representam um estado mitigado reconstruído.")
        if result.error:
            text += paragraph("Falha registrada", result.error)
        text += paragraph("Arquivos", "\n".join(str(path) for path in files) if files else "Consulte Documentar e exportar para produzir relatórios, figuras e dados deste experimento.")
        self.summary.setHtml(text)
        from core.figures import histogram_figure
        from gui.widgets.plot_canvas import style_figure
        histogram_figure([experiment], fig=self.chart.fig, colors=(PALETTE.primary,), label_size=10)
        style_figure(self.chart.fig)
        self.chart.draw_idle()
        if result.metadata.get("operations") or result.circuit_text or files is not None:
            if result.error and not result.metadata.get("operations"):
                self.circuit.clear("Esta execução falhou e não possui operações registradas para consulta.")
            else:
                try:
                    self.circuit.show_experiment(experiment, name)
                except (ValueError, TypeError, KeyError) as exc:
                    self.circuit.clear("Não foi possível apresentar o circuito deste registro: " + str(exc))
        else:
            self.circuit.clear("Carregando as operações registradas do circuito…")
        metadata = {key: (f"{len(value)} operações; veja JSON completo" if key == "operations" else value) for key, value in result.metadata.items()}
        self.technical.setPlainText(json.dumps({"id": experiment.id, "created_at": experiment.created_at.isoformat(), "configuration": asdict(config), "metadata": metadata, "mitigation_method": (result.mitigation or {}).get("method")}, ensure_ascii=False, indent=2, default=str))

    def _search_changed(self, *_):
        self.offset = 0
        self._filter()

    def _sort_changed(self, *_):
        self.offset = 0
        self._filter()

    def _paginate(self, delta):
        self.offset = max(0, self.offset + delta * self.page_size)
        self._filter()

    def _open(self, row, column):
        item = self.table.item(row, 0)
        if item:
            self.experiment_selected.emit(item.data(Qt.UserRole))
