from PySide6.QtCore import Signal, Qt
from PySide6.QtWidgets import (
    QLabel,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QPlainTextEdit,
    QHeaderView,
)
from gui.pages.base import PageBase
from gui.widgets.card import MetricCard, MetricGrid
from gui.widgets.button import PrimaryButton, SecondaryButton
from gui.tabs.results_tab import ResultsTab
from gui.widgets.state_inspector import StateInspector
from gui.widgets.content_tabs import ContentTabs
from core.export import result_interpretation
from core.reproduction import scientific_context
from data.workspace import experiment_title
from gui.widgets.data_table import configure_table
import json, numpy as np


class ResultsPage(PageBase):
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
        self.details.setWordWrap(True)
        self.body().addWidget(self.details)
        self.card_fid = MetricCard("Fidelidade ao circuito sem ruído")
        self.card_pur = MetricCard("Pureza global")
        self.card_erg = MetricCard("Energia ⟨H⟩")
        self.card_err = MetricCard("Infidelidade (1−F)")
        self.metric_grid = MetricGrid([self.card_fid, self.card_pur, self.card_erg, self.card_err])
        self.body().addWidget(self.metric_grid)
        self.body().setSpacing(12)
        self.science_note = QLabel()
        self.science_note.setWordWrap(True)
        self.science_note.setTextFormat(Qt.PlainText)
        self.body().addWidget(self.science_note)
        self.reproduction_status = QLabel()
        self.reproduction_status.setWordWrap(True)
        self.body().addWidget(self.reproduction_status)
        self.tabs = ContentTabs()
        self.results_tab = ResultsTab()
        self.interpretation = QLabel("A interpretação aparecerá após uma execução.")
        self.interpretation.setWordWrap(True)
        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(
            ["Estado", "Contagens", "Frequência", "Probabilidade do estado"]
        )
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        configure_table(self.table)
        self.metadata = QPlainTextEdit()
        self.metadata.setReadOnly(True)
        self.tabs.addTab(self.results_tab, "Gráficos")
        self.tabs.addTab(self.interpretation, "Entender resultado")
        self.tabs.addTab(self.table, "Dados")
        self.tabs.addTab(self.metadata, "Reprodutibilidade")
        self.state_inspector = StateInspector()
        self.tabs.addTab(self.state_inspector, "Estado global")
        self.body().addWidget(self.tabs, 1)
        for name, text, signal in [
            ("btn_rerun", "Reexecutar", self.rerun_requested),
            ("btn_report", "Relatório", self.report_requested),
            ("btn_save", "Salvar", self.save_requested),
            ("btn_export", "CSV", self.export_requested),
            ("btn_export_full", "JSON / pacote", self.export_experiment_requested),
            ("btn_figures", "Figuras PNG", self.export_figures_requested),
        ]:
            button = SecondaryButton(text)
            button.clicked.connect(signal.emit)
            button.setEnabled(False)
            setattr(self, name, button)
            self.add_action(button)

    def update_metrics(self, fid=None, pur=None, erg=None):
        for card, value in [
            (self.card_fid, fid),
            (self.card_pur, pur),
            (self.card_erg, erg),
            (self.card_err, None if fid is None else 1 - fid),
        ]:
            card.set_value("—" if value is None else f"{value:.4f}")

    def set_experiment_title(self, title):
        self._display_title = title
        if getattr(self, "_experiment", None) is not None:
            self._update_details()

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
            f"{self._display_title} · {'Circuito livre' if c.circuit is not None else c.system.hamiltonian} · {c.system.num_qubits} qubits · "
            f"{c.shots} shots · {experiment.duration_s:.3f} s · profundidade {r.circuit_depth}\n"
            f"Semente efetiva: {r.metadata.get('effective_seed', 'não registrada')}"
        )

    def show_experiment(self, experiment):
        self._experiment = experiment
        self.state_inspector.set_state(experiment.result.final_state,
                                       experiment.result.ideal_final_state,
                                       "Estado final da execução · calculado pelo simulador")
        self._display_title = experiment_title(experiment)
        r, c = experiment.result, experiment.config
        self.btn_rerun.setText("Reproduzir ZNE" if r.mitigation else "Reexecutar")
        self.btn_rerun.setToolTip("Recalcula a análise ZNE com método, fatores, shots e seed registrados; preserva as métricas da fonte." if r.mitigation else "Executa novamente a configuração com a semente efetiva registrada.")
        self._update_details()
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
        for index in range(self.table.rowCount()):
            bits = f"{index:0{c.system.num_qubits}b}"
            count = (r.counts or {}).get(bits, 0)
            for column, text in enumerate(
                [
                    bits,
                    str(count),
                    f"{count / c.shots:.6f}",
                    "—" if probabilities is None else f"{probabilities[index]:.6f}",
                ]
            ):
                self.table.setItem(index, column, QTableWidgetItem(text))
        self.metadata.setPlainText(
            json.dumps(
                {
                    "id": experiment.id,
                    "config": __import__("dataclasses").asdict(c),
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
