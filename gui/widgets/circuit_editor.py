"""Editable circuit workbench, undoable documents and real execution settings."""

from dataclasses import replace
from pathlib import Path
import json
import math
from PySide6.QtCore import Qt, Signal, QSignalBlocker, QMimeData, QEvent, QTimer
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
    QScrollArea,
    QFileDialog,
    QApplication,
    QPlainTextEdit,
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
from gui.widgets.scientific_input import ScientificSpinBox
from gui.icons import get_icon
from gui.theme import PALETTE
from data.circuit_library import CircuitLibrary

CIRCUIT_CLIPBOARD = "application/x-entrela-circuit-gates"


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
        self.selected_indices = []
        self.library = None
        self._library_id = None
        self._loaded_revision = None
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
                self._new,
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
        library_row = QHBoxLayout()
        self.circuit_name = QLineEdit()
        self.circuit_name.setMaxLength(120)
        self.circuit_name.setPlaceholderText("Nome do circuito")
        self.circuit_name.setAccessibleName("Nome do circuito na biblioteca")
        library_row.addWidget(self.circuit_name, 1)
        self.save_revision_button = SecondaryButton("Salvar revisão")
        self.save_revision_button.clicked.connect(self._save_revision)
        self.save_revision_button.setEnabled(False)
        library_row.addWidget(self.save_revision_button)
        library_toggle = GhostButton("Biblioteca")
        library_toggle.setCheckable(True)
        library_row.addWidget(library_toggle)
        self.revision_label = QLabel("Rascunho independente")
        library_row.addWidget(self.revision_label)
        root.addLayout(library_row)
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
        root.addWidget(self.library_panel)
        self.library_panel.hide()
        library_toggle.toggled.connect(self.library_panel.setVisible)
        self.summary = QLabel()
        self.summary.setWordWrap(True)
        self.summary.setObjectName("SectionSubtitle")
        root.addWidget(self.summary)
        row = QHBoxLayout()
        palette = QWidget()
        palette_body = QGridLayout(palette)
        palette_body.setContentsMargins(4, 4, 4, 4)
        palette_body.setHorizontalSpacing(6)
        self.palette_grid = palette_body
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
        palette_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.palette_scroll = palette_scroll
        self._palette_columns = 2
        row.addWidget(palette_scroll)
        self.canvas = CircuitCanvas(editable=True)
        self.canvas.zoom_changed.connect(self._sync_zoom)
        row.addWidget(self.canvas, 1)
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
        self.gate_matrix = QPlainTextEdit()
        self.gate_matrix.setReadOnly(True)
        self.gate_matrix.setMaximumHeight(145)
        self.gate_matrix.setAccessibleName("Matriz unitária da porta selecionada")
        self.gate_matrix.setToolTip("Matriz numérica do Qiskit. A base local é |q[k−1]…q[0]⟩, pela ordem das conexões da porta.")
        form_body.addWidget(self.gate_matrix)
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
            ("Remover seleção", self._remove),
            ("Copiar seleção", self._copy_selected),
            ("Colar portas", self._paste_gates),
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
            "Até 200 portas · Ctrl+clique seleciona várias · Ctrl+C/V copia e cola · arraste para reordenar."
        )
        self.message.setWordWrap(True)
        self.message.setTextFormat(Qt.PlainText)
        root.addWidget(self.message)
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
            action = QAction(title, self.canvas)
            action.setShortcut(sequence)
            action.setShortcutContext(Qt.WidgetWithChildrenShortcut)
            action.triggered.connect(callback)
            self.canvas.addAction(action)
        self._set_document(self.document)
        QTimer.singleShot(0, self._resize_gate_palette)

    def _resize_gate_palette(self):
        """Reserve actual styled button widths instead of clipping two columns."""
        if not hasattr(self, "palette_scroll"):
            return
        columns = 1 if self.width() < 720 else 2
        if columns != self._palette_columns:
            for button in self.palette_buttons.values():
                self.palette_grid.removeWidget(button)
            for index, button in enumerate(self.palette_buttons.values()):
                self.palette_grid.addWidget(button, index // columns, index % columns)
            self._palette_columns = columns
        widths = [0] * columns
        for index, button in enumerate(self.palette_buttons.values()):
            button.ensurePolished()
            widths[index % columns] = max(widths[index % columns], button.minimumSizeHint().width())
        margins = self.palette_grid.contentsMargins()
        width = (sum(widths) + max(0, columns - 1) * self.palette_grid.horizontalSpacing()
                 + margins.left() + margins.right()
                 + self.palette_scroll.verticalScrollBar().sizeHint().width()
                 + 2 * self.palette_scroll.frameWidth() + 2)
        if self.palette_scroll.width() != width:
            self.palette_scroll.setFixedWidth(width)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._resize_gate_palette()

    def changeEvent(self, event):
        super().changeEvent(event)
        if event.type() in (QEvent.FontChange, QEvent.StyleChange):
            QTimer.singleShot(0, self._resize_gate_palette)

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
        except (OSError, ValueError, TypeError, KeyError, StopIteration) as exc:
            self.message.setText("Não foi possível abrir a revisão: " + str(exc))

    def _new(self):
        self.replace_document(CircuitDocument(self.document.num_qubits), "Novo circuito")
        self._library_id = self._loaded_revision = None
        self.circuit_name.clear()
        self.circuit_description.clear()
        self.revision_label.setText("Rascunho independente")

    def _duplicate(self):
        self._library_id = self._loaded_revision = None
        name = self.circuit_name.text().strip()
        self.circuit_name.setText((name + " · cópia")[:120] if name else "Cópia do circuito")
        self.revision_label.setText("Cópia independente · ainda não salva")
        self.message.setText("O próximo salvamento cria um circuito independente.")

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
        circuit = document.to_quantum_circuit()
        counts = " · ".join(f"{name.upper()} {count}" for name, count in sorted(circuit.count_ops().items()))
        self.summary.setText(f"{document.num_qubits} qubits · {len(document.gates)} portas · profundidade lógica {circuit.depth()}"
                             + (" · " + counts if counts else " · estado inicial |0…0⟩"))
        self._select(self.selected)

    def _select_many(self, indexes):
        self.selected_indices = sorted(i for i in indexes if 0 <= i < len(self.document.gates))
        self._select(self.selected_indices[-1] if self.selected_indices else -1, sync_canvas=False)

    def _select(self, index, sync_canvas=True):
        self.selected = index if 0 <= index < len(self.document.gates) else -1
        if sync_canvas:
            self.selected_indices = [self.selected] if self.selected >= 0 else []
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
        if sync_canvas:
            self.canvas.select_operation(self.selected)
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
