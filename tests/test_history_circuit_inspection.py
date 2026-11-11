"""History inspects recorded operations without editing or inventing states."""
from copy import deepcopy
from dataclasses import replace
import json
import pytest
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QGraphicsItem, QPlainTextEdit
from core.examples import create_example_config
from core.simulation import run_experiment
from core.circuit_inspection import inspect_circuit
from core.figures import circuit_figure
from core.types import ExperimentResult
from gui.widgets.circuit_canvas import GateItem, TOP
from gui.widgets.circuit_editor import CircuitEditor
from gui.widgets.circuit_inspector import CircuitInspector
from tests.qt_helpers import wait_until
from gui.controllers.appearance import apply_appearance


@pytest.fixture(scope='module')
def source():
    return run_experiment(replace(create_example_config('bell'), shots=16, seed=42))


def test_history_loads_recorded_diagram_and_explains_click_without_changing_source(window, qt_app, source):
    window.repository.save(source)
    before = window.repository._path(source.id).read_bytes()
    window._refresh_history()
    page = window.page_history
    window._show_page('history')
    page._view(source.id)
    wait_until(lambda: window._current_worker is None)
    page.detail_tabs.setCurrentWidget(page.circuit)
    page.expand_details.click()
    qt_app.processEvents()
    viewer = page.circuit
    assert isinstance(viewer, CircuitInspector)
    assert not isinstance(viewer, QPlainTextEdit)
    assert not viewer.findChildren(CircuitEditor)
    assert not viewer.canvas.editable
    assert viewer.operations == source.result.metadata['operations']
    item = next(item for item in viewer.canvas.scene().items() if isinstance(item, GateItem) and item.index == 0)
    assert not item.flags() & QGraphicsItem.ItemIsMovable
    assert 'Hadamard' in item.toolTip()
    point = viewer.canvas.mapFromScene(item.pos().x(), TOP)
    QTest.mouseClick(viewer.canvas.viewport(), Qt.LeftButton, Qt.NoModifier, point)
    assert viewer.selected == 0
    assert 'Hadamard' in viewer.details.text()
    viewer.canvas.setFocus()
    QTest.keyClick(viewer.canvas, Qt.Key_Right)
    assert viewer.selected == 1
    assert 'controle' in viewer.details.text()
    QTest.keyClick(viewer.canvas, Qt.Key_Delete)
    assert viewer.operations == source.result.metadata['operations']
    assert window._current_experiment is None  # Inspecting history does not replace the laboratory.
    assert window.repository._path(source.id).read_bytes() == before
    assert page.table.isHidden()
    page.expand_details.click()
    assert not page.table.isHidden()
    assert page.selected_identifier == source.id


def test_summary_and_stale_async_result_never_show_another_runs_circuit(window, source):
    other = replace(source, id='other-record')
    for record in (source, other):
        window.repository.save(record)
    summaries = window.repository.list_summaries()
    page = window.page_history
    page.load(summaries)
    page.selected_identifier = source.id
    page.set_detail(source)
    page.selected_identifier = other.id
    page.set_detail(next(record for record in summaries if record.id == other.id))
    assert page.circuit.canvas.isHidden()
    assert 'Carregando' in page.circuit.context.text()
    page.set_detail(source, files=[])
    assert page.circuit.experiment is None
    page.set_detail(other, files=[])
    assert page.circuit.experiment.id == other.id
    page.expand_details.setChecked(True)
    page.load([])
    assert page.selected_identifier is None
    assert page._detail_experiment is None
    assert page.circuit.experiment is None
    assert not page.expand_details.isChecked()


def test_recorded_operations_do_not_infer_missing_phase_or_rebuild(monkeypatch, source):
    metadata = deepcopy(source.result.metadata)
    metadata.pop('circuit_global_phase')
    record = replace(source, result=replace(source.result, metadata=metadata))
    monkeypatch.setattr('core.circuit_inspection.execution_circuit', lambda config: pytest.fail('Recorded evidence must not be rebuilt'))
    inspected = inspect_circuit(record)
    assert inspected.global_phase is None
    assert not inspected.reconstructed
    inspected.operations[0]['name'] = 'changed-copy'
    assert record.result.metadata['operations'][0]['name'] == 'h'


def test_preparation_gates_refer_to_the_saved_complete_preparation(qt_app, source):
    import numpy as np
    viewer = CircuitInspector(snapshots_action=True)
    selected = []
    viewer.snapshot_requested.connect(selected.append)
    try:
        viewer.show_experiment(source)
        for index in (0, 1):
            assert viewer.operations[index]['stage'] == 'preparation'
            viewer.select_operation(index)
            assert 'fim da preparação completa' in viewer.details.text()
            viewer.snapshot_button.click()
        assert selected == [0, 0]
        np.testing.assert_allclose(source.result.states[0].probabilities(), [.5, 0, 0, .5])
    finally:
        viewer.close()
        viewer.deleteLater()


def test_failed_execution_does_not_present_a_reconstructed_circuit_as_evidence(window, source):
    failed = replace(source, result=ExperimentResult(error='Falha registrada'))
    page = window.page_history
    page.load([failed])
    page.set_detail(failed, files=[])
    assert page.circuit.experiment is None
    assert not page.circuit.operations
    assert page.circuit.canvas.isHidden()
    assert 'falhou' in page.circuit.context.text()


def test_legacy_reconstruction_is_identified_in_widget_and_portable_figure(qt_app, source):
    legacy = replace(source, result=replace(source.result, metadata={}, circuit_text='ASCII is retained only as a legacy artifact'))
    viewer = CircuitInspector()
    try:
        viewer.show_experiment(legacy)
        assert 'reconstruído' in viewer.context.text()
        assert 'bibliotecas atuais' in viewer.context.text()
        assert viewer.operations[0]['stage'] == 'preparation'
        assert viewer.operations[0]['step'] == 0
        fig = circuit_figure(legacy)
        assert 'Reconstruído' in fig._suptitle.get_text()
        fig.clear()
    finally:
        viewer.close()


def test_long_circuit_jump_changes_chunk_and_export_is_vector(qt_app, tmp_path):
    config = create_example_config('ising')
    config = replace(config, protocol=replace(config.protocol, trotter_steps=20, save_snapshots=False), shots=8)
    record = run_experiment(config)
    before = json.dumps(record.result.metadata, sort_keys=True)
    viewer = CircuitInspector()
    try:
        viewer.show_experiment(record)
        assert len(viewer.operations) > 100
        viewer.jump.setValue(101)
        assert viewer.chunk.value() == 2
        assert viewer.selected == 100
        assert viewer.canvas.offset == 100
        assert 'não salvou snapshots' in viewer.details.text()
        path = tmp_path / 'consulta.svg'
        viewer.canvas.export_svg(path)
        svg = path.read_text(encoding='utf-8')
        assert '<svg' in svg and '<image' not in svg
        assert json.dumps(record.result.metadata, sort_keys=True) == before
    finally:
        viewer.close()


@pytest.mark.parametrize('font_size', [15, 24])
def test_wrapped_controls_do_not_overlap_diagram_in_small_history(window, qt_app, source, font_size):
    page = window.page_history
    page.load([source])
    page.set_detail(source)
    page.detail_tabs.setCurrentWidget(page.circuit)
    page.expand_details.setChecked(True)
    window._show_page('history')
    apply_appearance(window, 'dark', font_size)
    window.resize(1024, 768)
    for _ in range(8):
        qt_app.processEvents()
    viewer = page.circuit
    assert viewer.controls.height() >= viewer.controls.layout().heightForWidth(viewer.controls.width())
    assert viewer.canvas.geometry().top() >= viewer.controls.geometry().bottom()
    assert viewer.range_label.geometry().top() >= viewer.canvas.geometry().bottom()
    assert viewer.canvas.height() >= viewer.canvas.minimumHeight()
    assert page._scroll.horizontalScrollBar().maximum() == 0
