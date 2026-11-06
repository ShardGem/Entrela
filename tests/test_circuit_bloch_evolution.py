"""Scientific precision, durable circuit revisions and snapshot interaction regressions."""

from dataclasses import replace
from types import SimpleNamespace
import json
import math

import numpy as np
import pytest
from matplotlib.backend_bases import MouseEvent
from qiskit.quantum_info import Statevector
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest

from core.circuit_document import CircuitDocument, CircuitGate
from core.examples import create_example_config
from core.simulation import run_experiment
from core.types import ExperimentConfig, SystemConfig, SimulationProtocol, NoiseConfig
from data.circuit_library import CircuitLibrary
from gui.pages.bloch import BlochPage
from gui.widgets.circuit_editor import CircuitEditor
from gui.widgets.circuit_canvas import LEFT, TOP, COLUMN


@pytest.fixture
def editor(qt_app):
    widget = CircuitEditor()
    yield widget
    QApplication.clipboard().clear()
    widget.close()


def test_editing_without_changes_preserves_full_angle_and_global_phase(editor):
    angle = 0.12345678912345678
    document = CircuitDocument(1, (CircuitGate("rx", (0,), (angle,)),), 0.23456789123456789)
    editor.replace_document(document)
    editor._select(0)
    assert float(editor.param_fields[0].text()) == angle
    editor._apply_gate()
    editor._apply_phase()
    assert editor.document == document


def test_multigate_clipboard_order_parameters_and_undo(editor):
    document = CircuitDocument(2, (
        CircuitGate("h", (0,)), CircuitGate("ry", (1,), (0.12345678912345678,)),
        CircuitGate("cx", (0, 1)),
    ))
    editor.replace_document(document)
    editor._select_many([0, 2])
    editor._copy_selected()
    editor._paste_gates()
    assert editor.document.gates == document.gates + (document.gates[0], document.gates[2])
    assert editor.selected_indices == [3, 4]
    editor.undo_stack.undo()
    assert editor.document == document
    editor.undo_stack.redo()
    editor._select_all()
    editor._cut_selected()
    assert editor.document.gates == ()
    editor.undo_stack.undo()
    assert len(editor.document.gates) == 5


def test_ctrl_click_multiselection_and_clipboard_shortcut_respects_text_fields(editor, qt_app):
    editor._bell()
    editor.resize(1300, 850)
    editor.show()
    qt_app.processEvents()
    first = editor.canvas.mapFromScene(LEFT, TOP)
    second = editor.canvas.mapFromScene(LEFT + COLUMN, TOP)
    QTest.mouseClick(editor.canvas.viewport(), Qt.LeftButton, Qt.NoModifier, first)
    QTest.mouseClick(editor.canvas.viewport(), Qt.LeftButton, Qt.ControlModifier, second)
    assert editor.selected_indices == [0, 1]
    QTest.keyClick(editor.canvas, Qt.Key_C, Qt.ControlModifier)
    QTest.keyClick(editor.canvas, Qt.Key_V, Qt.ControlModifier)
    assert [gate.name for gate in editor.document.gates] == ["h", "cx", "h", "cx"]
    editor.circuit_name.setText("Texto para copiar")
    editor.circuit_name.setFocus()
    editor.circuit_name.selectAll()
    QTest.keyClick(editor.circuit_name, Qt.Key_C, Qt.ControlModifier)
    assert QApplication.clipboard().text() == "Texto para copiar"


@pytest.mark.parametrize("width,columns", [(680, 1), (880, 1), (1280, 2)])
def test_gate_palette_columns_fit_viewport_at_different_widths(editor, qt_app, width, columns):
    from gui.theme import build_qss
    editor.setStyleSheet(build_qss())
    editor.resize(width, 850)
    editor.show()
    for _ in range(3):
        qt_app.processEvents()
    viewport = editor.palette_scroll.viewport()
    assert editor.palette_scroll.horizontalScrollBar().maximum() == 0
    for button in editor.palette_buttons.values():
        position = button.mapTo(viewport, button.rect().topLeft())
        assert position.x() >= 0
        assert position.x() + button.width() <= viewport.width()
    # Readable gate names need more room than symbols alone. Narrow editors
    # keep one column so the drawing and inspector retain usable space.
    assert editor._palette_columns == columns


def test_named_revisions_restore_without_overwriting_and_duplicate(editor, tmp_path):
    editor.set_storage_directory(tmp_path / "circuits")
    editor.circuit_name.setText("Bell para aula")
    editor._bell()
    first = editor.document
    editor._save_revision()
    identifier = editor._library_id
    editor._add("z")
    second = editor.document
    editor._save_revision()
    assert [r.document for r in CircuitLibrary(tmp_path / "circuits").revisions(identifier)] == [first, second]
    editor.revision_combo.setCurrentIndex(editor.revision_combo.findData(1))
    editor._load_revision()
    assert editor.document == first
    editor._save_revision()
    revisions = editor.library.revisions(identifier)
    assert [r.version for r in revisions] == [1, 2, 3]
    assert revisions[1].document == second and revisions[2].document == first
    editor._duplicate()
    editor._save_revision()
    assert editor._library_id != identifier
    assert len(editor.library.entries()) == 2
    editor.phase.setText("invalid")
    editor._save_revision()
    assert len(editor.library.revisions(editor._library_id)) == 1


def test_library_rejects_traversal_and_skips_corrupt_foreign_file(tmp_path):
    library = CircuitLibrary(tmp_path)
    with pytest.raises(ValueError):
        library.revisions("../other")
    path = tmp_path / ("a" * 32 + ".json")
    path.write_text(json.dumps({"schema_version": 1, "id": "a" * 32, "revisions": []}))
    assert library.entries() == []


def test_focus_dropdown_synchronizes_selection_and_new_snapshot_set(qt_app):
    page = BlochPage()
    page.load_statevectors([Statevector.from_label("00"), Statevector.from_label("11")])
    page.focus_combo.setCurrentIndex(page.focus_combo.findData(0))
    page.focus_combo.setCurrentIndex(page.focus_combo.findData(1))
    assert page.canvas.focus == page.canvas.selected_qubit == 1
    assert "q1" in page.selection_label.text()
    assert page._qubit_panels[0].isHidden()
    page.slider.setValue(1)
    page.load_statevectors([Statevector.from_label("0")])
    assert page.current_frame == 0 and page.canvas.focus == -1
    page.close()


def test_probability_hover_reports_full_numeric_precision_and_snapshot(qt_app):
    page = BlochPage()
    state = Statevector([math.sqrt(1 / 3), math.sqrt(2 / 3)])
    page.load_statevectors([state], times=[0.1234567890123456])
    page.visual_tabs.setCurrentIndex(1)
    page.probabilities_canvas.draw()
    bar, _, value, _ = page._probability_bars[0]
    point = bar.axes.transData.transform((bar.get_x() + bar.get_width() / 2, value / 2))
    event = MouseEvent("motion_notify_event", page.probabilities_canvas, *point)
    page._hover_probability(event)
    text = page._probability_annotation.get_text()
    assert f"{value:.17g}" in text
    assert "|0⟩" in text and "Snapshot 1" in text
    assert "0.12345678901234559" in text
    page._hover_probability(SimpleNamespace(inaxes=None))
    assert not page._probability_annotation.get_visible()
    page.close()


def test_timeline_distinguishes_logical_gates_from_trotter_layers(qt_app):
    page = BlochPage()
    document = CircuitDocument(3, (CircuitGate("h", (0,)), CircuitGate("ccx", (0, 1, 2))))
    config = ExperimentConfig(SystemConfig(3), SimulationProtocol(2, 2, True), NoiseConfig(False), 64, 42, document)
    record = run_experiment(config)
    page.load_statevectors(record.result.states, record.result.times, time_unit=record.result.metadata["time_unit"])
    page.set_experiment(record)
    page.slider.setValue(2)
    text = page.timeline_detail.toPlainText()
    assert "Porta lógica 2: CCX" in text
    assert "Antes:" in text and "Depois:" in text
    record = run_experiment(replace(create_example_config("bell"), shots=64))
    page.load_statevectors(record.result.states, record.result.times)
    page.set_experiment(record)
    page.slider.setValue(1)
    assert "Camada Suzuki–Trotter 1" in page.timeline_detail.toPlainText()
    assert "não há estados intermediários por porta" in page.timeline_detail.toPlainText()
    page.close()
