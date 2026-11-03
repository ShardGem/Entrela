"""Página principal de simulação: configuração + execução + status."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget,
    QHBoxLayout,
    QVBoxLayout,
    QSplitter,
    QLabel,
    QFrame,
    QProgressBar,
    QScrollArea,
    QLineEdit,QFormLayout,
)

from gui.pages.base import PageBase
from gui.widgets.card import Card
from gui.widgets.button import PrimaryButton
from gui.icons import get_pixmap
from gui.theme import PALETTE, SPACING
from gui.panels.config_panel import ConfigPanel


class SimulationStatus(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("Card")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(12)

        self._icon = QLabel()
        self._icon.setFixedSize(18, 18)
        layout.addWidget(self._icon)

        self._text = QLabel("Pronto para executar")
        self._text.setWordWrap(True)
        self._text.setStyleSheet(f"color: {PALETTE.text}; font-size: 13px;")
        layout.addWidget(self._text)

        layout.addStretch()

        self._progress = QProgressBar()
        self._progress.setFixedWidth(160)
        self._progress.setTextVisible(False)
        self._progress.setVisible(False)
        layout.addWidget(self._progress)

        self._set_state("idle")

    def _set_state(self, state: str):
        mapping = {
            "idle": ("info", PALETTE.text_muted, "Pronto para executar"),
            "running": ("play", PALETTE.primary, "Simulação em andamento..."),
            "success": ("check", PALETTE.success, "Simulação concluída"),
            "error": ("alert", PALETTE.danger, "Erro na simulação"),
        }
        icon_name, color, text = mapping.get(state, mapping["idle"])
        self._icon.setPixmap(get_pixmap(icon_name, color=color, size=18))
        self._text.setText(text)
        self._progress.setVisible(state == "running")

    def set_running(self):
        self._set_state("running")

    def set_success(self, message: str = "Simulação concluída"):
        self._set_state("success")
        self._text.setText(message)

    def set_error(self, message: str):
        self._set_state("error")
        self._text.setText(message)

    def set_idle(self, message: str = "Pronto para executar"):
        self._set_state("idle")
        self._text.setText(message)


class SimulationPage(PageBase):
    run_requested = Signal(dict)
    cancel_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(
            "Simulação",
            "Configure o sistema quântico, o protocolo e o modelo de ruído.",
        )
        self._build()
        self._refresh_summary()

    def _build(self):
        identity=QFormLayout()
        identity.setRowWrapPolicy(QFormLayout.WrapLongRows)
        self.experiment_name=QLineEdit()
        self.experiment_name.setMaxLength(160)
        self.experiment_name.setPlaceholderText("Ex.: Bell — referência ideal, comparação de ruído…")
        self.experiment_name.setAccessibleName("Nome do experimento")
        self.experiment_description=QLineEdit()
        self.experiment_description.setMaxLength(10000)
        self.experiment_description.setPlaceholderText("Descreva o que deseja investigar; objetivo e hipótese podem ser detalhados no histórico.")
        identity.addRow("Nome do experimento",self.experiment_name)
        identity.addRow("Descrição",self.experiment_description)
        self.body().addLayout(identity)
        splitter = QSplitter(Qt.Horizontal)
        self.splitter = splitter
        splitter.setChildrenCollapsible(False)
        splitter.setHandleWidth(6)

        # Coluna esquerda: configuração
        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(SPACING.lg)

        self.config_panel = ConfigPanel()
        # The page has a persistent primary execution control beside the form.
        self.config_panel.btn_executar.hide()
        self.config_panel.simulacao_acionada.connect(self._emit_run)
        self.config_panel.parametros_alterados.connect(self._refresh_summary)
        left_layout.addWidget(self.config_panel, 1)

        # Coluna direita: resumo + status + execução
        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(SPACING.lg)

        summary = Card(
            "Antes de executar", "Resumo dos parâmetros selecionados."
        )
        self._summary_rows: dict[str, QLabel] = {}
        for key, label in [
            ("sistema", "Sistema"),
            ("initial", "Estado inicial"),
            ("protocolo", "Protocolo"),
            ("ruido", "Modelo de ruído"),
            ("shots", "Shots"),
            ("resources", "Recursos"),
        ]:
            row = QHBoxLayout()
            row.setSpacing(16)
            lbl = QLabel(label)
            lbl.setStyleSheet(
                f"color: {PALETTE.text_muted}; font-size: 12px; min-width: 120px;"
            )
            val = QLabel("—")
            val.setWordWrap(True)
            val.setStyleSheet(
                f"color: {PALETTE.text}; font-size: 13px; font-weight: 500;"
            )
            row.addWidget(lbl)
            row.addWidget(val, 1)
            summary.add_layout(row)
            self._summary_rows[key] = val
        right_layout.addWidget(summary)
        self.configuration_feedback = QLabel()
        self.configuration_feedback.setWordWrap(True)
        self.configuration_feedback.setObjectName("LeadText")
        self.configuration_feedback.setAccessibleName("Validação da configuração")
        right_layout.addWidget(self.configuration_feedback)

        science = Card("Como ler os resultados")
        explanation = QLabel(
            "<b>Fidelidade</b> compara a execução ao mesmo circuito sem ruído. "
            "<b>Pureza global</b> mede a mistura do estado completo. "
            "<b>Energia</b> é a média do Hamiltoniano selecionado.<br><br>"
            "Para separar ruído de aproximação Trotter, use a referência exata em Análises. "
            "ZNE estima um observável e é calculado depois da execução; não produz um estado mitigado."
        )
        explanation.setWordWrap(True)
        science.add(explanation)
        right_layout.addWidget(science)

        self.status = SimulationStatus()
        right_layout.addWidget(self.status)

        action_card = Card()
        btn_row = QHBoxLayout()
        btn_row.setSpacing(SPACING.md)
        self.btn_run = PrimaryButton("Executar simulação", icon="play")
        self.btn_run.setMinimumHeight(44)
        self.btn_run.clicked.connect(self._emit_run)
        btn_row.addWidget(self.btn_run, 1)
        self.btn_cancel = PrimaryButton("Cancelar")
        self.btn_cancel.setEnabled(False)
        self.btn_cancel.clicked.connect(self.cancel_requested.emit)
        btn_row.addWidget(self.btn_cancel)
        action_card.add_layout(btn_row)
        right_layout.addWidget(action_card)
        # Keep execution available before the explanatory content. A scroll area
        # honors labels' height-for-width; a raw splitter child can compress
        # wrapped summary text to a few pixels on a projector-sized display.
        right_layout.removeWidget(self.status)
        right_layout.removeWidget(action_card)
        right_layout.insertWidget(0, self.status)
        right_layout.insertWidget(1, action_card)

        right_layout.addStretch()

        splitter.addWidget(left)
        self.summary_scroll = QScrollArea()
        self.summary_scroll.setFrameShape(QFrame.NoFrame)
        self.summary_scroll.setWidgetResizable(True)
        self.summary_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.summary_scroll.setMinimumWidth(300)
        self.summary_scroll.setWidget(right)
        splitter.addWidget(self.summary_scroll)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 2)
        splitter.setSizes([560, 420])

        self.body().addWidget(splitter, 1)

    def _emit_run(self):
        params = self.config_panel.coletar_tudo()
        self.run_requested.emit(params)

    def _refresh_summary(self):
        p = self.config_panel.coletar_tudo()
        self._summary_rows["sistema"].setText(
            f"{p['hamiltoniano']} · {p['qubits']} qubits · J={p['J']}, h={p['h']}"
        )
        self._summary_rows["initial"].setText(
            self.config_panel.combo_initial.currentText()
        )
        self._summary_rows["protocolo"].setText(
            f"T={p['tempo']} · {p['passos']} passos Trotter"
            + (" · snapshots" if p["salvar_snaps"] else "")
        )
        if p["ruido_ativo"]:
            if "Térm" in p["modelo_ruido"]:
                self._summary_rows["ruido"].setText(
                    f"Térmico · T1={p['t1']}µs, T2={p['t2']}µs"
                )
            else:
                self._summary_rows["ruido"].setText(
                    f"Despolarizador · p1={p['p1']}, p2={p['p2']}"
                )
        else:
            self._summary_rows["ruido"].setText("Desativado (ideal)")
        from core.types import resource_estimate

        try:
            config = self.config_panel.get_config()
            estimate = resource_estimate(config)
            self._summary_rows["resources"].setText(
                f"{estimate['snapshots']} snapshots · {estimate['state_bytes'] / 1024**2:.2f} MiB de estados brutos; JSON e renderização consomem mais. Limites: 6 qubits, 200 passos."
            )
            self.configuration_feedback.setText(
                "Configuração válida. Este resumo não simula nem prevê as métricas; "
                "execute para obter os resultados e registrá-los no histórico."
            )
        except ValueError as exc:
            self._summary_rows["resources"].setText("Revise a configuração.")
            self.configuration_feedback.setText(f"Antes de executar, ajuste: {exc}")
        self._summary_rows["shots"].setText(
            f"{p['shots']:,} · semente {p['seed'] or 'automática'}"
        )

    def set_running(self, running: bool):
        self.btn_run.setEnabled(not running)
        self.btn_cancel.setEnabled(running)
        self.config_panel.setEnabled(not running)
        self.btn_run.setText("Executando..." if running else "Executar simulação")
        if running:
            self.status.set_running()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, "splitter"):
            font_scale = max(1., self.font().pixelSize() / 15)
            vertical=self.width()<860 * font_scale
            self.splitter.setOrientation(
                Qt.Vertical if vertical else Qt.Horizontal
            )
            self.splitter.widget(0).setMinimumHeight(480 if vertical else 360)
            self.summary_scroll.setMinimumHeight(300 if vertical else 0)
