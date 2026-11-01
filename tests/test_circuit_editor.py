"""Circuit semantics, document persistence and real graphical editing workflows."""

from dataclasses import replace, asdict
import json
import math
import numpy as np
import pytest
from qiskit.quantum_info import Statevector, Operator
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from core.circuit_document import CircuitDocument, CircuitGate, GATES, parse_angle
from core.types import (
    ExperimentConfig,
    SystemConfig,
    SimulationProtocol,
    NoiseConfig,
    config_from_dict,
)
from core.simulation import run_experiment
from core.analysis import temporal_analysis, convergence_analysis, parameter_sweep
from core.examples import create_example_config
from data.repository import ExperimentRepository
from gui.widgets.circuit_canvas import GateItem, TOP, WIRE
from tests.qt_helpers import wait_until


def configuration(document, noisy=False):
    steps = max(1, len(document.gates))
    return ExperimentConfig(
        SystemConfig(document.num_qubits, J=0, h=0),
        SimulationProtocol(float(steps), steps, True),
        NoiseConfig(enabled=noisy),
        128,
        42,
        document,
    )


@pytest.mark.parametrize(
    "text,value",
    [
        ("pi/2", math.pi / 2),
        ("−π/4", -math.pi / 4),
        ("2*pi - 1", 2 * math.pi - 1),
        ("0,125", 0.125),
    ],
)
def test_angle_language(text, value):
    assert parse_angle(text) == pytest.approx(value)


@pytest.mark.parametrize(
    "text",
    [
        '__import__("os").system("echo nope")',
        "pi.__class__",
        "1/0",
        "2**99999",
        "[1]",
        'float("nan")',
    ],
)
def test_angle_language_rejects_code_and_unbounded_expressions(text):
    with pytest.raises(ValueError):
        parse_angle(text)


@pytest.mark.parametrize("name", list(GATES))
def test_editor_gates_match_qiskit_unitary_and_preserve_phase(name):
    _, arity, nparams = GATES[name]
    n = max(2, arity)
    gates = tuple(CircuitGate("h", (q,)) for q in range(n)) + (
        CircuitGate(
            name, tuple(range(arity)), tuple(0.2 * (i + 1) for i in range(nparams))
        ),
    )
    document = CircuitDocument(n, gates, 5.2832)
    result = run_experiment(configuration(document)).result
    np.testing.assert_allclose(
        result.final_state.data,
        Statevector.from_instruction(document.to_quantum_circuit()).data,
        atol=1e-10,
    )
    assert result.energy is None
    assert result.fidelity == pytest.approx(1)
    assert len(result.states) == len(gates) + 1
    assert result.metadata["experiment_kind"] == "circuit"


def test_document_qasm_json_roundtrip_and_reproducible_record(tmp_path):
    document = CircuitDocument(
        2,
        (
            CircuitGate("h", (0,)),
            CircuitGate("u", (1,), (0.1, -math.pi / 2, math.pi / 2)),
            CircuitGate("cx", (0, 1)),
        ),
        5.2832,
    )
    assert (
        CircuitDocument.from_dict(json.loads(json.dumps(document.to_dict())))
        == document
    )
    qasm = CircuitDocument.from_qasm(document.to_qasm())
    np.testing.assert_allclose(
        Operator(qasm.to_quantum_circuit()).data,
        Operator(document.to_quantum_circuit()).data,
        atol=1e-12,
    )
    config = configuration(document, True)
    assert config_from_dict(asdict(config)) == config
    record = run_experiment(config)
    repo = ExperimentRepository(tmp_path)
    repo.save(record)
    loaded = repo.load(record.id)
    assert loaded.config == config
    rerun = run_experiment(loaded.config)
    assert rerun.result.counts == record.result.counts
    np.testing.assert_allclose(
        rerun.result.final_state.data, record.result.final_state.data
    )


def test_circuit_analysis_does_not_invent_hamiltonian_energy():
    doc = CircuitDocument(2, (CircuitGate("h", (0,)), CircuitGate("cx", (0, 1))))
    record = run_experiment(configuration(doc, True))
    rows = temporal_analysis(record)["rows"]
    assert all(
        r["energy"] is None
        and r["fidelity_exact"] is None
        and r["trotter_infidelity"] is None
        for r in rows
    )
    with pytest.raises(ValueError):
        convergence_analysis(record.config)
    with pytest.raises(ValueError):
        parameter_sweep(record.config, "J", [0, 1])


def test_three_qubit_gate_gets_native_noise():
    doc = CircuitDocument(
        3,
        tuple(CircuitGate("h", (q,)) for q in range(3))
        + (CircuitGate("ccx", (0, 1, 2)),),
    )
    config = replace(configuration(doc, True), noise=NoiseConfig(True, p1=0, p2=0.2))
    record = run_experiment(config)
    assert record.result.purity < 0.9
    assert any(
        op.get("logical_gate") == "ccx" and op["name"] == "cx"
        for op in record.result.metadata["operations"]
    )


@pytest.mark.parametrize(
    "document",
    [
        CircuitDocument(2, (CircuitGate("cx", (0, 0)),)),
        CircuitDocument(1, (CircuitGate("rx", (0,), ()),)),
        CircuitDocument(2, (CircuitGate("h", (5,)),)),
        CircuitDocument(2, (), float("nan")),
        CircuitDocument(2, tuple(CircuitGate("h", (0,)) for _ in range(201))),
    ],
)
def test_invalid_documents_are_rejected(document):
    with pytest.raises(ValueError):
        document.validate()


def test_graphical_edit_undo_redo_and_source_are_independent(window, qt_app):
    record = run_experiment(replace(create_example_config("bell"), shots=64))
    page = window.page_circuit
    page.show_experiment(record)
    original = record.config
    page._copy_to_editor()
    editor = page.editor
    before = editor.document
    editor._add("x")
    assert len(editor.document.gates) == len(before.gates) + 1
    editor.undo_stack.undo()
    assert editor.document == before
    editor.undo_stack.redo()
    assert editor.document != before
    editor._reorder(0, 1)
    assert editor.document.gates[1] == before.gates[0]
    assert record.config == original
    assert page.operations == record.result.metadata["operations"]
    assert page.phase_label.text().startswith("Fase global:")


def test_graphical_click_inspects_gate_and_svg_is_vector(window, qt_app, tmp_path):
    page = window.page_circuit
    editor = page.editor
    editor._bell()
    window._show_page("circuit")
    page.tabs.setCurrentWidget(editor)
    qt_app.processEvents()
    item = next(
        i
        for i in editor.canvas.scene().items()
        if isinstance(i, GateItem) and i.index == 1
    )
    point = editor.canvas.mapFromScene(item.pos().x(), TOP + WIRE)
    QTest.mouseClick(editor.canvas.viewport(), Qt.LeftButton, Qt.NoModifier, point)
    assert editor.selected == 1
    assert editor.gate_type.currentText() == "cx"
    path = tmp_path / "circuit.svg"
    editor.canvas.export_svg(path)
    text = path.read_text(encoding="utf-8")
    assert "<svg" in text and "<path" in text
    assert "<image" not in text


def test_invalid_field_changes_do_not_mutate_draft(window):
    editor = window.page_circuit.editor
    editor._bell()
    editor._select(1)
    before = editor.document
    editor.qubit_fields[0].setValue(1)
    editor.qubit_fields[1].setValue(1)
    editor._apply_gate()
    assert editor.document == before
    editor.phase.setText('__import__("os")')
    editor._run()
    assert window._current_worker is None


def test_editor_execution_storage_reopen_and_snapshot_navigation(window, qt_app):
    editor = window.page_circuit.editor
    editor._bell()
    editor.shots.setValue(64)
    editor.phase.setText("2*pi-1")
    editor._run()
    wait_until(lambda: window._current_worker is None)
    record = window._current_experiment
    assert record.config.circuit is not None
    assert set(record.result.counts) <= {"00", "11"}
    saved = window.repository.load(record.id)
    assert saved.config.circuit == editor.document
    window._open_experiment(record.id)
    page = window.page_circuit
    page.select_operation(1)
    page.snapshot_button.click()
    assert window._current_page == "bloch"
    assert window.page_bloch.current_frame == 2
    assert "porta" in window.page_bloch.frame_label.text()
    window._run_analysis("temporal", {})
    wait_until(lambda: window._current_worker is None)
    assert len(window.page_bloch.metrics.rows) == 3
    assert "Energia=—" in window.page_bloch.metrics.summary.text()


def test_source_trotter_copy_preserves_actual_unitary_and_global_phase(window):
    from core.circuits import build_circuit

    config = ExperimentConfig(
        SystemConfig(2), SimulationProtocol(1, 4, True), NoiseConfig(False), 64, 42
    )
    record = run_experiment(config)
    window.page_circuit.show_experiment(record)
    window.page_circuit._copy_to_editor()
    document = window.page_circuit.editor.document
    assert document.global_phase == pytest.approx(
        record.result.metadata["circuit_global_phase"]
    )
    assert document.global_phase == pytest.approx(2 * math.pi - 1)
    np.testing.assert_allclose(
        Statevector.from_instruction(document.to_quantum_circuit()).data,
        record.result.final_state.data,
        atol=1e-12,
    )


def test_custom_record_schema_cannot_be_misread_as_a_hamiltonian(tmp_path):
    record = run_experiment(
        configuration(CircuitDocument(1, (CircuitGate("h", (0,)),)))
    )
    raw = ExperimentRepository._serialize(record)
    assert raw["schema_version"] == 3
    raw["schema_version"] = 2
    with pytest.raises(ValueError):
        ExperimentRepository._deserialize(raw)


def test_editor_thermal_configuration_and_validation(window):
    editor = window.page_circuit.editor
    editor._bell()
    editor.noise_kind.setCurrentIndex(editor.noise_kind.findData("Termico"))
    editor.noise.setChecked(True)
    editor.t1.setValue(50)
    editor.t2.setValue(30)
    config = editor.configuration()
    assert config.noise.kind == "Termico"
    record = run_experiment(replace(config, shots=64))
    assert record.result.purity < 1
    editor.t2.setValue(200)
    with pytest.raises(ValueError):
        editor.configuration()


def test_drag_reorders_after_mouse_release(window, qt_app):
    from gui.widgets.circuit_canvas import LEFT, COLUMN

    editor = window.page_circuit.editor
    editor._bell()
    window._show_page("circuit")
    window.page_circuit.tabs.setCurrentWidget(editor)
    qt_app.processEvents()
    start = editor.canvas.mapFromScene(LEFT, TOP)
    end = editor.canvas.mapFromScene(LEFT + COLUMN * 1.2, TOP)
    QTest.mousePress(editor.canvas.viewport(), Qt.LeftButton, Qt.NoModifier, start)
    QTest.mouseMove(editor.canvas.viewport(), end, 40)
    QTest.mouseRelease(editor.canvas.viewport(), Qt.LeftButton, Qt.NoModifier, end)
    qt_app.processEvents()
    assert editor.document.gates[0].name == "cx"
    assert editor.document.gates[1].name == "h"
    editor.undo_stack.undo()
    assert editor.document.gates[0].name == "h"
