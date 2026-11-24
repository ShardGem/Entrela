from dataclasses import asdict
import json

from PySide6.QtCore import Signal, Qt
from PySide6.QtWidgets import (
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QPlainTextEdit,
    QHeaderView,
    QFrame, QFormLayout, QMenu, QHBoxLayout, QVBoxLayout, QWidget, QScrollArea,
)
from gui.pages.base import PageBase
from gui.widgets.card import MetricCard, MetricGrid, EmptyState
from gui.widgets.button import GhostButton, PrimaryButton, SecondaryButton
from gui.design_system import Surface
from gui.tabs.results_tab import ResultsTab
from gui.widgets.state_inspector import StateInspector
from gui.widgets.content_tabs import ContentTabs
from gui.widgets.collapsible import CollapsibleSection
from gui.widgets.flow_layout import FlowLayout
from core.export import result_interpretation
from core.reproduction import scientific_context
from core.types import system_label
from gui.widgets.data_table import configure_table
from gui.formatting import quantity, timestamp


class ResultsPage(PageBase):
    history_requested = Signal()
    edit_config_requested = Signal()
    report_requested = Signal()
    rerun_requested = Signal()
    save_requested = Signal()
    export_requested = Signal()
    export_experiment_requested = Signal()
    export_figures_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(
            "Resultados", "Dados e interpretações da execução selecionada.", parent
        )
        self.details = QLabel("Execute ou abra um experimento.")
        self.empty = EmptyState('results', 'Escolha uma execução para explorar',
                                'Abra um resultado salvo ou prepare uma nova simulação no laboratório.',
                                'Abrir execuções salvas')
        self.empty.action_button.clicked.connect(self.history_requested.emit)
        self.body().addWidget(self.empty)
        self.details.setWordWrap(True)
        self.details.setObjectName('FieldHint')
        self.details.setTextFormat(Qt.PlainText)
        self.card_fid = MetricCard("Fidelidade ao circuito sem ruído")
        self.card_pur = MetricCard("Pureza global")
        self.card_erg = MetricCard("Energia ⟨H⟩")
        self.card_err = MetricCard("Infidelidade (1−F)", parent=self)
        self.card_err.hide()
        self.metric_grid = MetricGrid([self.card_fid, self.card_pur, self.card_erg])
        for card in self.metric_grid.cards:
            card.setObjectName('RunMetric')
            card.layout().setContentsMargins(0, 4, 0, 8)
            card.layout().setSpacing(3)
        self.metric_grid.layout().setSpacing(6)
        self.body().setSpacing(12)
        self.science_note = QLabel()
        self.science_note.setWordWrap(True)
        self.science_note.setTextFormat(Qt.PlainText)
        self.science_note.setObjectName('FieldHint')
        self.reproduction_status = QLabel()
        self.reproduction_status.setWordWrap(True)
        self.reproduction_status.setObjectName('FieldHint')
        self.tabs = ContentTabs()
        self.results_tab = ResultsTab()
        self.interpretation = QLabel("A interpretação aparecerá após uma execução.")
        self.interpretation.setWordWrap(True)
        self.interpretation.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        self.interpretation.setObjectName("ResultInterpretation")
        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(
            ["Estado", "Contagens", "Frequência", "Probabilidade do estado"]
        )
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        configure_table(self.table)
        self.metadata = QWidget()
        metadata_layout = QVBoxLayout(self.metadata)
        metadata_layout.setContentsMargins(0, 0, 0, 0)
        metadata_layout.setSpacing(12)
        provenance = Surface("Parâmetros registrados")
        form = QFormLayout()
        form.setRowWrapPolicy(QFormLayout.WrapLongRows)
        form.setVerticalSpacing(10)
        self.provenance_values = {}
        for field in ("Sistema", "Protocolo", "Ruído", "Medições", "Versões", "Registro"):
            value = QLabel()
            value.setTextFormat(Qt.PlainText)
            value.setWordWrap(True)
            value.setTextInteractionFlags(Qt.TextSelectableByMouse)
            self.provenance_values[field] = value
            form.addRow(field, value)
        provenance.body().addLayout(form)
        metadata_layout.addWidget(provenance)
        self.metadata_details = CollapsibleSection("JSON do registro")
        self.metadata_json = QPlainTextEdit()
        self.metadata_json.setReadOnly(True)
        self.metadata_json.setAccessibleName("JSON do registro")
        self.metadata_details.content_layout.addWidget(self.metadata_json)
        metadata_layout.addWidget(self.metadata_details)
        metadata_layout.addStretch()
        self.tabs.addTab(self.results_tab, "Gráficos")
        self.tabs.addTab(self.interpretation, "Entender resultado")
        self.tabs.addTab(self.table, "Dados")
        self.tabs.addTab(self.metadata, "Reprodutibilidade")
        self.state_inspector = StateInspector()
        self.tabs.addTab(self.state_inspector, "Estado global")
        self.result_layout = QWidget()
        column_layout = QHBoxLayout(self.result_layout)
        column_layout.setContentsMargins(0, 0, 0, 0)
        column_layout.setSpacing(20)
        column_layout.addWidget(self.tabs, 1)

        self.inspector = Surface('Sobre a execução', role='WorkbenchInspector')
        self.inspector.add(self.details)
        self.inspector.add(self.metric_grid)
        self.inspector.add(self.science_note)
        self.inspector.add(self.reproduction_status)
        self.inspector_scroll = QScrollArea()
        self.inspector_scroll.setObjectName('InspectorScroll')
        self.inspector_scroll.setWidgetResizable(True)
        self.inspector_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.inspector_scroll.setWidget(self.inspector)
        self.inspector_toggle = GhostButton('Detalhes', icon='panel-right')
        self.inspector_toggle.setToolTip('Mostrar ou ocultar as métricas e a referência da execução')
        self.inspector_toggle.setCheckable(True)
        self.inspector_toggle.setChecked(True)
        self.inspector_toggle.toggled.connect(self._set_inspector_open)
        self.add_action(self.inspector_toggle)
        column_layout.addWidget(self.inspector_scroll)
        self.body().addWidget(self.result_layout, 1)
        self.execution_actions = QFrame()
        self.execution_actions.setObjectName('ExecutionActions')
        actions = FlowLayout(self.execution_actions)
        actions.setContentsMargins(8, 6, 8, 6)
        for name, text, icon, signal in [
            ("btn_rerun", "Reexecutar", 'rerun', self.rerun_requested),
            ("btn_report", "Relatório", None, self.report_requested),
            ("btn_save", "Salvar execução", 'save', self.save_requested),
            ("btn_export", "CSV", None, self.export_requested),
            ("btn_export_full", "JSON / pacote", None, self.export_experiment_requested),
            ("btn_figures", "Figuras PNG", None, self.export_figures_requested),
        ]:
            button_type = PrimaryButton if name == 'btn_save' else SecondaryButton
            button = button_type(text, icon=icon, parent=self)
            button.clicked.connect(signal.emit)
            button.setEnabled(False)
            setattr(self, name, button)
            if name in ('btn_rerun', 'btn_save'):
                actions.addWidget(button)
            else:
                button.hide()
        self.btn_edit = SecondaryButton('Criar rascunho', icon='copy')
        self.btn_edit.setToolTip('Criar uma cópia editável da configuração desta execução. Não executa o rascunho atual.')
        self.btn_edit.clicked.connect(self.edit_config_requested.emit)
        actions.addWidget(self.btn_edit)
        self.export_menu = QMenu(self)
        self.export_button = SecondaryButton('Exportar', icon='export')
        self.export_button.setAccessibleName('Exportar a execução selecionada')
        self.export_button.setMenu(self.export_menu)
        for text, button in [('Relatório científico PDF…', self.btn_report), ('Dados das medições CSV…', self.btn_export),
                             ('Execução completa JSON / pacote ZIP…', self.btn_export_full), ('Figuras da execução PNG…', self.btn_figures)]:
            self.export_menu.addAction(text, button.click)
        actions.addWidget(self.export_button)
        self.body().addWidget(self.execution_actions)
        self.inspector.body().addStretch()
        self.tabs.currentChanged.connect(self._arrange_result_view)
        self._available = False
        self._set_available(False)

    def _set_available(self, available):
        self._available = available
        self.empty.setVisible(not available)
        self.result_layout.setVisible(available)
        self.execution_actions.setVisible(available)
        self.reproduction_status.hide()
        self.inspector_toggle.setEnabled(available)
        self.export_button.setEnabled(available)
        self.btn_edit.setEnabled(available)

    def _set_inspector_open(self, opened):
        self.inspector_scroll.setVisible(opened)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        scale = max(1, self.fontMetrics().height() / 19)
        self.inspector_scroll.setFixedWidth(round(276 * scale))

    def _arrange_result_view(self, *_):
        summary = self.tabs.currentWidget() in (self.results_tab, self.interpretation)
        self.metric_grid.setVisible(summary)
        self.science_note.setVisible(summary)

    def set_saved(self, saved):
        self.btn_save.setText('Execução salva' if saved else 'Salvar execução')
        self.btn_save.setEnabled(not saved)
        self.btn_save.setVisible(not saved)
        self.btn_save.setToolTip('Resultados preservados no histórico.' if saved else 'Guardar os resultados disponíveis no histórico.')

    def update_metrics(self, fid=None, pur=None, erg=None):
        for card, value in [
            (self.card_fid, fid),
            (self.card_pur, pur),
            (self.card_erg, erg),
            (self.card_err, None if fid is None else 1 - fid),
        ]:
            card.set_value(quantity(value))
            card.setToolTip('Indisponível neste registro' if value is None else 'Valor completo: ' + repr(float(value)))
        if fid is not None:
            self.card_fid.setToolTip(self.card_fid.toolTip() + '\nInfidelidade (1−F): ' + quantity(1 - fid))

    def _update_details(self):
        experiment = self._experiment
        r, c = experiment.result, experiment.config
        context = scientific_context(experiment)
        self.science_note.setText("\n".join(line for line in context.splitlines() if line.startswith(("Referência", "Hipóteses", "ZNE"))))
        self.science_note.setToolTip(context)
        check = r.metadata.get("reproduction_check")
        status_text = ""
        if check:
            subject = "Reprodução da ZNE" if check.get("kind") == "zne" else "Reprodução"
            detail = {"matched":"numericamente compatível dentro da tolerância registrada.",
                      "different":"com diferenças; consulte Reprodutibilidade.",
                      "unavailable":"sem dados suficientes na origem para verificação."}.get(check.get("status"),"sem verificação disponível.")
            status_text = subject + " " + detail + (" Contagens idênticas." if check.get("counts_match") else " Contagens não idênticas; a verificação numérica é informada separadamente.")
        self.reproduction_status.setText(status_text)
        self.reproduction_status.setVisible(bool(check))
        self.details.setText(
            f"{system_label(c)} · {c.system.num_qubits} qubits\n"
            f"{c.shots} shots · profundidade {r.circuit_depth}\n"
            f"Duração: {experiment.duration_s:.3f} s\n"
            f"Semente efetiva: {r.metadata.get('effective_seed', 'não registrada')}"
        )

    def _update_provenance(self, experiment):
        config, result = experiment.config, experiment.result
        protocol = config.protocol
        if config.circuit is not None:
            method = f"Circuito de portas · {len(config.circuit.gates)} portas no documento"
        else:
            method = f"T={protocol.total_time:g} · {protocol.trotter_steps} passos · Suzuki de ordem {protocol.trotter_order}"
        raw_versions = result.metadata.get("versions")
        versions = raw_versions if isinstance(raw_versions, dict) else {}
        values = {
            "Sistema": f"{system_label(config)} · {config.system.num_qubits} qubits",
            "Protocolo": method,
            "Ruído": config.noise.kind if config.noise.enabled else "Desativado",
            "Medições": f"{config.shots} shots · semente efetiva {result.metadata.get('effective_seed', 'não registrada')}",
            "Versões": " · ".join(f"{name} {version}" for name, version in versions.items()) or "Não registradas",
            "Registro": f"{experiment.id} · {timestamp(experiment.created_at)}",
        }
        for field, value in values.items():
            self.provenance_values[field].setText(value)

    def show_experiment(self, experiment):
        self._set_available(True)
        self._experiment = experiment
        self.results_tab.set_final_state(experiment.result.final_state)
        self.state_inspector.set_state(experiment.result.final_state,
                                       experiment.result.ideal_final_state,
                                       "Estado final da execução · calculado pelo simulador")
        r, c = experiment.result, experiment.config
        self.btn_rerun.setText("Reproduzir ZNE" if r.mitigation else "Reexecutar")
        self.card_fid._label.setText('Fidelidade do estado de origem' if r.mitigation else 'Fidelidade ao circuito sem ruído')
        self.card_pur._label.setText('Pureza global da origem' if r.mitigation else 'Pureza global')
        self.card_erg._label.setText('Energia da origem ⟨H⟩' if r.mitigation else 'Energia ⟨H⟩')
        self.btn_rerun.setToolTip("Recalcula a análise ZNE com método, fatores, shots e seed registrados; preserva as métricas da fonte." if r.mitigation else "Executa novamente a configuração com a semente efetiva registrada.")
        self._update_details()
        self._update_provenance(experiment)
        self.update_metrics(r.fidelity, r.purity, r.energy)
        self.results_tab.exibir_histograma(r.counts)
        self.results_tab.exibir_evolucao_temporal(
            r.states,
            r.times,
            "Índice da porta" if c.circuit is not None else "Tempo (adimensional, ℏ=1)",
        )
        self.interpretation.setText(result_interpretation(experiment) + "\n\n" + scientific_context(experiment))
        self.table.setRowCount(2**c.system.num_qubits)
        probabilities = (
            r.final_state.probabilities() if r.final_state is not None else None
        )
        total_counts = sum((r.counts or {}).values())
        for index in range(self.table.rowCount()):
            bits = f"{index:0{c.system.num_qubits}b}"
            count = (r.counts or {}).get(bits, 0)
            for column, text in enumerate(
                [
                    bits,
                    str(count),
                    f"{count / total_counts:.12g}" if total_counts else "—",
                    "—" if probabilities is None else f"{probabilities[index]:.12g}",
                ]
            ):
                self.table.setItem(index, column, QTableWidgetItem(text))
        self.metadata_json.setPlainText(
            json.dumps(
                {
                    "id": experiment.id,
                    "config": asdict(c),
                    "metadata": {
                        k: (
                            f"{len(v)} operações — inspecione na página Circuito ou no JSON completo"
                            if k == "operations"
                            else v
                        )
                        for k, v in r.metadata.items()
                    },
                    "mitigation": r.mitigation,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        for button in [
            self.btn_rerun,
            self.btn_report,
            self.btn_save,
            self.btn_export,
            self.btn_export_full,
            self.btn_figures,
        ]:
            button.setEnabled(True)
        self.btn_export.setEnabled(bool(r.counts))
        self._arrange_result_view()
