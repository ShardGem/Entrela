"""Scientific workbench: an editable configuration, an honest preview and a fixed execution bar."""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal, QEvent
from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QSplitter, QLabel, QFrame,
    QProgressBar, QScrollArea, QLineEdit, QToolButton, QMenu,
    QGridLayout,
)
from gui.pages.base import PageBase
from gui.widgets.content_tabs import ContentTabs
from gui.design_system import Surface, LAYOUT
from gui.widgets.flow_layout import FlowLayout
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
    workbench_changed = Signal()
    run_requested = Signal(dict)
    cancel_requested = Signal()
    example_requested = Signal(str)
    navigation_requested = Signal(str)

    def __init__(self, parent=None):
        super().__init__("Configurar experimento", "Defina o sistema, revise o protocolo e execute uma simulação reproduzível.",parent)
        self._running = False
        self._valid = True
        self._validation_error = False
        self._error_section = "system"
        self._compact = False
        self.body().setSpacing(12)
        self.body().setContentsMargins(20,4,20,16)
        self._build()
        self._refresh_summary()

    def _build(self):
        self.examples_button = GhostButton("Exemplos", icon="examples")
        self.examples_button.setToolTip("Carregar uma configuração demonstrativa existente. Nenhuma simulação é executada ao escolher o exemplo.")
        examples = QMenu(self.examples_button)
        from core.examples import get_example
        for identifier in ("first-qubit","bell","ising","depolarizing-bell","thermal-ising"):
            example = get_example(identifier)
            action = examples.addAction(example.title)
            action.setToolTip(example.description)
            action.triggered.connect(lambda checked=False,key=identifier: self.example_requested.emit(key))
        self.examples_button.setMenu(examples)

        identity = QFrame()
        identity.setObjectName("DocumentHeader")
        identity_body = QVBoxLayout(identity)
        identity_body.setContentsMargins(0, 0, 0, 0)
        identity_body.setSpacing(2)
        role = QLabel("Rascunho")
        self.draft_role = role
        role.setObjectName("Eyebrow")
        identity_body.addWidget(role)
        row = QHBoxLayout()
        self.experiment_name = QLineEdit()
        self.experiment_name.setObjectName("DocumentTitle")
        self.experiment_name.setMaxLength(160)
        self.experiment_name.setPlaceholderText("Simulação sem título")
        self.experiment_name.setAccessibleName("Nome do experimento")
        row.addWidget(self.experiment_name, 1)
        self.description_toggle = QToolButton()
        self.description_toggle.setText("Descrição")
        self.description_toggle.setCheckable(True)
        self.description_toggle.setArrowType(Qt.RightArrow)
        self.description_toggle.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        identity_body.addLayout(row)
        self.setup_actions = FlowLayout(spacing=8)
        self.setup_actions.addWidget(self.examples_button)
        self.setup_actions.addWidget(self.description_toggle)
        identity_body.addLayout(self.setup_actions)
        self.description_row = QWidget()
        desc = QHBoxLayout(self.description_row)
        desc.setContentsMargins(0, 0, 0, 0)
        self.experiment_description = QLineEdit()
        self.experiment_description.setAccessibleName("Descrição do experimento")
        self.experiment_description.setMaxLength(10000)
        self.experiment_description.setPlaceholderText("Qual pergunta você deseja investigar?")
        desc.addWidget(self.experiment_description)
        identity_body.addWidget(self.description_row)
        self.description_row.hide()
        self.description_toggle.toggled.connect(self.description_row.setVisible)
        self.description_toggle.toggled.connect(lambda opened: self.description_toggle.setArrowType(Qt.DownArrow if opened else Qt.RightArrow))

        self.body().addWidget(identity)

        self.splitter = QSplitter(Qt.Horizontal)
        self.splitter.setChildrenCollapsible(False)
        self.splitter.setHandleWidth(LAYOUT.handle_width)
        self.config_panel = ConfigPanel()
        self.config_panel.setObjectName("ParameterWorkspace")
        self.config_panel.setAttribute(Qt.WA_StyledBackground, True)
        self.config_panel.layout().setContentsMargins(4, 14, 24, 8)
        self.config_panel.set_inspector_mode(False)
        self.inspector_title = QLabel("Sistema e estado inicial")
        self.inspector_title.setObjectName("WorkspaceSectionTitle")
        self.config_panel.layout().insertWidget(0, self.inspector_title)
        self.config_panel.btn_executar.hide()
        self.config_panel.simulacao_acionada.connect(self._emit_run)
        self.config_panel.parametros_alterados.connect(self._refresh_summary)

        self.steps = QWidget()
        steps_layout = QVBoxLayout(self.steps)
        steps_layout.setContentsMargins(0, 0, 0, 0)
        steps_layout.addWidget(self.config_panel.section_nav)
        self.config_panel.external_steps = True
        self.config_panel._section_columns = 0
        self.config_panel._arrange_sections()
        self.config_panel._present()
        self.stage = Surface("Plano da simulação", role="WorkbenchInspector")
        self.stage.add(self.steps)
        self.preparation = PreparationPreview()
        self.state_caption = QLabel()
        self.state_caption.setObjectName("StateFormula")
        self.state_caption.setWordWrap(True)
        self.state_caption.setTextFormat(Qt.PlainText)
        self.initial_preview_section = CollapsibleSection('Prévia ideal de preparação', expanded=True)
        self.initial_preview_section.content_layout.addWidget(self.preparation)
        self.initial_preview_section.content_layout.addWidget(self.state_caption)
        system_content = self.config_panel.sections['system'].content_layout
        system_fields = self.config_panel.forms['system']
        system_content.removeItem(system_fields)
        self.system_layout = QHBoxLayout()
        self.system_layout.setSpacing(20)
        self.system_layout.addLayout(system_fields, 1)
        self.system_layout.addWidget(self.initial_preview_section, 1, Qt.AlignTop)
        system_content.addLayout(self.system_layout)
        self.protocol = CollapsibleSection("Revisar parâmetros")
        protocol_layout = self.protocol.content_layout
        grid = QGridLayout()
        grid.setHorizontalSpacing(20)
        grid.setVerticalSpacing(14)
        grid.setColumnStretch(1, 1)
        self._summary_rows = {}
        for index, (key, text) in enumerate((("sistema", "Sistema"), ("initial", "Preparação"), ("protocolo", "Evolução"),
                                            ("ruido", "Ruído"), ("shots", "Medições"), ("resources", "Registro"))):
            label = QLabel(text)
            label.setObjectName("FieldLabel")
            value = QLabel("—")
            value.setObjectName("SummaryValue")
            value.setWordWrap(True)
            grid.addWidget(label, index, 0, Qt.AlignTop)
            grid.addWidget(value, index, 1)
            self._summary_rows[key] = value
        protocol_layout.addLayout(grid)
        self.diagnostics = QLabel()
        self.diagnostics.setObjectName("FieldHint")
        self.diagnostics.setWordWrap(True)
        self.diagnostics.setTextFormat(Qt.PlainText)
        self.diagnostics.setAccessibleName("Orientações científicas para a configuração")
        self.diagnostics_section = CollapsibleSection("O que esperar desta configuração")
        self.diagnostics_section.content_layout.addWidget(self.diagnostics)
        protocol_layout.addWidget(self.diagnostics_section)
        self.science = CollapsibleSection("Método e interpretação")
        explanation = QLabel("Fidelidade compara com o mesmo circuito sem ruído; a referência exata em Estudos permite avaliar a aproximação Trotter. Pureza global mede mistura do sistema completo. Energia é a média do Hamiltoniano. ZNE extrapola observáveis e não reconstrói um estado mitigado.")
        explanation.setWordWrap(True)
        explanation.setObjectName("FieldHint")
        self.science.content_layout.addWidget(explanation)
        self.science.set_summary("Simulação local · estado ideal ou ensemble ruidoso")
        protocol_layout.addWidget(self.science)
        self.stage.add(self.protocol)
        self.config_panel.section_changed.connect(self._step_selected)
        self.summary_scroll = QScrollArea()
        self.summary_scroll.setWidgetResizable(True)
        self.summary_scroll.setFrameShape(QFrame.NoFrame)
        self.summary_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.summary_scroll.setMinimumWidth(240)
        self.summary_scroll.setWidget(self.stage)
        self.splitter.addWidget(self.config_panel)
        self.splitter.addWidget(self.summary_scroll)
        self.splitter.setStretchFactor(0, 1)
        self.splitter.setStretchFactor(1, 0)
        self.splitter.setSizes([840, 300])
        self.body().addWidget(self.splitter, 1)
        self.compact_tabs = ContentTabs()
        self.compact_tabs.setDocumentMode(True)
        self.compact_tabs.hide()
        self.body().addWidget(self.compact_tabs, 1)

        self.execution_bar = QFrame()
        self.execution_bar.setObjectName("ExecutionBar")
        footer = QVBoxLayout(self.execution_bar)
        footer.setContentsMargins(20,10,20,12)
        footer.setSpacing(8)
        self.configuration_feedback = QLabel()
        self.configuration_feedback.setObjectName("ValidationMessage")
        self.configuration_feedback.setWordWrap(True)
        self.configuration_feedback.setAccessibleName("Validação da configuração")
        self.revise_button = GhostButton("Revisar parâmetros")
        self.revise_button.clicked.connect(lambda: self._review_error())
        actions = QHBoxLayout()
        actions.setSpacing(12)
        self.status = SimulationStatus()
        actions.addWidget(self.status, 1)
        actions.addWidget(self.configuration_feedback, 1)
        actions.addWidget(self.revise_button)
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
        last = QVBoxLayout(self.last_result_row)
        last.setContentsMargins(0, 4, 0, 0)
        self.last_result_label = QLabel()
        self.last_result_label.setObjectName("FieldHint")
        self.last_result_label.setWordWrap(True)
        self.last_result_label.setTextFormat(Qt.PlainText)
        last.addWidget(self.last_result_label)
        self.last_results = GhostButton("Abrir resultados", icon="results")
        self.last_results.clicked.connect(lambda: self.navigation_requested.emit("results"))
        last.addWidget(self.last_results, 0, Qt.AlignLeft)
        self.stage.add(self.last_result_row)
        self.stage.body().addStretch()
        self.last_result_row.hide()
        self._root.addWidget(self.execution_bar)
        self._scroll.takeWidget()
        self._scroll.hide()
        self._root.insertWidget(1, self._body_widget, 1)

    def add_setup_action(self, button):
        self.setup_actions.addWidget(button)

    def _emit_run(self):
        try:
            self.validate_configuration()
        except ValueError:
            self._review_error()
            return
        self.run_requested.emit(self.config_panel.coletar_tudo())

    def _step_selected(self, key):
        self.inspector_title.setText({'system':'Sistema e estado inicial', 'hamiltonian':'Hamiltoniano',
            'evolution':'Evolução temporal', 'noise':'Modelo de ruído', 'execution':'Execução e amostragem'}[key])

    def validate_configuration(self):
        """One validation path for the form, footer, button and execution shortcut."""
        self._refresh_summary()
        return self.config_panel.get_config()

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
        self.protocol.set_summary(f"{p['hamiltoniano']} · {p['qubits']} qubits · {p['passos']} passos")
        from core.types import resource_estimate
        try:
            config = self.config_panel.get_config()
            from core.experiment_diagnostics import diagnose_experiment
            diagnostics = diagnose_experiment(config)
            self.diagnostics.setText("\n\n".join(item.title + ": " + item.message for item in diagnostics))
            self.diagnostics_section.set_summary(" · ".join(item.title for item in diagnostics))
            self.diagnostics_section.setVisible(bool(diagnostics))
            estimate = resource_estimate(config)
            self._summary_rows['resources'].setText(f"{estimate['snapshots']} snapshots · {estimate['state_bytes']/1024**2:.2f} MiB")
            self._summary_rows['resources'].setToolTip("Estimativa dos estados brutos. JSON e renderização consomem mais memória. Limites: 6 qubits e 200 passos.")
            self.configuration_feedback.setText("Configuração válida · pronta para executar e registrar no histórico.")
            self._valid = True
            if self._validation_error or self.status.state == 'idle':
                self.status.set_idle('Configuração válida')
            self._validation_error = False
        except ValueError as exc:
            self.diagnostics.clear()
            self.diagnostics_section.hide()
            message = str(exc)
            self._valid = False
            self._validation_error = True
            if not self._running:
                self.status.set_error(message)
            self._summary_rows['resources'].setText("Revisar configuração")
            self.configuration_feedback.setText("Antes de executar, ajuste: " + message)
            self._error_section = "execution" if "Semente" in message else "system" if "Bell" in message or "Qubit" in message else "noise"
        for key, button in self.config_panel.section_buttons.items():
            invalid = not self._valid and key == self._error_section
            button.setProperty('invalid', invalid)
            button.setText(('!  ' if invalid else '') + {'system':'Sistema', 'hamiltonian':'Hamiltoniano', 'evolution':'Evolução', 'noise':'Ruído', 'execution':'Execução'}[key])
            button.style().unpolish(button); button.style().polish(button)
        self.configuration_feedback.setProperty('state','valid' if self._valid else 'error')
        self.configuration_feedback.style().unpolish(self.configuration_feedback)
        self.configuration_feedback.style().polish(self.configuration_feedback)
        self._update_actions()

    def _update_actions(self):
        self.btn_run.setEnabled(not self._running and self._valid)
        self.btn_cancel.setEnabled(self._running)
        self.btn_cancel.setVisible(self._running)
        self.configuration_feedback.setVisible(not self._valid and not self._running)
        self.revise_button.setVisible(not self._valid and not self._running)
        self.status.setVisible(self._valid or self._running)

    def _review_error(self):
        if self._compact:
            self.compact_tabs.setCurrentWidget(self.config_panel)
        self.config_panel.set_section(self._error_section)

    def set_experiment(self, experiment, title):
        self._source_experiment = experiment
        self.last_result_label.setText(f"Execução selecionada\n{title}")
        self.last_result_row.show()

    def clear_experiment(self):
        self._source_experiment = None
        self.last_result_label.clear()
        self.last_result_row.hide()

    def set_running(self, running):
        self._running = running
        self.config_panel.setEnabled(not running)
        self.experiment_name.setEnabled(not running)
        self.experiment_description.setEnabled(not running)
        self.examples_button.setEnabled(not running)
        self.btn_run.setText("Executando…" if running else "Executar simulação")
        self._refresh_summary()
        if running:
            self.status.set_running()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._arrange_workbench()

    def _arrange_header(self):
        super()._arrange_header()
        if getattr(self, "_embedded_heading", False):
            self._header.hide()
        self.body().setContentsMargins(LAYOUT.page_margin, 4, LAYOUT.page_margin, LAYOUT.control_gap)
    def changeEvent(self, event):
        super().changeEvent(event)
        if event.type() in (QEvent.FontChange, QEvent.StyleChange):
            self._arrange_workbench()

    def _arrange_workbench(self):
        if not hasattr(self,'compact_tabs'):
            return
        scale = max(1, self.fontMetrics().height() / 19)
        wide_preview = self.width() > 1110 * scale
        self.system_layout.setDirection(QHBoxLayout.LeftToRight if wide_preview else QHBoxLayout.TopToBottom)
        compact = self.width() < 900 * max(1, self.font().pixelSize() / 15)
        if compact == self._compact:
            return
        self._compact = compact
        self.draft_role.setVisible(not compact)
        self.inspector_title.setVisible(not compact)
        self._update_actions()
        if compact:
            self.config_panel.external_steps = False
            self.config_panel._present()
            self.steps.hide()
            self.splitter.hide()
            self.compact_tabs.addTab(self.config_panel,"Parâmetros")
            self.compact_tabs.addTab(self.summary_scroll,"Plano da simulação")
            self.config_panel.setMaximumWidth(16777215)
            self.summary_scroll.setMaximumWidth(16777215)
            self.compact_tabs.show()
        else:
            while self.compact_tabs.count():
                self.compact_tabs.removeTab(0)
            self.compact_tabs.hide()
            self.splitter.insertWidget(0, self.config_panel)
            self.splitter.addWidget(self.summary_scroll)
            self.config_panel.setMaximumWidth(16777215)
            self.config_panel.setMinimumWidth(360)
            self.summary_scroll.setMinimumWidth(280)
            self.summary_scroll.setMaximumWidth(380)
            self.config_panel.external_steps = True
            self.config_panel._section_columns = 0
            self.config_panel._arrange_sections()
            self.config_panel._present()
            self.steps.show(); self.config_panel.show(); self.summary_scroll.show()
            self.splitter.setSizes([840, 300])
            self.splitter.show()
        self.workbench_changed.emit()
