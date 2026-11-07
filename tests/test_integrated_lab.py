"""Fluxos reais no mesmo laboratório, com uma única execução e rascunhos preservados."""
from dataclasses import replace

from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QMessageBox

from core.examples import create_example_config
from core.simulation import run_experiment
from core.types import ExperimentConfig, SystemConfig, SimulationProtocol, NoiseConfig
from core.circuit_document import CircuitDocument, CircuitGate
from gui.controllers.appearance import apply_appearance
from tests.qt_helpers import execute, wait_until


def test_navigation_uses_existing_pages_and_keeps_independent_drafts(window, qt_app):
    workspace = window.page_workspace
    panel = window.page_simulation.config_panel
    panel.spin_J.setValue(.123456789012345)
    window.page_circuit.editor._bell()
    config, document = panel.get_config(), window.page_circuit.editor.document
    for index, key in enumerate(workspace.KEYS):
        window._show_page(key)
        assert window.stack.currentWidget() is workspace
        assert workspace.tabs.currentWidget() is window.pages[key]
        assert window.is_page_active(key)
        assert panel.get_config() == config
        assert window.page_circuit.editor.document == document
    workspace.tabs.setCurrentIndex(0)
    assert window._current_page == 'simulation'
    window._show_page('history')
    assert window.stack.currentWidget() is window.page_history
    window._show_page('circuit')
    assert workspace.tabs.currentWidget() is window.page_circuit
    assert window.page_circuit.editor.document == document


def test_simulate_review_and_annotate_in_the_same_workspace(window, qt_app):
    config = replace(create_example_config('bell'), shots=32)
    window._show_page('simulation')
    window.page_simulation.config_panel.load_config(config)
    workspace = window.stack.currentWidget()
    source = execute(window)
    assert window.stack.currentWidget() is workspace
    assert window.is_page_active('results')
    assert source.config == config
    assert sum(source.result.counts.values()) == 32
    assert window.page_results._experiment is source
    assert source.result.fidelity > .999999
    window._show_page('bloch')
    assert len(window.page_bloch.precomputed_bloch) == len(source.result.states)
    window._show_page('library')
    assert window.page_library.identifier == source.id
    window.page_library.notes.setPlainText('Interpretação da mesma execução')
    window._show_page('simulation')
    window._show_page('library')
    assert window.page_library.notes.toPlainText() == 'Interpretação da mesma execução'
    assert window._current_experiment is source
    assert window.repository.load(source.id).config == config


def test_keyboard_executes_the_visible_editor_not_the_hamiltonian_form(window, qt_app):
    panel = window.page_simulation.config_panel
    form = panel.get_config()
    editor = window.page_circuit.editor
    editor._bell()
    editor.shots.setValue(32)
    editor.seed.setText('42')
    editor.noise.setChecked(False)
    window._show_page('circuit')
    window.page_circuit.tabs.setCurrentWidget(editor)
    window.activateWindow()
    editor.canvas.setFocus()
    qt_app.processEvents()
    QTest.keyClick(window, Qt.Key_Return, Qt.ControlModifier)
    assert window._current_worker is not None
    assert not window.page_workspace.templates_button.isEnabled()
    wait_until(lambda: window._current_worker is None)
    assert window.is_page_active('results')
    assert window._current_experiment.config.circuit == editor.document
    assert window._current_experiment.config.shots == 32
    assert panel.get_config() == form
    assert window.page_workspace.templates_button.isEnabled()


def test_saved_configuration_menu_uses_existing_draft_protection(window, monkeypatch):
    panel = window.page_simulation.config_panel
    panel.load_config(create_example_config('thermal-ising'))
    saved = panel.get_config()
    window._save_template('Relaxação & comparação')
    panel.spin_J.setValue(.4321)
    edited = panel.get_config()
    action = window.page_workspace.templates_menu.actions()[0]
    monkeypatch.setattr(QMessageBox, 'question', lambda *args: QMessageBox.No)
    action.trigger()
    assert panel.get_config() == edited
    monkeypatch.setattr(QMessageBox, 'question', lambda *args: QMessageBox.Yes)
    action.trigger()
    assert panel.get_config() == saved
    assert window.is_page_active('simulation')
    assert window._current_worker is None
    window.page_workspace.templates_menu.actions()[-1].trigger()
    assert window.is_page_active('library')
    assert window.page_library.tabs.currentWidget() is window.page_library.templates_group


def test_recent_execution_menu_preserves_identity_and_notebook_link(window):
    panel = window.page_simulation.config_panel
    panel.load_config(replace(create_example_config('bell'), shots=16))
    source = execute(window)
    action = window.page_workspace.recent_menu.actions()[0]
    action.trigger()
    assert window.is_page_active('results')
    assert window._current_experiment.id == source.id
    assert window.page_library.identifier == source.id
    assert source.id not in window.page_workspace.selected_label.text()
    assert window.repository.load(source.id).result.counts == source.result.counts


def test_study_can_select_its_source_without_leaving_the_study(window):
    panel = window.page_simulation.config_panel
    panel.load_config(replace(create_example_config('bell'), shots=16))
    first = execute(window)
    panel.input_seed.setText('43')
    second = execute(window)
    assert second.id != first.id
    window._show_page('analysis')
    action = next(action for action in window.page_analysis.source_button.menu().actions() if action.data() == first.id)
    action.trigger()
    assert window.is_page_active('analysis')
    assert window._current_experiment.id == first.id
    assert window.page_library.identifier == first.id


def test_opening_circuit_results_preserves_form_identity_and_both_drafts(window, monkeypatch):
    panel = window.page_simulation.config_panel
    panel.spin_J.setValue(.123456789012345)
    window.page_simulation.experiment_name.setText('Dinâmica Ising')
    window.page_simulation.experiment_description.setText('Hipótese do Hamiltoniano')
    window._pending_example_id = 'ising'
    form, baseline = panel.get_config(), window.drafts.identity_baseline
    editor = window.page_circuit.editor
    editor.replace_document(CircuitDocument(1, (CircuitGate('ry',(0,),(.234567891234567,)),)))
    document = editor.document
    source = run_experiment(ExperimentConfig(SystemConfig(2,J=0,h=0),SimulationProtocol(2,2,True),
        NoiseConfig(False),16,42,CircuitDocument(2,(CircuitGate('h',(0,)),CircuitGate('cx',(0,1))))))
    window.repository.save(source)
    window._workspace_library().annotate(source.id, '', '', [], title='Bell do editor', description='Preparação H/CX')
    monkeypatch.setattr(QMessageBox, 'question', lambda *args: QMessageBox.No)
    window._open_experiment(source.id)
    assert window._current_experiment.id == source.id
    assert window.is_page_active('results')
    assert panel.get_config() == form
    assert window.page_simulation.experiment_name.text() == 'Dinâmica Ising'
    assert window.page_simulation.experiment_description.text() == 'Hipótese do Hamiltoniano'
    assert window.drafts.identity_baseline == baseline and window.drafts.identity_dirty
    assert window._pending_example_id == 'ising'
    assert editor.document == document


def test_loaded_result_does_not_add_global_configuration_scroll_at_large_font(window, qt_app):
    panel = window.page_simulation.config_panel
    panel.load_config(replace(create_example_config('bell'),shots=16))
    execute(window)
    window.page_library.run_title.setText('A')
    window._annotate_current('', '', [])
    try:
        apply_appearance(window,'light',24)
        window.resize(1024,768)
        for _ in range(3):
            window._show_page('results')
            window._show_page('simulation')
            for _ in range(5):
                qt_app.processEvents()
            assert window.page_simulation._scroll.verticalScrollBar().maximum() == 0
        assert window.page_simulation.examples_button.isVisible()
        assert window.page_simulation.btn_run.isVisible()
    finally:
        apply_appearance(window)
