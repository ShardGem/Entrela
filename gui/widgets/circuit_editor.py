"""Editable circuit workbench, undoable documents and real execution settings."""

from dataclasses import replace
from pathlib import Path
import json
import math
from PySide6.QtCore import Qt, Signal, QSignalBlocker
from PySide6.QtGui import QUndoStack, QUndoCommand, QKeySequence
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
    QScrollArea,
    QFileDialog,
)
from core.circuit_document import (
    CircuitDocument,
    CircuitGate,
    GATES,
    GATE_HELP,
    parse_angle,
)
from core.types import ExperimentConfig, SystemConfig, SimulationProtocol, NoiseConfig
from gui.widgets.circuit_canvas import CircuitCanvas, angle_label
from gui.widgets.button import PrimaryButton, SecondaryButton, GhostButton
from gui.widgets.scientific_input import ScientificSpinBox
from gui.icons import get_icon
from gui.theme import PALETTE


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

    def __init__(self, parent=None):
        super().__init__(parent)
        self.document = CircuitDocument()
        self.selected = -1
        self._running = False
        self.undo_stack = QUndoStack(self)
        self._history_actions = []
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        toolbar = QHBoxLayout()
        self.qubits = QSpinBox()
        self.qubits.setRange(1, 6)
        self.qubits.setValue(2)
        self.qubits.setAccessibleName("Quantidade de qubits do editor")
        toolbar.addWidget(QLabel("Qubits"))
        toolbar.addWidget(self.qubits)
        self.phase = QLineEdit("0")
        self.phase.setMaximumWidth(125)
        self.phase.setAccessibleName("Fase global em radianos")
        toolbar.addWidget(QLabel("Fase global"))
        toolbar.addWidget(self.phase)
        phase_button = SecondaryButton("Aplicar")
        phase_button.clicked.connect(self._apply_phase)
        toolbar.addWidget(phase_button)
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
        toolbar.addStretch()
        root.addLayout(toolbar)
        files = QHBoxLayout()
        self.zoom = QSpinBox()
        self.zoom.setRange(35, 250)
        self.zoom.setValue(100)
        self.zoom.setSuffix("%")
        self.zoom.setPrefix("Zoom ")
        self.zoom.valueChanged.connect(lambda value: self.canvas.set_zoom(value))
        for text, callback in [
            (
                "Novo",
                lambda: self.replace_document(
                    CircuitDocument(self.document.num_qubits), "Novo circuito"
                ),
            ),
            ("Bell", self._bell),
            ("Abrir JSON / QASM", self._import),
            ("Salvar JSON / QASM", self._export),
            ("SVG do trecho", self._export_svg),
            ("Ajustar visão", lambda: self.canvas.fit_circuit()),
        ]:
            button = GhostButton(text)
            button.clicked.connect(callback)
            files.addWidget(button)
        files.addWidget(self.zoom)
        root.addLayout(files)
        row = QHBoxLayout()
        palette = QWidget()
        palette_body = QGridLayout(palette)
        self.palette_buttons = {}
        for i, name in enumerate(GATES):
            button = SecondaryButton(name.upper())
            button.setToolTip(GATE_HELP[name] + "\nAdicionar após a seleção.")
            button.clicked.connect(lambda _, n=name: self._add(n))
            palette_body.addWidget(button, i // 2, i % 2)
            self.palette_buttons[name] = button
        palette_scroll = QScrollArea()
        palette_scroll.setWidgetResizable(True)
        palette_scroll.setWidget(palette)
        palette_scroll.setMinimumWidth(125)
        palette_scroll.setMaximumWidth(155)
        row.addWidget(palette_scroll)
        self.canvas = CircuitCanvas(editable=True)
        self.canvas.zoom_changed.connect(self._sync_zoom)
        row.addWidget(self.canvas, 1)
        self.canvas.operation_selected.connect(self._select)
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
        form = QFormLayout()
        form.setRowWrapPolicy(QFormLayout.WrapLongRows)
        self.gate_type = QComboBox()
        self.gate_type.addItems(list(GATES))
        form.addRow("Porta", self.gate_type)
        self.qubit_fields = []
        self.param_fields = []
        for i in range(3):
            spin = QSpinBox()
            spin.setRange(0, 1)
            spin.setAccessibleName(f"Conexão {i + 1} da porta")
            self.qubit_fields.append(spin)
            form.addRow(f"Qubit {i + 1}", spin)
        for name in ("θ / ângulo", "φ", "λ"):
            field = QLineEdit("0")
            field.setPlaceholderText("pi/2")
            field.setAccessibleName(name)
            self.param_fields.append(field)
            form.addRow(name, field)
        self.gate_form = form
        form_body.addLayout(form)
        apply = PrimaryButton("Aplicar à porta")
        apply.clicked.connect(self._apply_gate)
        form_body.addWidget(apply)
        for text, callback in [
            ("Remover porta", self._remove),
            ("Mover antes", lambda: self._reorder(self.selected, self.selected - 1)),
            ("Mover depois", lambda: self._reorder(self.selected, self.selected + 1)),
        ]:
            button = SecondaryButton(text)
            button.clicked.connect(callback)
            form_body.addWidget(button)
        note = QLabel(
            "Ângulos em radianos. Aceita pi/2, −pi/4 ou decimais. As medições em Z são adicionadas ao final."
        )
        note.setWordWrap(True)
        form_body.addWidget(note)
        noise_toggle = QToolButton()
        noise_toggle.setText("Mais opções de ruído")
        noise_toggle.setCheckable(True)
        advanced = QWidget()
        advanced_form = QFormLayout(advanced)
        advanced_form.setRowWrapPolicy(QFormLayout.WrapLongRows)
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
        row.addWidget(inspector_scroll)
        root.addLayout(row, 1)
        settings = QGridLayout()
        self.shots = QSpinBox()
        self.shots.setRange(1, 1_000_000)
        self.shots.setValue(1024)
        self.seed = QLineEdit("42")
        self.seed.setMaximumWidth(110)
        self.seed.setPlaceholderText("Automática")
        self.noise = QCheckBox("Ativar ruído")
        self.p1 = ScientificSpinBox()
        self.p2 = ScientificSpinBox()
        for w, value in [(self.p1, 0.01), (self.p2, 0.05)]:
            w.setRange(0, 1)
            w.setValue(value)
            w.setMaximumWidth(100)
        for text, widget, row, column in [
            ("Shots", self.shots, 0, 0),
            ("Semente", self.seed, 0, 2),
            ("p1", self.p1, 1, 0),
            ("p2", self.p2, 1, 2),
        ]:
            settings.addWidget(QLabel(text), row, column)
            settings.addWidget(widget, row, column + 1)
        settings.addWidget(self.noise, 0, 4, 1, 2)
        self.run = PrimaryButton("Executar circuito", icon="play")
        self.run.clicked.connect(self._run)
        settings.addWidget(self.run, 1, 4, 1, 2)
        settings.setColumnStretch(5, 1)
        root.addLayout(settings)
        self.message = QLabel(
            "Rascunho independente · até 200 portas · arraste as portas para reordenar."
        )
        self.message.setWordWrap(True)
        self.message.setTextFormat(Qt.PlainText)
        root.addWidget(self.message)
        self.gate_type.currentTextChanged.connect(self._show_fields)
        self.qubits.valueChanged.connect(self._change_qubits)
        self.noise.toggled.connect(self._update_noise_fields)
        self.noise_kind.currentIndexChanged.connect(self._update_noise_fields)
        self._update_noise_fields()
        self._set_document(self.document)

    def replace_document(self, document, title="Carregar circuito"):
        try:
            document.validate()
            if document != self.document:
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
        self.phase.setToolTip(repr(float(document.global_phase)) + " rad")
        del blockers
        for field in self.qubit_fields:
            field.setRange(0, document.num_qubits - 1)
        for name, button in self.palette_buttons.items():
            button.setEnabled(GATES[name][1] <= document.num_qubits)
        self.canvas.description = f"Fase global: {document.global_phase!r} rad; {document.num_qubits} qubits; medição final na base Z."
        self.canvas.set_operations(operation_records(document), document.num_qubits)
        self._select(self.selected)

    def _select(self, index):
        self.selected = index if 0 <= index < len(self.document.gates) else -1
        if self.selected < 0:
            self.selection_label.setText("Adicione uma porta pela paleta.")
            self._show_fields()
            return
        gate = self.document.gates[self.selected]
        self.selection_label.setText(
            f"Porta {self.selected + 1} de {len(self.document.gates)} · {gate.name.upper()}"
        )
        self.gate_type.setCurrentText(gate.name)
        for i, value in enumerate(gate.qubits):
            self.qubit_fields[i].setValue(value)
        for i, value in enumerate(gate.parameters):
            self.param_fields[i].setText(angle_label(value))
        self.canvas.select_operation(self.selected)
        self._show_fields()

    def _show_fields(self, *_):
        name = self.gate_type.currentText()
        _, arity, nparams = GATES[name]
        self.gate_help.setText(GATE_HELP[name])
        for i, w in enumerate(self.qubit_fields):
            self.gate_form.setRowVisible(w, i < arity)
            label = (
                ("Alvo" if i == arity - 1 else "Controle " + str(i + 1))
                if name in ("cx", "cy", "cz", "ch", "ccx")
                else "Qubit " + str(i + 1)
            )
            self.gate_form.labelForField(w).setText(label)
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
        if self.selected >= 0:
            gates = list(self.document.gates)
            gates.pop(self.selected)
            self.replace_document(
                replace(self.document, gates=tuple(gates)), "Remover porta"
            )

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

    def set_running(self, running):
        self._running = running
        self.run.setEnabled(not running)
        self.run.setText("Executando…" if running else "Executar circuito")

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
        for field in (self.t1, self.t2):
            field.setEnabled(self.noise.isChecked() and thermal)
        self.noise.setToolTip(
            "Térmico: duração educativa de 50 ns por porta; T₂ ≤ 2T₁."
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
