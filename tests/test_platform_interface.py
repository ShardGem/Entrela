"""Fluxos da interface de plataforma e proveniência do resultado no editor."""
from dataclasses import replace
import numpy as np
from PySide6.QtGui import QFontInfo
from core.circuit_document import CircuitDocument, CircuitGate
from core.examples import create_example_config
from core.simulation import run_experiment
from gui.controllers.appearance import apply_appearance
from gui.theme import PALETTE
from tests.test_visual_profiles import _contrast


def settle(app):
    for _ in range(10):
        app.processEvents()


def circuit_source(window):
    document = CircuitDocument(2, (CircuitGate('h', (0,)), CircuitGate('cx', (0, 1))))
    base = create_example_config('bell')
    source = run_experiment(replace(base, circuit=document, shots=32,
                                    protocol=replace(base.protocol, total_time=2., trotter_steps=2)))
    window.repository.save(source)
    window._current_experiment = source
    window._display_experiment(source)
    return source


def test_sidebar_keeps_navigation_visible_and_header_shows_the_page(window, qt_app):
    window.resize(1920, 1080)
    window.navigation.open_page('circuit')
    settle(qt_app)
    workspace = window.topbar.parentWidget()
    assert workspace.objectName() == "Workbench"
    assert workspace.geometry().left() > window.sidebar.geometry().right()
    assert window.centralWidget().rect().contains(workspace.geometry())
    assert window.topbar.title.text() == 'Editor de circuitos'
    assert window.sidebar.brand_box.isVisible()
    assert window.sidebar._expanded_groups == {key for key, *_ in window.sidebar.GROUPS}
    assert 'Inter' == QFontInfo(window.topbar.title.font()).family()
    assert window.sidebar.search.accessibleName() == 'Buscar'
    assert window.sidebar.buttons['settings'].accessibleName() == 'Preferências'


def test_primary_action_contrast_and_customization_work_in_each_theme(window):
    for theme in ('dark', 'light', 'navy'):
        apply_appearance(window, theme)
        assert _contrast(PALETTE.action_bg, PALETTE.action_on) >= 4.5
        assert _contrast(PALETTE.action_hover, PALETTE.action_on) >= 4.5
        assert _contrast(PALETTE.action_pressed, PALETTE.action_on) >= 4.5
        apply_appearance(window, theme, accent='violet')
        assert _contrast(PALETTE.action_bg, PALETTE.action_on) >= 4.5
        assert PALETTE.action_bg == PALETTE.primary


def test_editor_evidence_uses_recorded_counts_and_preserves_state_when_draft_changes(window, qt_app):
    source = circuit_source(window)
    window.resize(1920, 1080)
    window.navigation.open_page('circuit')
    editor = window.page_circuit.editor
    editor.replace_document(source.config.circuit)
    settle(qt_app)
    panel = editor.evidence
    assert not panel.isVisible()
    editor.evidence_toggle.click()
    settle(qt_app)
    assert panel.experiment is source
    assert panel.data_view.isVisible()
    assert panel.open_results.isVisible()
    viewport = window.page_circuit._scroll.viewport()
    assert viewport.rect().contains(panel.mapTo(viewport, panel.rect().bottomRight()))
    for value in panel.values:
        assert panel.data_view.rect().contains(value.mapTo(panel.data_view, value.rect().bottomRight()))
    assert [bar.get_height() for bar in panel.plot.fig.axes[0].patches] == [source.result.counts[k] / 32 for k in sorted(source.result.counts)]
    assert panel.values[0].toolTip() == str(source.result.fidelity)
    assert panel.values[1].toolTip() == str(source.result.purity)
    state = source.result.final_state.data.copy()
    counts = dict(source.result.counts)
    editor._add('x')
    assert 'alterado' in panel.change_notice.text()
    assert panel.experiment is source
    assert source.result.counts == counts
    np.testing.assert_array_equal(source.result.final_state.data, state)
    assert window._current_worker is None
    panel.open_results.click()
    assert window.is_page_active('results')
    assert window._current_experiment is source


def test_hamiltonian_source_does_not_appear_as_a_free_circuit_result(window, qt_app):
    source = circuit_source(window)
    hamiltonian = run_experiment(replace(create_example_config('bell'), shots=32))
    window._current_experiment = hamiltonian
    window._display_experiment(hamiltonian)
    window.navigation.open_page('circuit')
    settle(qt_app)
    window.page_circuit.editor.evidence_toggle.click()
    settle(qt_app)
    panel = window.page_circuit.editor.evidence
    assert panel.experiment is None
    assert panel.empty.isVisible()
    assert not panel.data_view.isVisible()
    assert not panel.open_results.isVisible()
    assert source.config.circuit is not None and hamiltonian.config.circuit is None


def test_edit_menu_keeps_clipboard_operations_and_undo(window, qt_app):
    window.navigation.open_page('circuit')
    editor = window.page_circuit.editor
    assert not editor.apply_gate_button.isEnabled()
    editor._bell()
    editor._select(0)
    original = editor.document
    editor.edit_menu.actions()[0].trigger()
    editor.edit_menu.actions()[2].trigger()
    assert len(editor.document.gates) == len(original.gates) + 1
    editor.undo_stack.undo()
    assert editor.document == original
    assert editor.apply_gate_button.isEnabled()
    qt_app.clipboard().clear()


def test_enlarged_text_keeps_editor_execution_and_opt_in_evidence_reachable(window, qt_app):
    circuit_source(window)
    window.page_settings.apply_values({'font_size': 24})
    window._apply_preferences()
    window.resize(1024, 768)
    window.navigation.open_page('circuit')
    settle(qt_app)
    editor = window.page_circuit.editor
    assert editor._compact_scene
    assert not editor.evidence.isVisible()
    assert editor.run.isVisible()
    assert window.page_circuit._scroll.horizontalScrollBar().maximum() == 0
    editor.scene_compact_tabs.setCurrentWidget(editor.inspector_tabs)
    editor.evidence_toggle.click()
    settle(qt_app)
    assert editor.evidence.isVisible()
    assert editor.scene_compact_tabs.currentWidget() is editor.operation_views
    assert window._current_worker is None
