"""Searchable experiment catalogue and a lazy, read-only detail inspector."""

from dataclasses import asdict
from html import escape
import json

from core.types import system_label
from data.workspace import experiment_title
from PySide6.QtCore import Signal, Qt
from PySide6.QtWidgets import (
    QTableWidget, QTableWidgetItem, QHeaderView, QLineEdit, QHBoxLayout,
    QLabel, QPushButton, QComboBox, QSplitter, QWidget, QVBoxLayout,
    QTabWidget, QTextBrowser, QPlainTextEdit, QToolButton, QMenu,
)
from gui.pages.base import PageBase
from gui.widgets.data_table import configure_table, DataTableItem
from gui.widgets.plot_canvas import MplCanvas, style_axes


class HistoryPage(PageBase):
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

        splitter = QSplitter(Qt.Vertical)
        splitter.setChildrenCollapsible(False)
        splitter.setHandleWidth(6)
        self.table = QTableWidget(0, 10)
        self.table.setHorizontalHeaderLabels([
            "Data / fuso", "Experimento", "Modelo", "Qubits", "Ruído",
            "Fidelidade", "Estado", "Projeto", "Etiquetas", "Ação",
        ])
        configure_table(self.table, sortable=True)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
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
        detail_layout = QVBoxLayout(details)
        detail_layout.setContentsMargins(0, 8, 0, 0)
        bar = QHBoxLayout()
        self.detail_title = QLabel("Selecione Visualizar em uma execução")
        self.detail_title.setWordWrap(True)
        bar.addWidget(self.detail_title, 1)
        self.open_result = QPushButton("Abrir resultados")
        self.edit_annotation = QPushButton("Editar identificação")
        bar.addWidget(self.open_result)
        bar.addWidget(self.edit_annotation)
        detail_layout.addLayout(bar)
        self.detail_tabs = QTabWidget()
        self.summary = QTextBrowser()
        self.summary.setOpenExternalLinks(False)
        self.chart = MplCanvas()
        self.circuit = QPlainTextEdit()
        self.circuit.setReadOnly(True)
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
        self.selected_identifier = None
        self._detail_experiment = None
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
        self.search.textChanged.connect(self._search_changed)
        self.status_filter.currentIndexChanged.connect(self._search_changed)
        self.table.horizontalHeader().sortIndicatorChanged.connect(self._sort_changed)

    def load(self, experiments):
        self.records = list(experiments)
        if self.selected_identifier and not any(e.id == self.selected_identifier for e in self.records):
            self.selected_identifier = None
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
            values = [
                exp.created_at.astimezone().strftime("%d/%m/%Y %H:%M %z"),
                experiment_title(exp, self.annotations), system_label(exp.config),
                str(exp.config.system.num_qubits),
                exp.config.noise.kind if exp.config.noise.enabled else "Ideal",
                "—" if exp.result.fidelity is None else f"{exp.result.fidelity:.4f}", status,
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
                item.setToolTip(f"{value}\nIdentificador técnico: {exp.id}")
                if col in (3, 5):
                    item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.table.setItem(row, col, item)
            button = QPushButton("Visualizar")
            button.setAccessibleName(f"Visualizar {values[1]}")
            button.clicked.connect(lambda checked=False, identifier=exp.id: self._view(identifier))
            self.table.setCellWidget(row, 9, button)
        self.table.setSortingEnabled(True)
        self.page_label.setText(
            f"{len(matches)} registro(s) · página {self.offset // self.page_size + 1}"
            if matches else "Nenhum experimento encontrado. Execute uma simulação ou ajuste os filtros."
        )
        self.previous.setEnabled(self.offset > 0)
        self.next.setEnabled(self.offset + self.page_size < len(matches))

    def _view(self, identifier):
        record = next((record for record in self.records if record.id == identifier), None)
        if record is None:
            return
        self.selected_identifier = identifier
        self.set_detail(record)
        self.detail_requested.emit(identifier)

    def set_detail(self, experiment, files=None):
        """Accept summaries immediately and replace them with loaded scientific data."""
        if (self.selected_identifier is not None and experiment.id != self.selected_identifier) or not any(record.id == experiment.id for record in self.records):
            return
        self.selected_identifier = experiment.id
        self._detail_experiment = experiment
        name = experiment_title(experiment, self.annotations)
        self.detail_title.setText(name)
        self.open_result.setEnabled(True)
        self.edit_annotation.setEnabled(True)
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
        ax = self.chart.reset_axes()
        counts = result.counts or {}
        total = sum(counts.values())
        if total:
            keys = sorted(counts)
            ax.bar(keys, [counts[key] / total for key in keys])
            ax.set_ylabel("Frequência observada")
            ax.set_xlabel("Estado computacional")
            if len(keys) > 8:
                ax.tick_params(axis="x", labelrotation=90)
        else:
            ax.text(.5, .5, "Sem contagens disponíveis nesta execução.", ha="center", va="center", transform=ax.transAxes)
        style_axes(ax)
        self.chart.draw_idle()
        self.circuit.setPlainText(result.circuit_text or "Circuito textual indisponível neste registro.")
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
