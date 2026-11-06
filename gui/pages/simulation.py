"""Scientific workbench: an editable configuration, an honest preview and a fixed execution bar."""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal, QEvent
from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QSplitter, QLabel, QFrame,
    QProgressBar, QScrollArea, QLineEdit, QToolButton, QMenu,
    QGridLayout, QTabWidget,
)
from gui.pages.base import PageBase
from gui.widgets.card import Card
from gui.widgets.button import PrimaryButton, SecondaryButton, GhostButton
from gui.widgets.collapsible import CollapsibleSection
from gui.widgets.preparation_preview import PreparationPreview
from gui.icons import get_pixmap
from gui.theme import PALETTE
from gui.panels.config_panel import ConfigPanel


class SimulationStatus(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("ExecutionStatus")
        self.state = "idle"
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0,0,0,0)
        layout.setSpacing(10)
        self._icon = QLabel()
        self._icon.setFixedSize(18,18)
        layout.addWidget(self._icon)
        self._text = QLabel()
        self._text.setWordWrap(True)
        self._text.setAccessibleName("Estado da execução")
        layout.addWidget(self._text,1)
        self._progress = QProgressBar()
        self._progress.setMaximumWidth(110)
        self._progress.setTextVisible(False)
        self._progress.setAccessibleName("Progresso da tarefa")
        layout.addWidget(self._progress)
        self._set_state("idle")

    def _set_state(self, state, message=None):
        self.state = state
        defaults = dict(idle="Pronto para executar",running="Simulação em andamento…",
                        success="Simulação concluída",error="Revise a execução")
        self._text.setText(message or defaults[state])
        self._progress.setVisible(state == "running")
        self.refresh_theme()

    def refresh_theme(self):
        name,color = {"idle":("info",PALETTE.text_muted),"running":("play",PALETTE.primary),
                      "success":("check",PALETTE.success),"error":("alert",PALETTE.danger)}[self.state]
        self._icon.setPixmap(get_pixmap(name,color=color,size=18))

    def set_running(self, message=None):
        self._progress.setValue(0)
        self._set_state("running",message)

    def set_success(self, message="Simulação concluída"):
        self._set_state("success",message)

    def set_error(self, message):
        self._set_state("error",message)

    def set_idle(self, message="Pronto para executar"):
        self._set_state("idle",message)


class SimulationPage(PageBase):
    run_requested = Signal(dict)
    cancel_requested = Signal()
    example_requested = Signal(str)
    navigation_requested = Signal(str)

    def __init__(self, parent=None):
        super().__init__("Configurar experimento", "Defina o sistema, revise o protocolo e execute uma simulação reproduzível.",parent)
        self._running = False
        self._valid = True
        self._error_section = "system"
        self._compact = False
        self.body().setSpacing(12)
        self.body().setContentsMargins(20,4,20,16)
        self._build()
        self._refresh_summary()

    def _build(self):
        self.examples_button = SecondaryButton("Exemplos",icon="examples")
        self.examples_button.setToolTip("Carregar uma configuração demonstrativa existente. Nenhuma simulação é executada ao escolher o exemplo.")
        examples = QMenu(self.examples_button)
        from core.examples import get_example
        for identifier in ("first-qubit","bell","ising","depolarizing-bell","thermal-ising"):
            example = get_example(identifier)
            action = examples.addAction(example.title)
            action.setToolTip(example.description)
            action.triggered.connect(lambda checked=False,key=identifier: self.example_requested.emit(key))
        self.examples_button.setMenu(examples)
        self.add_action(self.examples_button)

        identity = Card(padding=12)
        identity.setObjectName("IdentityCard")
        identity.body().setSpacing(8)
        row = QHBoxLayout()
        label = QLabel("Experimento")
        label.setObjectName("FieldLabel")
        row.addWidget(label)
        self.experiment_name = QLineEdit()
        self.experiment_name.setMaxLength(160)
        self.experiment_name.setPlaceholderText("Nome opcional · ex.: Bell — referência ideal")
        self.experiment_name.setAccessibleName("Nome do experimento")
        label.setBuddy(self.experiment_name)
        row.addWidget(self.experiment_name,1)
        self.description_toggle = QToolButton()
        self.description_toggle.setObjectName("DescriptionToggle")
        self.description_toggle.setText("Descrição")
        self.description_toggle.setCheckable(True)
        self.description_toggle.setArrowType(Qt.RightArrow)
        self.description_toggle.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        row.addWidget(self.description_toggle)
        identity.add_layout(row)
        self.description_row = QWidget()
        desc = QHBoxLayout(self.description_row)
        desc.setContentsMargins(0,0,0,0)
        self.experiment_description = QLineEdit()
        self.experiment_description.setAccessibleName("Descrição do experimento")
        self.experiment_description.setMaxLength(10000)
        self.experiment_description.setPlaceholderText("O que deseja investigar? Hipótese e metodologia podem ser detalhadas no caderno do experimento.")
        desc.addWidget(self.experiment_description)
        identity.add(self.description_row)
        self.description_row.hide()
        self.description_toggle.toggled.connect(self.description_row.setVisible)
        self.description_toggle.toggled.connect(lambda opened: self.description_toggle.setArrowType(Qt.DownArrow if opened else Qt.RightArrow))
        self.experiment_description.textChanged.connect(lambda text: self.description_toggle.setChecked(True) if text else None)
        self.body().addWidget(identity)

        self.splitter = QSplitter(Qt.Horizontal)
        self.splitter.setChildrenCollapsible(False)
        self.splitter.setHandleWidth(6)
        self.config_panel = ConfigPanel()
        self.config_panel.btn_executar.hide()
        self.config_panel.simulacao_acionada.connect(self._emit_run)
        self.config_panel.parametros_alterados.connect(self._refresh_summary)
        self.splitter.addWidget(self.config_panel)

        right = QWidget()
        layout = QVBoxLayout(right)
        layout.setContentsMargins(0,0,0,0)
        layout.setSpacing(12)
        review = Card("Preparação e revisão", "Referência ideal da preparação · sem ruído",padding=16)
        review.body().setSpacing(12)
        self.preparation = PreparationPreview()
        review.add(self.preparation)
        self.state_caption = QLabel()
        self.state_caption.setObjectName("StateFormula")
        self.state_caption.setWordWrap(True)
        self.state_caption.setTextFormat(Qt.PlainText)
        review.add(self.state_caption)
        grid = QGridLayout()
        grid.setHorizontalSpacing(12)
        grid.setVerticalSpacing(10)
        grid.setColumnStretch(1,1)
        self._summary_rows = {}
        for index,(key,text) in enumerate((("sistema","Sistema"),("initial","Preparação"),("protocolo","Evolução"),
                                           ("ruido","Ruído"),("shots","Medições"),("resources","Registro"))):
            label = QLabel(text)
            label.setObjectName("FieldLabel")
            value = QLabel("—")
            value.setObjectName("SummaryValue")
            value.setWordWrap(True)
            value.setMinimumHeight(value.fontMetrics().height())
            grid.addWidget(label,index,0,Qt.AlignTop)
            grid.addWidget(value,index,1)
            self._summary_rows[key] = value
        review.add_layout(grid)
        note = QLabel("Esta prévia descreve a configuração. Os resultados são calculados ao executar.")
        note.setWordWrap(True)
        note.setObjectName("FieldHint")
        review.add(note)
        layout.addWidget(review)
        self.science = CollapsibleSection("Método e interpretação")
        explanation = QLabel("Fidelidade compara com o mesmo circuito sem ruído; a referência exata em Análises permite avaliar a aproximação Trotter. Pureza global mede mistura do sistema completo. Energia é a média do Hamiltoniano. ZNE extrapola observáveis e não reconstrói um estado mitigado.")
        explanation.setWordWrap(True)
        explanation.setObjectName("FieldHint")
        self.science.content_layout.addWidget(explanation)
        self.science.set_summary("Simulação local · estado ideal ou ensemble ruidoso")
        layout.addWidget(self.science)
        layout.addStretch()
        self.summary_scroll = QScrollArea()
        self.summary_scroll.setWidgetResizable(True)
        self.summary_scroll.setFrameShape(QFrame.NoFrame)
        self.summary_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.summary_scroll.setMinimumWidth(280)
        self.summary_scroll.setWidget(right)
        self.splitter.addWidget(self.summary_scroll)
        self.splitter.setStretchFactor(0,3)
        self.splitter.setStretchFactor(1,2)
        self.splitter.setSizes([640,380])
        self.body().addWidget(self.splitter,1)
        self.compact_tabs = QTabWidget()
        self.compact_tabs.setObjectName("WorkbenchTabs")
        self.compact_tabs.setDocumentMode(True)
        self.compact_tabs.tabBar().setDrawBase(False)
        self.compact_tabs.hide()
        self.body().addWidget(self.compact_tabs,1)

        self.execution_bar = QFrame()
        self.execution_bar.setObjectName("ExecutionBar")
        footer = QVBoxLayout(self.execution_bar)
        footer.setContentsMargins(20,10,20,12)
        footer.setSpacing(8)
        validation = QHBoxLayout()
        self.configuration_feedback = QLabel()
        self.configuration_feedback.setObjectName("ValidationMessage")
        self.configuration_feedback.setWordWrap(True)
        self.configuration_feedback.setAccessibleName("Validação da configuração")
        validation.addWidget(self.configuration_feedback,1)
        self.revise_button = GhostButton("Revisar parâmetros")
        self.revise_button.clicked.connect(lambda: self._review_error())
        validation.addWidget(self.revise_button)
        footer.addLayout(validation)
        actions = QHBoxLayout()
        actions.setSpacing(12)
        self.status = SimulationStatus()
        actions.addWidget(self.status,1)
        self.btn_cancel = SecondaryButton("Cancelar")
        self.btn_cancel.setEnabled(False)
        self.btn_cancel.clicked.connect(self.cancel_requested.emit)
        actions.addWidget(self.btn_cancel)
        self.btn_run = PrimaryButton("Executar simulação",icon="play")
        self.btn_run.setMinimumHeight(42)
        self.btn_run.clicked.connect(self._emit_run)
        actions.addWidget(self.btn_run)
        footer.addLayout(actions)
        self.last_result_row = QWidget()
        last = QHBoxLayout(self.last_result_row)
        last.setContentsMargins(0,0,0,0)
        self.last_result_label = QLabel("Execução selecionada")
        self.last_result_label.setObjectName("FieldHint")
        self.last_result_label.setWordWrap(True)
        last.addWidget(self.last_result_label,1)
        self.last_results = GhostButton("Ver resultados",icon="results")
        self.last_results.clicked.connect(lambda: self.navigation_requested.emit("results"))
        self.last_bloch = GhostButton("Abrir estados 3D",icon="bloch")
        self.last_bloch.clicked.connect(lambda: self.navigation_requested.emit("bloch"))
        last.addWidget(self.last_results)
        last.addWidget(self.last_bloch)
        footer.addWidget(self.last_result_row)
        self.last_result_row.hide()
        self._root.addWidget(self.execution_bar)

    def _emit_run(self):
        self.run_requested.emit(self.config_panel.coletar_tudo())

    def _refresh_summary(self):
        p = self.config_panel.coletar_tudo()
        self.preparation.set_preparation(p['qubits'],self.config_panel.combo_initial.currentData())
        self.state_caption.setText({"zero":f"Ideal: |ψ₀⟩ = |0⟩⊗{p['qubits']}","plus":f"Ideal: |ψ₀⟩ = |+⟩⊗{p['qubits']}",
                                    "bell":"Ideal: |ψ₀⟩ = (|00⟩ + |11⟩)/√2"}[self.config_panel.combo_initial.currentData()])
        if self.config_panel.combo_initial.currentData() == "bell" and p['qubits'] != 2:
            self.state_caption.setText("Bell requer dois qubits.")
        field = f", h={p['h']:g}" if p['hamiltoniano'] in ('Ising','Custom') else ''
        self._summary_rows['sistema'].setText(f"{p['hamiltoniano']} · {p['qubits']} qubits · J={p['J']:g}{field}")
        self._summary_rows['initial'].setText(self.config_panel.combo_initial.currentText())
        self._summary_rows['protocolo'].setText(f"T={p['tempo']:g} · {p['passos']} passos · ordem {self.config_panel.combo_order.currentData()}")
        self._summary_rows['ruido'].setText("Desativado · ideal" if not p['ruido_ativo'] else
            f"Térmico · T₁={p['t1']:g} µs · T₂={p['t2']:g} µs" if "Térm" in p['modelo_ruido'] else
            f"Despolarizador · p₁={p['p1']:g} · p₂={p['p2']:g}")
        self._summary_rows['shots'].setText(f"{p['shots']:,} shots · semente {p['seed'] or 'automática'}".replace(',','.'))
        from core.types import resource_estimate
        try:
            config = self.config_panel.get_config()
            estimate = resource_estimate(config)
            self._summary_rows['resources'].setText(f"{estimate['snapshots']} snapshots · {estimate['state_bytes']/1024**2:.2f} MiB")
            self._summary_rows['resources'].setToolTip("Estimativa dos estados brutos. JSON e renderização consomem mais memória. Limites: 6 qubits e 200 passos.")
            self.configuration_feedback.setText("Configuração válida · pronta para executar e registrar no histórico.")
            self._valid = True
        except ValueError as exc:
            message = str(exc)
            self._valid = False
            self._summary_rows['resources'].setText("Revisar configuração")
            self.configuration_feedback.setText("Antes de executar, ajuste: " + message)
            self._error_section = "execution" if "Semente" in message else "system" if "Bell" in message or "Qubit" in message else "noise"
        self.configuration_feedback.setProperty('state','valid' if self._valid else 'error')
        self.configuration_feedback.style().unpolish(self.configuration_feedback)
        self.configuration_feedback.style().polish(self.configuration_feedback)
        self.revise_button.setVisible(not self._valid)
        self._update_actions()

    def _update_actions(self):
        self.btn_run.setEnabled(not self._running and self._valid)
        self.btn_cancel.setEnabled(self._running)

    def _review_error(self):
        if self._compact:
            self.compact_tabs.setCurrentWidget(self.config_panel)
        self.config_panel.set_section(self._error_section)

    def set_experiment(self, experiment, title):
        self.last_result_row.show()
        self.last_result_label.setText("Execução selecionada disponível")
        self.last_result_label.setToolTip(title)
        self.last_bloch.setEnabled(bool(experiment.result.states))
        self.last_bloch.setToolTip("Snapshots da execução selecionada" if experiment.result.states else "Esta execução não salvou snapshots")

    def set_running(self, running):
        self._running = running
        self.config_panel.setEnabled(not running)
        self.experiment_name.setEnabled(not running)
        self.experiment_description.setEnabled(not running)
        self.examples_button.setEnabled(not running)
        self.btn_run.setText("Executando…" if running else "Executar simulação")
        self._refresh_summary()
        if running:
            self.configuration_feedback.setText("Tarefa em andamento · aguarde ou cancele para editar os parâmetros.")
            self.revise_button.hide()
            self.status.set_running()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._arrange_workbench()

    def _arrange_header(self):
        super()._arrange_header()
        # O menu estreito mantém os nomes; use o espaço real antes de empilhar
        # o único botão desta página e criar outra rolagem com fonte ampliada.
        if self._actions_slot.count() != 1:
            return
        action = self._actions_slot.itemAt(0)
        text_width = max(self._title.minimumSizeHint().width(), self._subtitle.minimumSizeHint().width())
        if text_width + action.sizeHint().width() + 72 <= self.width():
            self._header.layout().setDirection(QHBoxLayout.LeftToRight)

    def changeEvent(self, event):
        super().changeEvent(event)
        if event.type() in (QEvent.FontChange, QEvent.StyleChange):
            self._arrange_workbench()

    def _arrange_workbench(self):
        if not hasattr(self,'compact_tabs'):
            return
        compact = self.width() < 960*max(1,self.font().pixelSize()/15)
        if compact == self._compact:
            return
        self._compact = compact
        if compact:
            self.splitter.hide()
            self.compact_tabs.addTab(self.config_panel,"Parâmetros")
            self.compact_tabs.addTab(self.summary_scroll,"Prévia e revisão")
            self.compact_tabs.show()
        else:
            while self.compact_tabs.count():
                self.compact_tabs.removeTab(0)
            self.compact_tabs.hide()
            self.splitter.addWidget(self.config_panel)
            self.splitter.addWidget(self.summary_scroll)
            self.config_panel.show()
            self.summary_scroll.show()
            self.splitter.setSizes([640,380])
            self.splitter.show()
