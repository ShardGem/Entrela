"""Recover real work and exercise the native focus/unfocus gestures."""
from dataclasses import replace
from types import SimpleNamespace
import json

import numpy as np
import pytest
from mpl_toolkits.mplot3d import proj3d
from PySide6.QtWidgets import QMessageBox
from qiskit.quantum_info import Statevector

from core.circuit_document import CircuitDocument, CircuitGate
from core.examples import create_example_config
from core.simulation import run_experiment
from data.drafts import DraftStore
from gui.main_window import MainWindow
from gui.pages.bloch import BlochPage
from tests.qt_helpers import wait_until


def test_unfinished_circuit_and_invalid_inputs_survive_restart(window, qt_app):
    editor = window.page_circuit.editor
    document = CircuitDocument(2,(CircuitGate("rx",(0,),(.12345678912345678,)),))
    editor.replace_document(document)
    editor._select(0)
    editor.param_fields[0].setText("pi /")
    editor.phase.setText("pi +")
    editor.circuit_name.setText("Circuito em construção")
    editor.circuit_description.setText("Hipótese ainda em edição")
    editor.seed.setText("semente incompleta")
    page = window.page_simulation
    page.experiment_name.setText("Estudo a preparar")
    page.experiment_description.setText("Descrição ainda sem execução")
    page.config_panel.input_seed.setText("rascunho inválido")
    window.page_analysis.protocol.fields["question"].setText("Questão antes da primeira execução")
    assert window.close()
    other = MainWindow(window.repository,window.settings)
    try:
        recovered = other.page_circuit.editor
        assert recovered.document == document
        assert recovered.param_fields[0].text() == "pi /"
        assert recovered.phase.text() == "pi +"
        assert recovered.seed.text() == "semente incompleta"
        assert recovered.circuit_name.text() == "Circuito em construção"
        assert other.page_analysis.protocol.fields["question"].text() == "Questão antes da primeira execução"
        assert other.page_simulation.experiment_name.text() == "Estudo a preparar"
        assert other.page_simulation.experiment_description.text() == "Descrição ainda sem execução"
        assert other.page_simulation.config_panel.input_seed.text() == "rascunho inválido"
        with pytest.raises(ValueError):
            other.page_simulation.config_panel.get_config()
        assert not other.repository.list_summaries()
    finally:
        other.close()


def test_annotation_draft_survives_refresh_restart_and_explicit_commit(window):
    source = run_experiment(replace(create_example_config("bell"),shots=32))
    window.repository.save(source)
    before = window.repository._path(source.id).read_bytes()
    window._current_experiment = source
    window._display_experiment(source)
    window.page_library.notes.setPlainText("Interpretação ainda não confirmada")
    window.page_library.hypothesis.setPlainText("Hipótese em elaboração")
    window._refresh_library()
    assert window.page_library.notes.toPlainText() == "Interpretação ainda não confirmada"
    window.close()
    other = MainWindow(window.repository,window.settings)
    try:
        other._open_experiment(source.id)
        assert other.page_library.hypothesis.toPlainText() == "Hipótese em elaboração"
        other._annotate_current("TCC",other.page_library.notes.toPlainText(),["Bell"])
        assert source.id not in other.drafts.annotations
        assert other._current_annotation()["notes"] == "Interpretação ainda não confirmada"
        assert window.repository._path(source.id).read_bytes() == before
    finally:
        other.close()


def test_autosave_runs_before_close_and_falls_back_after_corruption(window):
    window.page_circuit.editor.circuit_name.setText("Protegido durante edição")
    wait_until(lambda: window.drafts.store.path.exists())
    payload = json.loads(window.drafts.store.path.read_text())
    assert payload["state"]["editor"]["name"] == "Protegido durante edição"
    store = window.drafts.store
    window.page_circuit.editor.circuit_name.setText("Versão posterior")
    assert window.drafts.flush()
    store.path.write_text("arquivo danificado",encoding="utf-8")
    assert store.load()["editor"]["name"] == "Protegido durante edição"
    assert "última cópia válida" in store.warning
    store.save(payload["state"])
    assert list(store.path.parent.glob("drafts-damaged-*.json"))


def test_close_can_be_cancelled_when_recovery_write_fails(window, monkeypatch):
    original = window.drafts.store.save
    monkeypatch.setattr(window.drafts.store,"save",lambda *args: (_ for _ in ()).throw(OSError("disco cheio")))
    monkeypatch.setattr(QMessageBox,"warning",lambda *args: QMessageBox.Cancel)
    window.page_circuit.editor.circuit_name.setText("Não perder")
    assert not window.close()
    assert "não protegidos" in window.drafts.indicator.text()
    monkeypatch.setattr(window.drafts.store,"save",original)
    assert window.drafts.flush()


@pytest.mark.parametrize("qubits",[4,5,6])
def test_four_qubits_per_row_and_unfocus_resets_every_control(qt_app,qubits):
    page = BlochPage()
    state = Statevector.from_int(0,2**qubits)
    page.load_statevectors([state],[0])
    page.resize(1400,900)
    page.show()
    qt_app.processEvents()
    try:
        canvas = page.canvas
        centers = np.asarray(canvas._sphere_centers)
        assert len(set(centers[:4,2])) == 1
        if qubits > 4:
            assert centers[4,2] != centers[3,2]
        for q in range(4):
            assert page._info_container.layout().getItemPosition(q)[:2] == (0,q)
        page.focus_combo.setCurrentIndex(page.focus_combo.findData(2))
        canvas.draw()
        x,y,_ = proj3d.proj_transform(*centers[2],canvas.ax.get_proj())
        px,py = canvas.ax.transData.transform((x,y))
        event = SimpleNamespace(inaxes=canvas.ax,x=px,y=py,button=1,modifiers=(),key=None)
        canvas._on_press(event)
        canvas._end_drag(event)
        assert canvas.focus == canvas.selected_qubit == -1
        assert page.focus_combo.currentData() == -1
        assert all(not panel.isHidden() for panel in page._qubit_panels)
        assert not page.focus_selected.isEnabled()
        page.focus_combo.setCurrentIndex(page.focus_combo.findData(3))
        page.focus_selected.click()
        assert canvas.focus == -1
        page.focus_combo.setCurrentIndex(page.focus_combo.findData(1))
        canvas.set_zoom(2)
        canvas.reset_camera()
        assert canvas.focus == -1 and canvas.zoom == 1
        assert page.focus_combo.currentData() == -1
        assert "selecionado" not in page.selection_label.text()
        np.testing.assert_array_equal(page.original_svs[0].data,state.data)
    finally:
        page.close()


def test_native_qt_click_unfocuses_the_isolated_sphere(qt_app):
    from PySide6.QtCore import QPoint,Qt
    from PySide6.QtTest import QTest
    page = BlochPage()
    page.load_statevectors([Statevector.from_label("0000")],[0])
    page.resize(1200,800)
    page.set_maximized(True)
    page.show()
    qt_app.processEvents()
    try:
        page.focus_combo.setCurrentIndex(page.focus_combo.findData(3))
        canvas = page.canvas
        canvas.draw()
        x,y,_ = proj3d.proj_transform(*canvas._sphere_centers[3],canvas.ax.get_proj())
        px,py = canvas.ax.transData.transform((x,y))
        ratio = canvas.device_pixel_ratio
        point = QPoint(round(px/ratio),round(canvas.height()-py/ratio))
        QTest.mouseClick(canvas,Qt.LeftButton,Qt.NoModifier,point)
        qt_app.processEvents()
        assert canvas.focus == -1 and page.focus_combo.currentData() == -1
        assert all(artist.get_visible() for artist in canvas._line_handles)
    finally:
        page.close()


def test_recovery_can_restore_replaced_named_circuit_after_restart(window):
    editor = window.page_circuit.editor
    document = CircuitDocument(2,(CircuitGate("h",(0,)),CircuitGate("cx",(0,1))))
    editor.replace_document(document)
    editor.circuit_name.setText("Bell a preservar")
    editor._new()
    assert not editor.document.gates
    assert window.close()
    other = MainWindow(window.repository,window.settings)
    try:
        index = next(index for index,item in enumerate(other.drafts.history) if item["editor"].get("name") == "Bell a preservar")
        other.drafts.restore_editor_checkpoint(index)
        assert other.page_circuit.editor.document == document
        assert other.page_circuit.editor.circuit_name.text() == "Bell a preservar"
        assert other.page_circuit.editor.recover_draft.isEnabled()
    finally:
        other.close()


def test_replacing_form_checks_name_and_description_even_when_parameters_unchanged(window,monkeypatch):
    page = window.page_simulation
    config = page.config_panel.get_config()
    page.experiment_name.setText("Planejamento independente")
    page.experiment_description.setText("Não substituir silenciosamente")
    monkeypatch.setattr(QMessageBox,"question",lambda *args: QMessageBox.No)
    window._load_example("bell")
    assert page.experiment_name.text() == "Planejamento independente"
    assert page.config_panel.get_config() == config
    monkeypatch.setattr(QMessageBox,"question",lambda *args: QMessageBox.Yes)
    window._load_example("bell")
    assert page.config_panel.get_config() == create_example_config("bell")
    assert not window.drafts.identity_dirty


def test_editor_execution_keeps_the_other_form_draft_independent(window):
    page = window.page_simulation
    page.experiment_name.setText("Outro estudo a planejar")
    page.experiment_description.setText("Descrição do formulário")
    config = page.config_panel.get_config()
    editor = window.page_circuit.editor
    editor.replace_document(CircuitDocument(2,(CircuitGate("h",(0,)),CircuitGate("cx",(0,1)))))
    editor.circuit_name.setText("Experimento do editor")
    editor.circuit_description.setText("Descrição do circuito")
    editor.shots.setValue(32)
    window._run_editor_circuit(editor.configuration())
    wait_until(lambda: window._current_worker is None)
    assert page.experiment_name.text() == "Outro estudo a planejar"
    assert page.experiment_description.text() == "Descrição do formulário"
    assert page.config_panel.get_config() == config
    assert window._current_annotation()["title"] == "Experimento do editor"
    assert window._current_annotation()["description"] == "Descrição do circuito"
    assert window.drafts.identity_dirty
