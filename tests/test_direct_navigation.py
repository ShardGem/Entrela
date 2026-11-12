"""Todas as funções permanecem visíveis e abrem o destino anunciado."""
from dataclasses import replace
from PySide6.QtTest import QTest
from PySide6.QtCore import Qt
from core.examples import create_example_config
from core.simulation import run_experiment
from gui.navigation import NAV_LABELS, NAV_ACTIONS


def settle(app):
    for _ in range(8):
        app.processEvents()


def test_every_existing_page_has_a_named_direct_access(window, qt_app):
    sidebar = window.sidebar
    assert set(window.pages) <= set(sidebar.buttons)
    assert set(sidebar.group_bodies) == {'lab', 'research', 'records', 'learning'}
    assert all(not group.isHidden() for group in sidebar.group_bodies.values())
    for key in window.pages:
        sidebar.buttons[key].click()
        settle(qt_app)
        assert window.is_page_active(key), key
        assert window.topbar.title.text() == NAV_LABELS[key]
        assert sidebar.buttons[key].isChecked()
        assert sum(button.isChecked() for button in sidebar.buttons.values()) == 1
        assert sidebar.buttons[key].accessibleName() == NAV_LABELS[key]
        assert sidebar.buttons[key].accessibleDescription()
        assert window._current_worker is None
    assert not sidebar.scroll.isAncestorOf(sidebar.buttons['dashboard'])
    assert not sidebar.scroll.isAncestorOf(sidebar.buttons['settings'])


def test_clicking_a_function_does_not_resume_a_different_function(window, qt_app):
    window._show_page('comparison')
    window.sidebar.buttons['analysis'].click()
    assert window.is_page_active('analysis')
    window.sidebar.buttons['examples'].click()
    window.sidebar.buttons['docs'].click()
    assert window.is_page_active('docs')
    assert all(section.selector.isHidden() for section in window.section_workspaces.values())


def test_editor_entry_always_opens_editor_and_inspection_belongs_to_results(window, qt_app):
    window.page_workspace._apply_route('circuit:inspect')
    window._show_page('circuit')
    assert window.sidebar.buttons['results'].isChecked()
    assert not window.sidebar.buttons['circuit'].isChecked()
    assert window.topbar.title.text() == 'Circuito executado'
    window.sidebar.buttons['circuit'].click()
    assert window.page_circuit.tabs.currentWidget() is window.page_circuit.editor
    assert window.page_workspace._route == 'circuit:edit'
    assert window.sidebar.buttons['circuit'].isChecked()
    assert window.topbar.title.text() == 'Editor de circuitos'


def test_named_navigation_preserves_the_selected_run_and_both_drafts(window, qt_app):
    source = run_experiment(replace(create_example_config('bell'), shots=16))
    window._current_experiment = source
    window._display_experiment(source)
    window.page_circuit.editor._bell()
    window.page_simulation.config_panel.spin_J.setValue(.1234567890123)
    window.page_library.notes.setPlainText('Anotação em andamento')
    config = window.page_simulation.config_panel.get_config()
    circuit = window.page_circuit.editor.document
    for key, button in window.sidebar.buttons.items():
        if key in NAV_ACTIONS:
            continue
        button.click()
        settle(qt_app)
        assert window._current_experiment is source
        assert window.page_simulation.config_panel.get_config() == config
        assert window.page_circuit.editor.document == circuit
        assert window.page_library.notes.toPlainText() == 'Anotação em andamento'
    assert window._current_worker is None


def test_saved_configurations_is_an_action_and_keeps_page_selection(window, qt_app):
    window.sidebar.buttons['simulation'].click()
    window.page_simulation.experiment_name.setText('Rascunho preservado')
    window.sidebar.buttons['configurations'].click()
    settle(qt_app)
    assert window.configuration_dialog.isVisible()
    assert window.is_page_active('simulation')
    assert window.sidebar.buttons['simulation'].isChecked()
    assert not window.sidebar.buttons['configurations'].isChecked()
    assert window.page_simulation.experiment_name.text() == 'Rascunho preservado'
    window.configuration_dialog.close()


def test_keyboard_opens_named_destination_without_folding_its_group(window, qt_app):
    button = window.sidebar.buttons['mitigation']
    button.setFocus()
    QTest.keyClick(button, Qt.Key_Space)
    settle(qt_app)
    assert window.is_page_active('mitigation')
    assert not window.sidebar.group_bodies['research'].isHidden()
    window.sidebar.buttons['docs'].setFocus()
    QTest.keyClick(window.sidebar.buttons['docs'], Qt.Key_Space)
    settle(qt_app)
    assert window.is_page_active('docs')
    assert window.sidebar.scroll.viewport().rect().contains(window.sidebar.buttons['docs'].mapTo(window.sidebar.scroll.viewport(), window.sidebar.buttons['docs'].rect().center()))
    window.sidebar.buttons['settings'].setFocus()
    QTest.keyClick(window.sidebar.buttons['settings'], Qt.Key_Space)
    assert window.is_page_active('settings')
