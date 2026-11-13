"""Editable circuit workbench, undoable documents and real execution settings."""

from dataclasses import replace
from pathlib import Path
import json
import math
from textwrap import fill
import unicodedata
from PySide6.QtCore import Qt, Signal, QSignalBlocker, QMimeData, QEvent, QTimer, QSize, QItemSelectionModel
from PySide6.QtGui import QUndoStack, QUndoCommand, QKeySequence, QAction
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QFormLayout,
    QLabel,
    QComboBox,
    QSpinBox,
    QLineEdit,
    QCheckBox,
    QToolButton,
    QMenu,
    QScrollArea,
    QFileDialog,
    QApplication,
    QPlainTextEdit,
    QMessageBox,
    QFrame,
    QTabWidget,
    QSplitter,
    QListWidget,
    QListWidgetItem,
    QAbstractItemView,
)
from core.circuit_document import (
    CircuitDocument,
    CircuitGate,
    GATES,
    GATE_HELP,
    parse_angle,
)
from core.types import ExperimentConfig, SystemConfig, SimulationProtocol, NoiseConfig
from gui.widgets.circuit_canvas import CircuitCanvas
from gui.widgets.button import PrimaryButton, SecondaryButton, GhostButton
from gui.widgets.content_tabs import ContentTabs
from gui.widgets.scientific_input import ScientificSpinBox
from gui.widgets.flow_layout import FlowLayout
from gui.widgets.collapsible import CollapsibleSection
from gui.widgets.circuit_guidance import GATE_NAMES, ANGLE_HELP, PHASE_HELP, TEMPLATES, QUICK_START
from gui.icons import get_icon
from gui.theme import PALETTE
from data.circuit_library import CircuitLibrary

CIRCUIT_CLIPBOARD = "application/x-entrela-circuit-gates"

# Categories describe use, without altering the gate IDs saved in documents.
GATE_CATEGORIES = {
    "Básicas": ("h", "x", "y", "z", "sx", "id"),
    "Fases e rotações": ("s", "sdg", "t", "tdg", "rx", "ry", "rz", "p", "u"),
    "Controladas": ("cx", "cy", "cz", "ch", "ccx"),
    "Operações conjuntas": ("swap", "rxx", "ryy", "rzz"),
}


def _search_text(text):
    return "".join(char for char in unicodedata.normalize("NFD", text.casefold())
                   if not unicodedata.combining(char))


class GatePaletteButton(SecondaryButton):
    """Reserve enough space for the symbol and its readable name."""
    def sizeHint(self):
        self.ensurePolished()
        metrics = self.fontMetrics()
        lines = self.text().splitlines() or [""]
        return QSize(max(metrics.horizontalAdvance(line) for line in lines)+32,
                     len(lines)*metrics.lineSpacing()+16)

    def minimumSizeHint(self):
        return self.sizeHint()


class DocumentChange(QUndoCommand):
    def __init__(self, editor, before, after, title):
        super().__init__(title)
        self.editor = editor
        self.before = before
        self.after = after

    def redo(self):
        self.editor._set_document(self.after)

    def undo(self):
        self.editor._set_document(self.before)


def operation_records(document):
    return [
        dict(
            name=g.name,
            qubits=list(g.qubits),
            parameters=list(g.parameters),
            stage="evolution",
            step=i + 1,
        )
        for i, g in enumerate(document.gates)
    ]


class CircuitEditor(QWidget):
    run_requested = Signal(object)
    cancel_requested = Signal()
    draft_changed = Signal()
    document_replacing = Signal(object)
    recovery_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._palette_layout_timer = QTimer(self)
        self._palette_layout_timer.setSingleShot(True)
        self._palette_layout_timer.setInterval(0)
        self._palette_layout_timer.timeout.connect(self._resize_gate_palette)
        self.document = CircuitDocument()
        self.selected = -1
        self.selected_indices = []
        self.library = None
        self._library_id = None
        self._loaded_revision = None
        self._running = False
        self.undo_stack = QUndoStack(self)
        self._history_actions = []
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        introduction = QLabel("Adicione portas ou carregue um modelo para começar.")
        introduction.setWordWrap(True)
        introduction.setObjectName("FieldHint")
        introduction.hide()
        introduction.setParent(self)
        self.creation_help = CollapsibleSection("Como criar um circuito")
        self.creation_help.set_summary("")
        self.creation_help.layout().removeWidget(self.creation_help.header)
        self.creation_help.header.setParent(self)
        self.creation_help.header.setText("Como criar")
        self.creation_help.header.setToolTip("Como criar um circuito: passo a passo, controle e alvo, ângulos e leitura dos resultados.")
        help_text = QLabel(QUICK_START)
        help_text.setWordWrap(True)
        help_text.setTextFormat(Qt.PlainText)
        self.creation_help.content_layout.addWidget(help_text)
        templates = FlowLayout()
        self.template_selector = QComboBox()
        self.template_selector.setAccessibleName("Modelo pronto de circuito")
        self.template_selector.setMinimumContentsLength(18)
        self.template_selector.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLengthWithIcon)
        self.template_selector.addItem("Escolha um modelo…", None)
        for template in TEMPLATES:
            self.template_selector.addItem(template.title, template.key)
        templates.add_group(QLabel("Modelos prontos"), self.template_selector)
        self.use_template = SecondaryButton("Carregar modelo")
        self.use_template.setEnabled(False)
        self.use_template.setToolTip("Abre uma cópia editável. Você decide quando executar; a opção Desfazer recupera o circuito anterior.")
        self.use_template.clicked.connect(self._load_template)
        templates.addWidget(self.use_template)
        templates.addWidget(self.creation_help.header)
        root.addLayout(templates)
        root.addWidget(self.creation_help)
        self.creation_help.hide()
        self.creation_help.expanded_changed.connect(self.creation_help.setVisible)
        self.template_hint = QLabel()
        self.template_hint.setWordWrap(True)
        self.template_hint.setObjectName("FieldHint")
        self.template_hint.hide()
        root.addWidget(self.template_hint)
        self.template_selector.currentIndexChanged.connect(self._describe_template)
        toolbar = FlowLayout()
        self.qubits = QSpinBox()
        self.qubits.setRange(1, 6)
        self.qubits.setValue(2)
        self.qubits.setAccessibleName("Quantidade de qubits do editor")
        self.qubits.setToolTip("Quantidade de linhas do circuito. q0 é o primeiro qubit; a numeração começa em zero. Use de 1 a 6.")
        toolbar.add_group(QLabel("Qubits"), self.qubits)
        self.phase = QLineEdit("0")
        self.phase.setMaximumWidth(125)
        self.phase.setAccessibleName("Fase global em radianos")
        self.phase.setToolTip(PHASE_HELP)
        phase_button = SecondaryButton("Aplicar")
        phase_button.clicked.connect(self._apply_phase)
        phase_label = QLabel("Fase global (rad)")
        phase_label.setToolTip(PHASE_HELP)
        self.advanced_section = CollapsibleSection("Parâmetros avançados")
        phase_row = QHBoxLayout()
        phase_row.addWidget(phase_label)
        phase_row.addWidget(self.phase)
        phase_row.addWidget(phase_button)
        phase_row.addStretch()
        self.advanced_section.content_layout.addLayout(phase_row)
        phase_hint = QLabel(PHASE_HELP)
        phase_hint.setWordWrap(True)
        self.advanced_section.content_layout.addWidget(phase_hint)
        for title, key in [
            ("Desfazer", QKeySequence.Undo),
            ("Refazer", QKeySequence.Redo),
        ]:
            action = (
                self.undo_stack.createUndoAction(self, title)
                if title == "Desfazer"
                else self.undo_stack.createRedoAction(self, title)
            )
            action.setShortcut(key)
            action.setShortcutContext(Qt.WidgetWithChildrenShortcut)
            self.addAction(action)
            icon = "undo" if title == "Desfazer" else "redo"
            action.setIcon(get_icon(icon, color=PALETTE.text))
            self._history_actions.append((action, icon))
            button = QToolButton()
            button.setDefaultAction(action)
            button.setToolButtonStyle(Qt.ToolButtonIconOnly)
            button.setAccessibleName(title)
            toolbar.addWidget(button)
        files = toolbar
        self.file_menu = QToolButton()
        self.file_menu.setText("Arquivo e desenho")
        self.file_menu.setPopupMode(QToolButton.InstantPopup)
        self.file_menu.setAccessibleName("Operações de arquivo e visualização do circuito")
        file_menu = QMenu(self.file_menu)
        self.file_menu.setMenu(file_menu)
        self.zoom = QSpinBox()
        self.zoom.setRange(35, 250)
        self.zoom.setValue(100)
        self.zoom.setSuffix("%")
        self.zoom.setPrefix("Zoom ")
        self.zoom.valueChanged.connect(lambda value: self.canvas.set_zoom(value))
        for text, callback in [
            (
                "Novo",
                self._new,
            ),
            ("Abrir circuito…", self._import),
            ("Salvar circuito…", self._export),
            ("Exportar desenho…", self._export_svg),
            ("Ajustar visão", lambda: self.canvas.fit_circuit()),
        ]:
            button = GhostButton(text)
            button.clicked.connect(callback)
            if callback in (self._import, self._export):
                button.setToolTip("JSON guarda portas e parâmetros. OpenQASM é um formato de código para circuitos quânticos.")
            elif callback == self._export_svg:
                button.setToolTip("Exporta o trecho visível como imagem vetorial SVG, que pode ser ampliada sem perder nitidez.")
            button.hide()
            button.setParent(self)
            action = file_menu.addAction(text, button.click)
            action.setToolTip(button.toolTip())
        files.addWidget(self.file_menu)
        files.addWidget(self.zoom)
        self.advanced_section.layout().removeWidget(self.advanced_section.header)
        self.advanced_section.header.setParent(self)
        self.advanced_section.header.setText("Avançado")
        self.advanced_section.header.setToolTip("Fase global do circuito, em radianos. Não altera probabilidades de medição isoladamente.")
        files.addWidget(self.advanced_section.header)
        self.advanced_section.hide()
        self.advanced_section.expanded_changed.connect(self.advanced_section.setVisible)
        root.addLayout(files)
        root.addWidget(self.advanced_section)
        library_row = FlowLayout()
        self.circuit_name = QLineEdit()
        self.circuit_name.setObjectName("DocumentTitle")
        self.circuit_name.setMinimumWidth(360)
        self.circuit_name.setMaximumWidth(420)
        self.circuit_name.setMaxLength(120)
        self.circuit_name.setPlaceholderText("Nome do circuito")
        self.circuit_name.setAccessibleName("Nome do circuito na biblioteca")
        library_row.addWidget(self.circuit_name)
        self.save_revision_button = SecondaryButton("Salvar revisão")
        self.save_revision_button.clicked.connect(self._save_revision)
        self.save_revision_button.setEnabled(False)
        library_row.addWidget(self.save_revision_button)
        library_toggle = GhostButton("Biblioteca")
        library_toggle.setCheckable(True)
        library_row.addWidget(library_toggle)
        self.revision_label = QLabel("Rascunho independente")
        self.revision_label.setWordWrap(True)
        library_row.addWidget(self.revision_label)
        root.insertLayout(0, library_row)
        self.library_panel = QWidget()
        library_body = QFormLayout(self.library_panel)
        self.circuit_description = QLineEdit()
        self.circuit_description.setMaxLength(4000)
        self.circuit_description.setPlaceholderText("Objetivo ou descrição opcional")
        library_body.addRow("Descrição", self.circuit_description)
        self.library_combo = QComboBox()
        self.library_combo.setAccessibleName("Circuitos salvos")
        self.library_combo.currentIndexChanged.connect(self._library_selection_changed)
        self.revision_combo = QComboBox()
        self.revision_combo.setAccessibleName("Revisões do circuito")
        picker = QHBoxLayout()
        picker.addWidget(self.library_combo, 2)
        picker.addWidget(self.revision_combo, 1)
        open_revision = SecondaryButton("Abrir revisão")
        open_revision.clicked.connect(self._load_revision)
        picker.addWidget(open_revision)
        duplicate = GhostButton("Duplicar rascunho")
        duplicate.clicked.connect(self._duplicate)
        picker.addWidget(duplicate)
        library_body.addRow("Biblioteca", picker)
        self.recover_draft = SecondaryButton("Recuperar rascunho anterior…")
        self.recover_draft.setToolTip("Recupere até dez estados anteriores do editor, inclusive após fechar e reabrir o aplicativo.")
        self.recover_draft.setEnabled(False)
        self.recover_draft.clicked.connect(self.recovery_requested.emit)
        library_body.addRow("Recuperação local",self.recover_draft)
        root.addWidget(self.library_panel)
        self.library_panel.hide()
        library_toggle.toggled.connect(self.library_panel.setVisible)
        self.summary = QLabel()
        self.summary.setWordWrap(True)
        self.summary.setObjectName("SectionSubtitle")
        root.addWidget(self.summary)
        self.scene_splitter = QSplitter(Qt.Horizontal)
        self.scene_splitter.setHandleWidth(3)
        self.scene_splitter.setChildrenCollapsible(False)
        palette = QWidget()
        palette_body = QGridLayout(palette)
        palette_body.setContentsMargins(4, 4, 4, 4)
        palette_body.setHorizontalSpacing(6)
        palette_body.setAlignment(Qt.AlignTop)
        self.palette_grid = palette_body
        self.palette_buttons = {}
        for i, name in enumerate(GATES):
            symbol, title = GATE_NAMES[name]
            button = GatePaletteButton(symbol + "\n" + fill(title, width=12))
            button.setAccessibleName(f"Adicionar {symbol}: {title}")
            button.setToolTip(GATE_HELP[name] + "\nAdicionar após a seleção.")
            button.clicked.connect(lambda _, n=name: self._add(n))
            palette_body.addWidget(button, i // 2, i % 2)
            self.palette_buttons[name] = button
        palette_panel = QWidget()
        palette_layout = QVBoxLayout(palette_panel)
        palette_layout.setContentsMargins(0, 0, 0, 0)
        palette_layout.setSpacing(6)
        self.gate_search = QLineEdit()
        self.gate_search.setPlaceholderText("Buscar porta…")
        self.gate_search.setAccessibleName("Buscar portas por nome ou símbolo")
        self.gate_search.setClearButtonEnabled(True)
        self.gate_search.setToolTip("Busque pelo nome ou símbolo, como Hadamard, rotação ou CX.")
        palette_layout.addWidget(self.gate_search)
        self.gate_category = QComboBox()
        self.gate_category.setAccessibleName("Categoria de portas")
        self.gate_category.addItem("Todas as portas", None)
        for category in GATE_CATEGORIES:
            self.gate_category.addItem(category, category)
        self.gate_category.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLengthWithIcon)
        self.gate_category.setMinimumContentsLength(8)
        palette_layout.addWidget(self.gate_category)
        self.palette_empty = QLabel("Nenhuma porta encontrada.")
        self.palette_empty.setWordWrap(True)
        self.palette_empty.hide()
        palette_layout.addWidget(self.palette_empty)
        palette_scroll = QScrollArea()
        palette_scroll.setWidgetResizable(True)
        palette_scroll.setWidget(palette)
        palette_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.palette_scroll = palette_scroll
        self.palette_scroll.viewport().installEventFilter(self)
        self.palette_panel = palette_panel
        palette_layout.addWidget(palette_scroll, 1)
        self._palette_columns = 2
        self._visible_gates = list(GATES)
        self.gate_search.textChanged.connect(self._filter_gate_palette)
        self.gate_category.currentIndexChanged.connect(self._filter_gate_palette)
        root.removeItem(templates)
        for item in list(templates.items):
            if item.widget(): item.widget().hide()
        palette_layout.insertWidget(0, self.template_selector)
        palette_layout.insertWidget(1, self.use_template)
        root.removeWidget(self.template_hint)
        palette_layout.insertWidget(2, self.template_hint)
        self.template_selector.show()
        self.use_template.show()
        self.creation_help.header.setParent(self)
        self.creation_help.header.show()
        files.addWidget(self.creation_help.header)
        palette_panel.setMinimumWidth(180)
        palette_panel.setMaximumWidth(270)
        self.scene_splitter.addWidget(palette_panel)
        self.canvas = CircuitCanvas(editable=True)
        self.canvas.setMinimumWidth(220)
        self.canvas.zoom_changed.connect(self._sync_zoom)
        self.operation_views = QTabWidget()
        self.operation_views.setDocumentMode(True)
        self.operation_views.addTab(self.canvas, "Desenho")
        operations_panel = QWidget()
        operations_layout = QVBoxLayout(operations_panel)
        operations_layout.setContentsMargins(6, 6, 6, 6)
        operations_hint = QLabel("Selecione uma operação para editar. Use as setas; Shift ou Ctrl selecionam várias portas.")
        operations_hint.setWordWrap(True)
        operations_hint.setObjectName("FieldHint")
        operations_layout.addWidget(operations_hint)
        self.operations_list = QListWidget()
        self.operations_list.setAccessibleName("Operações do circuito em ordem de execução")
        self.operations_list.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.operations_list.setWordWrap(True)
        self.operations_list.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        operations_layout.addWidget(self.operations_list, 1)
        self.operation_views.addTab(operations_panel, "Operações")
        self.scene_splitter.addWidget(self.operation_views)
        self.operations_list.itemSelectionChanged.connect(self._select_from_list)
        self.canvas.operations_selected.connect(self._select_many)
        # A scene must not be cleared while Qt is dispatching a gate's release event.
        self.canvas.move_requested.connect(self._reorder, Qt.QueuedConnection)
        inspector = QWidget()
        form_body = QVBoxLayout(inspector)
        self.selection_label = QLabel("Adicione uma porta ou selecione no desenho.")
        self.selection_label.setWordWrap(True)
        form_body.addWidget(self.selection_label)
        self.gate_help = QLabel()
        self.gate_help.setWordWrap(True)
        form_body.addWidget(self.gate_help)
        self.gate_dependencies = QLabel()
        self.gate_dependencies.setWordWrap(True)
        self.gate_dependencies.setObjectName("SectionSubtitle")
        form_body.addWidget(self.gate_dependencies)
        matrix_section = CollapsibleSection("Matriz da porta")
        matrix_section.set_summary("")
        matrix_section.header.setToolTip("Inspeção matemática opcional da porta selecionada.")
        matrix_note = QLabel("A matriz descreve matematicamente a operação. Você não precisa preenchê-la para criar o circuito.")
        matrix_note.setWordWrap(True)
        matrix_note.setObjectName("FieldHint")
        matrix_section.content_layout.addWidget(matrix_note)
        self.gate_matrix = QPlainTextEdit()
        self.gate_matrix.setReadOnly(True)
        self.gate_matrix.setMaximumHeight(145)
        self.gate_matrix.setAccessibleName("Matriz unitária da porta selecionada")
        self.gate_matrix.setToolTip("Matriz numérica do Qiskit. A base local é |q[k−1]…q[0]⟩, pela ordem das conexões da porta.")
        matrix_section.content_layout.addWidget(self.gate_matrix)
        form_body.addWidget(matrix_section)
        form = QFormLayout()
        form.setRowWrapPolicy(QFormLayout.WrapLongRows)
        self.gate_type = QComboBox()
        self.gate_type.addItems(list(GATES))
        self.gate_type.setToolTip("Código da porta usada no desenho. A explicação acima mostra seu nome e efeito.")
        form.addRow("Porta no desenho", self.gate_type)
        self.qubit_fields = []
        self.param_fields = []
        for i in range(3):
            spin = QSpinBox()
            spin.setRange(0, 1)
            spin.setPrefix("q")
            spin.setAccessibleName(f"Conexão {i + 1} da porta")
            self.qubit_fields.append(spin)
            form.addRow(f"Qubit {i + 1}", spin)
        for name in ("Ângulo θ (rad)", "Fase φ (rad)", "Fase λ (rad)"):
            field = QLineEdit("0")
            field.setPlaceholderText("pi/2")
            field.setAccessibleName(name)
            field.setToolTip(ANGLE_HELP)
            self.param_fields.append(field)
            form.addRow(name, field)
        self.gate_form = form
        form_body.addLayout(form)
        apply = SecondaryButton("Aplicar alterações")
        apply.setToolTip("Atualiza a porta selecionada com os qubits e ângulos dos campos.")
        apply.clicked.connect(self._apply_gate)
        form_body.addWidget(apply)
        for text, callback in [
            ("Remover seleção", self._remove),
            ("Copiar seleção", self._copy_selected),
            ("Colar portas", self._paste_gates),
            ("Mover antes", lambda: self._reorder(self.selected, self.selected - 1)),
            ("Mover depois", lambda: self._reorder(self.selected, self.selected + 1)),
        ]:
            button = SecondaryButton(text)
            button.clicked.connect(callback)
            form_body.addWidget(button)
        note = QLabel("q0 é o primeiro qubit. Use qubits diferentes em portas controladas.\n" + ANGLE_HELP)
        note.setWordWrap(True)
        form_body.addWidget(note)
        noise_toggle = QToolButton()
        noise_toggle.setText("Mais opções de ruído")
        noise_toggle.setCheckable(True)
        advanced = QWidget()
        advanced_layout = QVBoxLayout(advanced)
        thermal_help = QLabel("T₁ descreve o relaxamento das populações; T₂, a perda de coerência. Ambos são medidos em microssegundos (µs), com T₂ ≤ 2T₁. Durações de porta usam nanossegundos (ns).")
        thermal_help.setWordWrap(True)
        thermal_help.setObjectName("FieldHint")
        advanced_layout.addWidget(thermal_help)
        advanced_form = QFormLayout()
        advanced_form.setRowWrapPolicy(QFormLayout.WrapLongRows)
        advanced_layout.addLayout(advanced_form)
        self.noise_kind = QComboBox()
        self.noise_kind.addItem("Despolarizador", "Despolarizador")
        self.noise_kind.addItem("Térmico (T₁/T₂)", "Termico")
        self.t1 = ScientificSpinBox()
        self.t2 = ScientificSpinBox()
        for field, value in ((self.t1, 50.0), (self.t2, 30.0)):
            field.setRange(0.001, 1e6)
            field.setValue(value)
        advanced_form.addRow("Modelo", self.noise_kind)
        advanced_form.addRow("T₁ (µs)", self.t1)
        advanced_form.addRow("T₂ (µs)", self.t2)
        self.gate1 = ScientificSpinBox()
        self.gate2 = ScientificSpinBox()
        for field in (self.gate1,self.gate2):
            field.setRange(0.001,1e6)
            field.setValue(50.0)
            field.setToolTip("Hipótese de exposição ao canal térmico por porta nativa; não é duração física total do algoritmo.")
        advanced_form.addRow("Porta 1q (ns)",self.gate1)
        advanced_form.addRow("Porta 2q (ns)",self.gate2)
        form_body.addWidget(noise_toggle)
        form_body.addWidget(advanced)
        advanced.hide()
        noise_toggle.toggled.connect(advanced.setVisible)
        form_body.addStretch()
        inspector_scroll = QScrollArea()
        inspector_scroll.setWidgetResizable(True)
        inspector_scroll.setWidget(inspector)
        inspector_scroll.setMinimumWidth(235)
        inspector_scroll.setMaximumWidth(280)
        inspector_scroll.setMaximumWidth(16777215)
        inspector_scroll.setFrameShape(QFrame.NoFrame)
        self.inspector_tabs = QTabWidget()
        self.inspector_tabs.setDocumentMode(True)
        self.inspector_tabs.setMinimumWidth(260)
        self.inspector_tabs.setMaximumWidth(370)
        self.inspector_tabs.addTab(inspector_scroll, "Porta")
        self.scene_splitter.addWidget(self.inspector_tabs)
        self.scene_splitter.setStretchFactor(1, 1)
        self.scene_splitter.setSizes([220, 800, 300])
        self.inspector_toggle = QToolButton()
        self.inspector_toggle.setText("Inspetor")
        self.inspector_toggle.setCheckable(True)
        self.inspector_toggle.setChecked(True)
        self.inspector_toggle.setAccessibleName("Mostrar inspetor do circuito")
        self.inspector_toggle.clicked.connect(self._toggle_inspector)
        files.addWidget(self.inspector_toggle)
        root.addWidget(self.scene_splitter, 1)
        self._compact_scene = False
        self._inspector_wide_visible = True
        self.scene_compact_tabs = ContentTabs()
        self.scene_compact_tabs.setDocumentMode(True)
        self.scene_compact_tabs.setAccessibleName("Portas, circuito ou inspetor")
        self.scene_compact_tabs.currentChanged.connect(lambda *_: self._palette_layout_timer.start())
        self.scene_compact_tabs.hide()
        root.addWidget(self.scene_compact_tabs, 1)
        execution_options = QWidget()
        options_layout = QVBoxLayout(execution_options)
        options_layout.setContentsMargins(12, 12, 12, 12)
        settings = QFormLayout()
        settings.setRowWrapPolicy(QFormLayout.WrapAllRows)
        options_layout.addLayout(settings)
        self.shots = QSpinBox()
        self.shots.setRange(1, 1_000_000)
        self.shots.setValue(1024)
        self.shots.setAccessibleName("Número de medições do circuito (shots)")
        self.shots.setToolTip("Quantidade de repetições: preparar e medir o circuito. Mais medições reduzem flutuações de contagem, mas não removem o ruído.")
        self.seed = QLineEdit("42")
        self.seed.setMaximumWidth(110)
        self.seed.setPlaceholderText("Automática")
        self.seed.setToolTip("Número inteiro que controla a amostragem. Exemplo: 42. Deixe vazio para gerar e registrar uma semente automaticamente.")
        self.noise = QCheckBox("Ativar ruído")
        self.p1 = ScientificSpinBox()
        self.p2 = ScientificSpinBox()
        for w, value in [(self.p1, 0.01), (self.p2, 0.05)]:
            w.setRange(0, 1)
            w.setValue(value)
            w.setMaximumWidth(100)
        self.p1.setToolTip("Parâmetro p₁ de despolarização aplicado por porta de um qubit, entre 0 e 1. Zero desativa esse canal.")
        self.p2.setToolTip("Parâmetro p₂ de despolarização aplicado por porta de dois qubits, entre 0 e 1. Zero desativa esse canal.")
        for text, widget in [
            ("Medições (shots)", self.shots),
            ("Semente", self.seed),
            ("Ruído em 1 qubit (p₁)", self.p1),
            ("Ruído em 2 qubits (p₂)", self.p2),
        ]:
            label = QLabel(text)
            label.setToolTip(widget.toolTip())
            label.setBuddy(widget)
            settings.addRow(label, widget)
        options_layout.addWidget(self.noise)
        form_body.removeWidget(noise_toggle)
        form_body.removeWidget(advanced)
        options_layout.addWidget(noise_toggle)
        options_layout.addWidget(advanced)
        options_layout.addStretch()
        execution_scroll = QScrollArea()
        execution_scroll.setFrameShape(QFrame.NoFrame)
        execution_scroll.setWidgetResizable(True)
        execution_scroll.setWidget(execution_options)
        self.inspector_tabs.addTab(execution_scroll, "Execução")
        self.message = QLabel(
            "Até 200 portas · Ctrl+clique seleciona várias · Ctrl+C/V copia e cola · arraste para reordenar."
        )
        self.message.setWordWrap(True)
        self.message.setTextFormat(Qt.PlainText)
        root.addWidget(self.message)
        # CircuitPage can host this bar outside its page scroll. Keep the same
        # run button and signal when this editor is used on its own.
        self.execution_bar = QFrame()
        self.execution_bar.setObjectName("ExecutionBar")
        execution = QHBoxLayout(self.execution_bar)
        execution.setContentsMargins(20, 10, 20, 12)
        execution.setSpacing(12)
        self.execution_status = QLabel("Pronto para executar · medição final na base Z.")
        self.execution_status.setObjectName("FieldHint")
        self.execution_status.setWordWrap(True)
        execution.addWidget(self.execution_status, 1)
        self.cancel = SecondaryButton("Cancelar", icon="stop")
        self.cancel.setEnabled(False)
        self.cancel.setAccessibleName("Cancelar execução do circuito")
        self.cancel.clicked.connect(self.cancel_requested.emit)
        execution.addWidget(self.cancel)
        self.run = PrimaryButton("Executar circuito", icon="play")
        self.run.setAccessibleName("Executar circuito")
        self.run.clicked.connect(self._run)
        execution.addWidget(self.run)
        root.addWidget(self.execution_bar)
        self.gate_type.currentTextChanged.connect(self._show_fields)
        self.qubits.valueChanged.connect(self._change_qubits)
        self.noise.toggled.connect(self._update_noise_fields)
        self.noise_kind.currentIndexChanged.connect(self._update_noise_fields)
        self._update_noise_fields()
        for title, sequence, callback in (
            ("Copiar portas", QKeySequence.Copy, self._copy_selected),
            ("Colar portas", QKeySequence.Paste, self._paste_gates),
            ("Recortar portas", QKeySequence.Cut, self._cut_selected),
            ("Selecionar todas as portas", QKeySequence.SelectAll, self._select_all),
            ("Remover portas", QKeySequence.Delete, self._remove),
        ):
            for target in (self.canvas, self.operations_list):
                action = QAction(title, target)
                action.setShortcut(sequence)
                action.setShortcutContext(Qt.WidgetWithChildrenShortcut)
                action.triggered.connect(callback)
                target.addAction(action)
        self._set_document(self.document)
        for widget in (self.circuit_name, self.circuit_description, self.phase, self.seed, *self.param_fields):
            widget.textChanged.connect(lambda *_: self.draft_changed.emit())
        for widget in (self.shots, self.p1, self.p2, self.t1, self.t2, self.gate1,self.gate2, *self.qubit_fields):
            widget.valueChanged.connect(lambda *_: self.draft_changed.emit())
        self.noise.toggled.connect(lambda *_: self.draft_changed.emit())
        self.noise_kind.currentIndexChanged.connect(lambda *_: self.draft_changed.emit())
        self.gate_type.currentIndexChanged.connect(lambda *_: self.draft_changed.emit())

    def draft_state(self):
        return dict(document=self.document.to_dict(), name=self.circuit_name.text(),
                    description=self.circuit_description.text(), phase=self.phase.text(),
                    library_id=self._library_id, revision=self._loaded_revision,
                    selected=self.selected, gate_type=self.gate_type.currentText(),
                    parameters=[field.text() for field in self.param_fields],
                    connections=[field.value() for field in self.qubit_fields],
                    seed=self.seed.text(), shots=self.shots.value(), noise=self.noise.isChecked(),
                    noise_kind=self.noise_kind.currentData(),
                    **{key:getattr(self,key).value() for key in ("p1", "p2", "t1", "t2", "gate1", "gate2")})

    def _describe_template(self):
        key = self.template_selector.currentData()
        template = next((item for item in TEMPLATES if item.key == key), None)
        self.use_template.setEnabled(template is not None and not self._running)
        self.template_hint.setVisible(template is not None)
        if template:
            self.template_hint.setText(template.instruction + " " + template.prediction +
                                       " Previsão analítica sem ruído; contagens finitas podem variar. Carregar não executa.")

    def _load_template(self):
        if self._running:
            return
        template = next((item for item in TEMPLATES if item.key == self.template_selector.currentData()), None)
        if template is None:
            return
        if self.document.gates and self.document != template.document:
            answer = QMessageBox.question(self, "Carregar modelo de circuito?",
                "O modelo substituirá as portas em edição. Você pode recuperar o circuito anterior com Desfazer. Deseja continuar?",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if answer != QMessageBox.Yes:
                return
        self.replace_document(template.document, "Carregar modelo: " + template.title)
        if not self.circuit_name.text().strip():
            self.circuit_name.setText(template.title)
        if not self.circuit_description.text().strip():
            self.circuit_description.setText(template.instruction + " Previsão analítica ideal: " + template.prediction)
        self.message.setText("Modelo carregado para edição. Escolha as medições e o ruído e clique em Executar circuito para gerar resultados.")

    def restore_draft(self, state):
        document = CircuitDocument.from_dict(state["document"])
        self._set_document(document)
        self.undo_stack.clear()
        self._library_id = state.get("library_id")
        self._loaded_revision = state.get("revision")
        self.circuit_name.setText(state.get("name", ""))
        self.circuit_description.setText(state.get("description", ""))
        self._select(state.get("selected", -1))
        self.gate_type.setCurrentText(state.get("gate_type", "h"))
        for field, value in zip(self.param_fields, state.get("parameters", [])):
            field.setText(value)
        for field, value in zip(self.qubit_fields, state.get("connections", [])):
            field.setValue(value)
        self.phase.setText(state.get("phase", repr(document.global_phase)))
        self.seed.setText(state.get("seed", "42"))
        self.shots.setValue(state.get("shots", 1024))
        self.noise.setChecked(state.get("noise", False))
        self.noise_kind.setCurrentIndex(max(0,self.noise_kind.findData(state.get("noise_kind", "Despolarizador"))))
        for key in ("p1", "p2", "t1", "t2", "gate1", "gate2"):
            if key in state:
                getattr(self,key).setValue(state[key])
        self.revision_label.setText("Rascunho recuperado")
        self.revision_label.setToolTip("Recuperação automática. Salve uma revisão para preservar esta versão na biblioteca.")
        self.draft_changed.emit()
        self._palette_layout_timer.start()

    def _resize_gate_palette(self):
        """Reserve actual styled button widths instead of clipping two columns."""
        if not hasattr(self, "palette_scroll"):
            return
        compact = getattr(self, '_compact_scene', False)
        scale = max(1, self.font().pixelSize() / 15)
        if compact:
            # Na aba Portas, a paleta utiliza toda a largura disponível.
            for widget in (self.palette_panel, self.palette_scroll):
                widget.setMinimumWidth(180)
                widget.setMaximumWidth(16777215)
            minimum = max(button.minimumSizeHint().width() for button in self.palette_buttons.values())
            columns = 2 if self.palette_scroll.viewport().width() >= 2 * minimum + 16 else 1
        else:
            columns = 1 if self.width() < 1000 * scale else 2
        if columns != self._palette_columns:
            self._palette_columns = columns
            self._layout_gate_palette()
        widths = [0] * columns
        for index, button in enumerate(self.palette_buttons.values()):
            button.ensurePolished()
            button.setMinimumHeight(button.sizeHint().height())
            widths[index % columns] = max(widths[index % columns], button.minimumSizeHint().width())
        if compact:
            return
        margins = self.palette_grid.contentsMargins()
        width = (sum(widths) + max(0, columns - 1) * self.palette_grid.horizontalSpacing()
                 + margins.left() + margins.right()
                 + self.palette_scroll.verticalScrollBar().sizeHint().width()
                 + 2 * self.palette_scroll.frameWidth() + 2)
        if self.palette_scroll.width() != width:
            self.palette_scroll.setFixedWidth(width)
            self.palette_panel.setFixedWidth(width)

    def _layout_gate_palette(self):
        for name, button in self.palette_buttons.items():
            self.palette_grid.removeWidget(button)
            button.setVisible(name in self._visible_gates)
        for index, name in enumerate(self._visible_gates):
            self.palette_grid.addWidget(self.palette_buttons[name],
                                        index // self._palette_columns, index % self._palette_columns)
        self.palette_empty.setVisible(not self._visible_gates)

    def _filter_gate_palette(self, *_):
        query = _search_text(self.gate_search.text().strip())
        category = self.gate_category.currentData()
        allowed = GATE_CATEGORIES[category] if category else GATES
        self._visible_gates = [name for name in GATES if name in allowed
                               and query in _search_text(" ".join((name, *GATE_NAMES[name], GATE_HELP[name])))]
        self._layout_gate_palette()
        self.palette_scroll.verticalScrollBar().setValue(0)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._resize_gate_palette()
        self._arrange_scene()

    def eventFilter(self, watched, event):
        if hasattr(self, 'palette_scroll') and watched is self.palette_scroll.viewport() and event.type() == QEvent.Resize:
            self._palette_layout_timer.start()
        return super().eventFilter(watched, event)

    def changeEvent(self, event):
        super().changeEvent(event)
        if event.type() in (QEvent.FontChange, QEvent.StyleChange) and hasattr(self, "_palette_layout_timer"):
            self._palette_layout_timer.start()
            self._arrange_scene()

    def _toggle_inspector(self, visible):
        if self._compact_scene:
            self.scene_compact_tabs.setCurrentWidget(self.inspector_tabs)
        else:
            self.inspector_tabs.setVisible(visible)

    def _arrange_scene(self):
        if not hasattr(self, 'scene_compact_tabs'):
            return
        compact = self.width() < 1100 * max(1, self.font().pixelSize() / 15)
        if compact == self._compact_scene:
            return
        self._compact_scene = compact
        if compact:
            self._inspector_wide_visible = self.inspector_toggle.isChecked()
            self.inspector_toggle.setCheckable(False)
            self.scene_splitter.hide()
            self.palette_panel.setMaximumWidth(16777215)
            self.inspector_tabs.setMaximumWidth(16777215)
            for widget, title in ((self.palette_panel, 'Portas'), (self.operation_views, 'Circuito'),
                                  (self.inspector_tabs, 'Inspetor')):
                self.scene_compact_tabs.addTab(widget, title)
            self.scene_compact_tabs.setCurrentIndex(1)
            self.scene_compact_tabs.show()
        else:
            while self.scene_compact_tabs.count():
                self.scene_compact_tabs.removeTab(0)
            self.scene_compact_tabs.hide()
            for widget in (self.palette_panel, self.operation_views, self.inspector_tabs):
                self.scene_splitter.addWidget(widget)
            self.palette_panel.setMaximumWidth(270)
            self.inspector_tabs.setMaximumWidth(370)
            self.palette_panel.show()
            self.operation_views.show()
            self.inspector_toggle.setCheckable(True)
            self.inspector_toggle.setChecked(self._inspector_wide_visible)
            self.inspector_tabs.setVisible(self._inspector_wide_visible)
            self.scene_splitter.setSizes([220, 800, 300])
            self.scene_splitter.show()
        self._palette_layout_timer.start()

    def set_storage_directory(self, path):
        """Keep reusable circuit revisions separate from immutable run records."""
        try:
            self.library = CircuitLibrary(path)
            self.save_revision_button.setEnabled(True)
            self._refresh_circuit_library()
        except OSError as exc:
            self.library = None
            self.save_revision_button.setEnabled(False)
            self.message.setText("Biblioteca indisponível: " + str(exc))

    def _refresh_circuit_library(self):
        if self.library is None:
            return
        blocker = QSignalBlocker(self.library_combo)
        self.library_combo.clear()
        for revision in self.library.entries():
            self.library_combo.addItem(revision.name, revision.identifier)
        selected = self.library_combo.findData(self._library_id)
        self.library_combo.setCurrentIndex(max(0, selected))
        del blocker
        self._library_selection_changed()

    def _library_selection_changed(self, *_):
        self.revision_combo.clear()
        identifier = self.library_combo.currentData()
        if self.library is None or identifier is None:
            return
        try:
            for revision in reversed(self.library.revisions(identifier)):
                self.revision_combo.addItem(
                    f"Revisão {revision.version} · {revision.created_at[:10]}",
                    revision.version,
                )
        except (OSError, ValueError, TypeError, KeyError) as exc:
            self.message.setText("Não foi possível ler o circuito: " + str(exc))

    def _save_revision(self):
        if self.library is None:
            self.message.setText("A biblioteca de circuitos está indisponível.")
            return
        try:
            # Invalid text must never silently save the previous phase.
            document = replace(self.document, global_phase=parse_angle(self.phase.text()))
            document.validate()
            revision = self.library.save(
                self.circuit_name.text(), document,
                self.circuit_description.text(), self._library_id,
            )
            self._library_id = revision.identifier
            self._loaded_revision = revision.version
            self.replace_document(document, "Aplicar fase para salvar")
            self.revision_label.setText(f"Revisão {revision.version} salva")
            self._refresh_circuit_library()
            self.message.setText("Circuito salvo. As revisões anteriores permanecem disponíveis.")
            self.draft_changed.emit()
        except (OSError, ValueError, TypeError, KeyError) as exc:
            self.message.setText("Não foi possível salvar: " + str(exc))

    def _load_revision(self):
        identifier = self.library_combo.currentData()
        version = self.revision_combo.currentData()
        if self.library is None or identifier is None or version is None:
            return
        try:
            revision = next(item for item in self.library.revisions(identifier) if item.version == version)
            self.replace_document(revision.document, "Abrir revisão de circuito")
            self._library_id, self._loaded_revision = identifier, version
            self.circuit_name.setText(revision.name)
            self.circuit_description.setText(revision.description)
            self.revision_label.setText(f"Revisão {version} aberta")
            self.message.setText("Revisão recuperada. Salvar cria uma nova revisão, sem substituir a anterior.")
            self.draft_changed.emit()
        except (OSError, ValueError, TypeError, KeyError, StopIteration) as exc:
            self.message.setText("Não foi possível abrir a revisão: " + str(exc))

    def _new(self):
        self.document_replacing.emit(self.draft_state())
        self.replace_document(CircuitDocument(self.document.num_qubits), "Novo circuito")
        self._library_id = self._loaded_revision = None
        self.circuit_name.clear()
        self.circuit_description.clear()
        self.revision_label.setText("Rascunho independente")
        self.draft_changed.emit()

    def _duplicate(self):
        self.document_replacing.emit(self.draft_state())
        self._library_id = self._loaded_revision = None
        name = self.circuit_name.text().strip()
        self.circuit_name.setText((name + " · cópia")[:120] if name else "Cópia do circuito")
        self.revision_label.setText("Cópia independente · ainda não salva")
        self.message.setText("O próximo salvamento cria um circuito independente.")
        self.draft_changed.emit()

    def revision_context(self):
        """Optional provenance for a run; the circuit itself remains in config."""
        if self._library_id is None or self.library is None:
            return {"name": self.circuit_name.text().strip(), "saved_revision": None}
        try:
            revision = next(item for item in self.library.revisions(self._library_id)
                            if item.version == self._loaded_revision)
        except (OSError, ValueError, TypeError, KeyError, StopIteration):
            return {"name": self.circuit_name.text().strip(), "saved_revision": None}
        return {"name": self.circuit_name.text().strip(), "library_id": self._library_id,
                "saved_revision": revision.version, "modified_since_revision": revision.document != self.document}

    def replace_document(self, document, title="Carregar circuito"):
        try:
            document.validate()
            if document != self.document:
                self.document_replacing.emit(self.draft_state())
                self.undo_stack.push(
                    DocumentChange(self, self.document, document, title)
                )
        except ValueError as exc:
            self.selected = min(self.selected, len(self.document.gates) - 1)
            self.message.setText(str(exc))

    def _set_document(self, document):
        self.document = document
        self.selected = min(self.selected, len(document.gates) - 1)
        blockers = [QSignalBlocker(self.qubits), QSignalBlocker(self.phase)]
        self.qubits.setValue(document.num_qubits)
        self.phase.setText(repr(float(document.global_phase)))
        self.phase.setCursorPosition(0)
        self.phase.setToolTip(PHASE_HELP + " Valor atual: " + repr(float(document.global_phase)) + " rad.")
        del blockers
        for field in self.qubit_fields:
            field.setRange(0, document.num_qubits - 1)
        for name, button in self.palette_buttons.items():
            button.setEnabled(GATES[name][1] <= document.num_qubits)
        self.canvas.description = f"Fase global: {document.global_phase!r} rad; {document.num_qubits} qubits; medição final na base Z."
        self.canvas.set_operations(operation_records(document), document.num_qubits)
        blocker = QSignalBlocker(self.operations_list)
        self.operations_list.clear()
        for index, gate in enumerate(document.gates):
            symbol, title = GATE_NAMES[gate.name]
            connections = ", ".join(f"q{qubit}" for qubit in gate.qubits)
            parameters = ", ".join(repr(float(value)) for value in gate.parameters)
            text = f"{index + 1}. {symbol} · {title}\nQubits: {connections}"
            if parameters:
                text += " · ângulos (rad): " + parameters
            item = QListWidgetItem(text)
            item.setData(Qt.UserRole, index)
            item.setToolTip(text + "\n" + GATE_HELP[gate.name])
            self.operations_list.addItem(item)
        del blocker
        circuit = document.to_quantum_circuit()
        counts = " · ".join(f"{name.upper()} {count}" for name, count in sorted(circuit.count_ops().items()))
        self.summary.setText(f"{document.num_qubits} qubits · {len(document.gates)} portas · profundidade lógica {circuit.depth()}"
                             + (" · " + counts if counts else " · estado inicial |0…0⟩"))
        self._select(self.selected)
        self.draft_changed.emit()

    def _select_many(self, indexes):
        self.selected_indices = sorted(i for i in indexes if 0 <= i < len(self.document.gates))
        self._select(self.selected_indices[-1] if self.selected_indices else -1, sync_canvas=False)

    def _select_from_list(self):
        indexes = sorted(item.data(Qt.UserRole) for item in self.operations_list.selectedItems())
        self.canvas.select_operations(indexes)
        self._select_many(indexes)

    def _sync_operation_list(self):
        blocker = QSignalBlocker(self.operations_list)
        selected = set(self.selected_indices)
        for index in range(self.operations_list.count()):
            self.operations_list.item(index).setSelected(index in selected)
        if self.selected >= 0:
            item = self.operations_list.item(self.selected)
            if not self.operations_list.hasFocus():
                self.operations_list.setCurrentRow(self.selected, QItemSelectionModel.NoUpdate)
            self.operations_list.scrollToItem(item)
        del blocker

    def _select(self, index, sync_canvas=True):
        self.selected = index if 0 <= index < len(self.document.gates) else -1
        if sync_canvas:
            self.selected_indices = [self.selected] if self.selected >= 0 else []
            self.canvas.select_operations(self.selected_indices)
        self._sync_operation_list()
        if self.selected < 0:
            self.selection_label.setText("Adicione uma porta pela paleta.")
            self.gate_matrix.clear()
            self.gate_dependencies.clear()
            self._show_fields()
            return
        gate = self.document.gates[self.selected]
        self.selection_label.setText(
            f"Porta {self.selected + 1} de {len(self.document.gates)} · {gate.name.upper()}"
            + (f" · {len(self.selected_indices)} selecionadas" if len(self.selected_indices) > 1 else "")
        )
        self.gate_type.setCurrentText(gate.name)
        for i, value in enumerate(gate.qubits):
            self.qubit_fields[i].setValue(value)
        for i, value in enumerate(gate.parameters):
            # Compact drawing labels must never round editable scientific values.
            self.param_fields[i].setText(repr(float(value)))
        self._show_matrix(gate)
        self._show_fields()

    def _show_matrix(self, gate):
        import numpy as np
        matrix = GATES[gate.name][0](*gate.parameters).to_matrix()
        text = np.array2string(matrix, precision=6, suppress_small=True, max_line_width=110)
        previous = {}
        for index, operation in enumerate(self.document.gates[:self.selected]):
            for qubit in operation.qubits:
                previous[qubit] = index + 1
        predecessors = sorted({previous[q] for q in gate.qubits if q in previous})
        self.gate_dependencies.setText("Depende das portas " + ", ".join(map(str, predecessors))
                                       if predecessors else "Sem operação anterior nos qubits envolvidos.")
        self.gate_matrix.setPlainText("U · base local |q[k−1]…q[0]⟩\n" + text)
        self.gate_matrix.setToolTip("Matriz numérica para inspeção (6 casas; cálculo preserva precisão integral).\n"
                                   + ("Dependências por qubit: portas " + ", ".join(map(str, predecessors))
                                      if predecessors else "Sem porta anterior nos qubits envolvidos."))

    def _show_fields(self, *_):
        name = self.gate_type.currentText()
        _, arity, nparams = GATES[name]
        symbol, title = GATE_NAMES[name]
        explanation = GATE_HELP[name]
        self.gate_help.setText(f"{symbol} — " + (explanation if explanation.startswith(title) else title + ". " + explanation))
        for i, w in enumerate(self.qubit_fields):
            self.gate_form.setRowVisible(w, i < arity)
            label = (
                ("Qubit alvo" if i == arity - 1 else "Qubit de controle " + str(i + 1))
                if name in ("cx", "cy", "cz", "ch", "ccx")
                else "Qubit " + str(i + 1)
            )
            self.gate_form.labelForField(w).setText(label)
            w.setAccessibleName(label)
            w.setToolTip("Escolha a linha do circuito, de q0 a q" + str(self.document.num_qubits-1) +
                         ". Em portas controladas, controle e alvo devem ser qubits diferentes.")
        for i, w in enumerate(self.param_fields):
            self.gate_form.setRowVisible(w, i < nparams)

    def _add(self, name):
        _, arity, nparams = GATES[name]
        gate = CircuitGate(name, tuple(range(arity)), tuple([math.pi / 2] * nparams))
        index = self.selected + 1 if self.selected >= 0 else len(self.document.gates)
        gates = list(self.document.gates)
        gates.insert(index, gate)
        self.selected = index
        self.replace_document(
            replace(self.document, gates=tuple(gates)), "Adicionar " + name.upper()
        )

    def _apply_gate(self):
        if self.selected < 0:
            self.message.setText("Selecione uma porta para aplicar as alterações.")
            return
        try:
            name = self.gate_type.currentText()
            _, arity, nparams = GATES[name]
            gate = CircuitGate(
                name,
                tuple(w.value() for w in self.qubit_fields[:arity]),
                tuple(parse_angle(w.text()) for w in self.param_fields[:nparams]),
            )
            gates = list(self.document.gates)
            gates[self.selected] = gate
            self.replace_document(
                replace(self.document, gates=tuple(gates)), "Editar porta"
            )
        except ValueError as exc:
            self.message.setText(str(exc))

    def _remove(self):
        chosen = set(self.selected_indices or ([self.selected] if self.selected >= 0 else []))
        if chosen:
            gates = [gate for index, gate in enumerate(self.document.gates) if index not in chosen]
            self.replace_document(
                replace(self.document, gates=tuple(gates)), "Remover seleção"
            )

    def _select_all(self):
        indexes = list(range(len(self.document.gates)))
        self.canvas.select_operations(indexes)
        self._select_many(indexes)

    def _copy_selected(self):
        chosen = self.selected_indices or ([self.selected] if self.selected >= 0 else [])
        if not chosen:
            self.message.setText("Selecione uma ou mais portas para copiar.")
            return
        document = CircuitDocument(self.document.num_qubits, tuple(self.document.gates[i] for i in sorted(chosen)))
        text = json.dumps(document.to_dict(), ensure_ascii=False, allow_nan=False)
        mime = QMimeData()
        mime.setData(CIRCUIT_CLIPBOARD, text.encode("utf-8"))
        mime.setText(text)
        QApplication.clipboard().setMimeData(mime)
        self.message.setText(f"{len(chosen)} porta(s) copiadas. Qubits e parâmetros preservados.")

    def _cut_selected(self):
        if self.selected_indices:
            self._copy_selected()
            self._remove()

    def _paste_gates(self):
        mime = QApplication.clipboard().mimeData()
        if not mime or not mime.hasFormat(CIRCUIT_CLIPBOARD):
            self.message.setText("Copie portas no editor antes de colar.")
            return
        try:
            data = bytes(mime.data(CIRCUIT_CLIPBOARD))
            if len(data) > 200_000:
                raise ValueError("Seleção copiada excede 200 kB")
            copied = CircuitDocument.from_dict(json.loads(data.decode("utf-8")))
            index = self.selected + 1 if self.selected >= 0 else len(self.document.gates)
            gates = self.document.gates[:index] + copied.gates + self.document.gates[index:]
            after = replace(self.document, gates=gates)
            after.validate()
            self.selected = index + len(copied.gates) - 1
            self.replace_document(after, "Colar portas")
            indexes = list(range(index, index + len(copied.gates)))
            self.canvas.select_operations(indexes)
            self._select_many(indexes)
        except (ValueError, UnicodeError) as exc:
            self.message.setText(str(exc))

    def _reorder(self, source, target):
        if (
            not 0 <= source < len(self.document.gates)
            or not 0 <= target < len(self.document.gates)
            or source == target
        ):
            return
        gates = list(self.document.gates)
        gate = gates.pop(source)
        gates.insert(target, gate)
        self.selected = target
        self.replace_document(
            replace(self.document, gates=tuple(gates)), "Reordenar portas"
        )

    def _apply_phase(self):
        try:
            self.replace_document(
                replace(self.document, global_phase=parse_angle(self.phase.text())),
                "Alterar fase global",
            )
        except ValueError as exc:
            self.message.setText(str(exc))

    def _change_qubits(self, value):
        before = self.document
        self.replace_document(replace(before, num_qubits=value), "Alterar qubits")
        if self.document.num_qubits != value:
            blocker = QSignalBlocker(self.qubits)
            self.qubits.setValue(before.num_qubits)
            del blocker

    def _bell(self):
        self.replace_document(
            CircuitDocument(2, (CircuitGate("h", (0,)), CircuitGate("cx", (0, 1)))),
            "Exemplo Bell",
        )

    def configuration(self):
        seed = self.seed.text().strip()
        if seed and (not seed.isascii() or not seed.isdecimal()):
            raise ValueError("Semente deve ser um inteiro não negativo")
        self.document.validate()
        steps = max(1, len(self.document.gates))
        config = ExperimentConfig(
            SystemConfig(self.document.num_qubits, J=0.0, h=0.0),
            SimulationProtocol(float(steps), steps, True),
            NoiseConfig(
                self.noise.isChecked(),
                self.noise_kind.currentData(),
                self.p1.value(),
                self.p2.value(),
                self.t1.value(),
                self.t2.value(),
                self.gate1.value(),
                self.gate2.value(),
            ),
            self.shots.value(),
            int(seed) if seed else None,
            self.document,
        )
        config.validate()
        return config

    def _run(self):
        try:
            self._apply_phase()
            # Read the field again so an invalid phase never executes a stale draft.
            parse_angle(self.phase.text())
            self.run_requested.emit(self.configuration())
        except ValueError as exc:
            self.message.setText(str(exc))
            self.execution_status.setText("Revise a configuração: " + str(exc))

    def set_running(self, running):
        self._running = running
        self.run.setEnabled(not running)
        self.run.setText("Executando…" if running else "Executar circuito")
        self.cancel.setEnabled(running)
        self.execution_status.setText("Execução em andamento. Você pode cancelar com segurança."
                                      if running else "Pronto para executar · medição final na base Z.")
        self._describe_template()

    def _import(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Abrir circuito", "", "Circuito JSON (*.json);;OpenQASM 2 (*.qasm)"
        )
        if not path:
            return
        try:
            if Path(path).stat().st_size > 200_000:
                raise ValueError("Arquivo excede 200 kB")
            text = Path(path).read_text(encoding="utf-8")
            document = (
                CircuitDocument.from_qasm(text)
                if Path(path).suffix.lower() == ".qasm"
                else CircuitDocument.from_dict(json.loads(text))
            )
            self.replace_document(document, "Importar circuito")
        except (OSError, ValueError) as exc:
            self.message.setText(str(exc))

    def _export(self):
        path, kind = QFileDialog.getSaveFileName(
            self,
            "Salvar circuito",
            "circuito.json",
            "Circuito JSON (*.json);;OpenQASM 2 (*.qasm)",
        )
        if not path:
            return
        try:
            self.replace_document(
                replace(self.document, global_phase=parse_angle(self.phase.text())),
                "Alterar fase global",
            )
            self.document.validate()
            text = (
                self.document.to_qasm()
                if "OpenQASM" in kind or Path(path).suffix.lower() == ".qasm"
                else json.dumps(
                    self.document.to_dict(),
                    ensure_ascii=False,
                    indent=2,
                    allow_nan=False,
                )
            )
            Path(path).write_text(text, encoding="utf-8")
            self.message.setText(
                "Circuito salvo. JSON preserva a fase global; QASM 2 a registra como comentário Entrela."
            )
        except (OSError, ValueError) as exc:
            self.message.setText(str(exc))

    def _export_svg(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Exportar desenho", "circuito.svg", "SVG (*.svg)"
        )
        if path:
            try:
                self.canvas.export_svg(path)
                self.message.setText("Desenho vetorial exportado.")
            except OSError as exc:
                self.message.setText(str(exc))

    def _update_noise_fields(self, *_):
        thermal = self.noise_kind.currentData() == "Termico"
        for field in (self.p1, self.p2):
            field.setEnabled(self.noise.isChecked() and not thermal)
        for field in (self.t1, self.t2, self.gate1,self.gate2):
            field.setEnabled(self.noise.isChecked() and thermal)
        self.noise.setToolTip(
            "Térmico: durações por porta configuráveis em Mais opções de ruído; T₂ ≤ 2T₁. Valores assumidos, sem calibração de hardware."
            if thermal
            else "Probabilidades de despolarização por operação de 1 ou 2 qubits."
        )

    def _sync_zoom(self, value):
        blocker = QSignalBlocker(self.zoom)
        self.zoom.setValue(value)
        del blocker

    def refresh_theme(self):
        for action, name in self._history_actions:
            action.setIcon(get_icon(name, color=PALETTE.text))
