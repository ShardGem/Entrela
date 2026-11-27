"""A introdução é dispensável, retomável e não substitui evidência científica."""

from dataclasses import replace

import pytest
from PySide6.QtCore import QSettings, Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QMessageBox

from core.examples import create_example_config
from core.simulation import run_experiment
from gui.controllers.appearance import apply_appearance
from tests.qt_helpers import wait_until


@pytest.fixture(scope='module')
def bell_record():
    return run_experiment(replace(create_example_config('bell'), shots=32, seed=29))


def settle(qt_app):
    for _ in range(12):
        qt_app.processEvents()


@pytest.mark.parametrize('dismiss', ['skip', 'escape', 'close'])
def test_first_offer_can_be_dismissed_without_altering_work(window, qt_app, dismiss):
    window.projects.open_project('Minha investigação')
    window._show_page('simulation')
    field = window.page_simulation.config_panel.spin_J
    field.setValue(.654321)
    original = window.page_simulation.config_panel.get_config()
    window.activateWindow()
    focus_target = window.sidebar.search
    focus_target.setFocus()
    settle(qt_app)
    assert QApplication.focusWidget() is focus_target
    window.onboarding.offer_on_startup()
    wait_until(lambda: window.onboarding.dialog is not None)
    dialog = window.onboarding.dialog
    assert dialog.isVisible()
    assert not window.settings.value('onboarding/welcome_seen', False, type=bool)
    if dismiss == 'skip':
        dialog.skip.click()
    elif dismiss == 'escape':
        QTest.keyClick(dialog, Qt.Key_Escape)
    else:
        dialog.close()
    settle(qt_app)
    assert window.onboarding.dialog is None
    assert window.settings.value('onboarding/welcome_seen', False, type=bool)
    assert not window.settings.value('onboarding/show_on_startup', True, type=bool)
    assert window.page_simulation.config_panel.get_config() == original
    assert window.projects.project == 'Minha investigação'
    assert window._current_worker is None
    assert window._current_experiment is None
    assert not window.tutorial.started
    assert QApplication.focusWidget() is focus_target
    window.onboarding.offer_on_startup()
    settle(qt_app)
    assert window.onboarding.dialog is None


def test_welcome_waits_for_the_real_window_and_remembers_repeat_choice(window, qt_app):
    window.hide()
    window.onboarding.offer_on_startup()
    settle(qt_app)
    assert window.onboarding.dialog is None
    assert not window.settings.contains('onboarding/welcome_seen')
    window.show()
    wait_until(lambda: window.onboarding.dialog is not None)
    window.onboarding.dialog.repeat.setChecked(True)
    window.onboarding.dialog.skip.click()
    window.settings.sync()
    restored_settings = QSettings(window.settings.fileName(), QSettings.IniFormat)
    assert restored_settings.value('onboarding/welcome_seen', False, type=bool)
    assert restored_settings.value('onboarding/show_on_startup', False, type=bool)
    window.onboarding.offer_on_startup()
    wait_until(lambda: window.onboarding.dialog is not None)
    window.onboarding.dialog.repeat.setChecked(False)
    window.onboarding.dialog.skip.click()


@pytest.mark.parametrize('choice', ['guide', 'examples'])
def test_welcome_paths_open_learning_without_creating_an_experiment(window, qt_app, choice):
    original = window.page_simulation.config_panel.get_config()
    window.onboarding.show_welcome()
    window.onboarding.dialog.actions[choice].click()
    settle(qt_app)
    assert window.is_page_active('docs' if choice == 'guide' else 'examples')
    if choice == 'guide':
        assert window.page_docs.sections.currentWidget() is window.page_docs.guide
    assert window.page_simulation.config_panel.get_config() == original
    assert not window.projects.store.works()
    assert not window.repository.list_all()
    assert window._current_worker is None


def test_welcome_practice_uses_the_existing_tutorial_and_its_draft_guard(window, monkeypatch):
    field = window.page_simulation.config_panel.spin_J
    field.setValue(.4321)
    original = window.page_simulation.config_panel.get_config()
    monkeypatch.setattr(QMessageBox, 'question', lambda *_args, **_kwargs: QMessageBox.No)
    window.onboarding.show_welcome()
    window.onboarding.dialog.actions['tutorial'].click()
    assert window.page_simulation.config_panel.get_config() == original
    assert not window.tutorial.started
    assert window._current_worker is None
    monkeypatch.setattr(QMessageBox, 'question', lambda *_args, **_kwargs: QMessageBox.Yes)
    window.onboarding.show_welcome()
    window.onboarding.dialog.actions['tutorial'].click()
    assert window.tutorial.active and window.tutorial.step == 0
    assert not window.tutorial.ready()
    assert window.is_page_active('simulation')
    assert window._current_worker is None


def test_guide_progress_reopens_without_changing_bell_progress_or_config(window, qt_app):
    window.settings.setValue('tutorial/bell/step', 3)
    window.settings.setValue('tutorial/bell/run_id', 'registro-anterior')
    original = window.page_simulation.config_panel.get_config()
    window.page_dashboard.guide_button.click()
    guide = window.page_docs.guide
    guide.next.click()
    guide.next.click()
    window._show_page('simulation')
    window._command('getting-started')
    assert guide.step == 2
    guide.next.click()
    guide.next.click()
    assert guide.completed
    window.settings.sync()
    restored_settings = QSettings(window.settings.fileName(), QSettings.IniFormat)
    assert restored_settings.value('onboarding/guide_step', -1, type=int) == 3
    assert restored_settings.value('onboarding/guide_completed', False, type=bool)
    assert window.settings.value('tutorial/bell/step', -1, type=int) == 3
    assert window.settings.value('tutorial/bell/run_id') == 'registro-anterior'
    assert window.page_simulation.config_panel.get_config() == original
    assert not window.repository.list_all()
    guide.next.click()
    assert guide.step == 0 and not guide.completed


def test_guide_uses_actual_result_identity_and_does_not_replace_the_draft(window, bell_record):
    window.onboarding.open_guide()
    guide = window.page_docs.guide
    guide.select_step(2)
    assert not guide.route_buttons['results'].isEnabled()
    assert not guide.route_buttons['bloch'].isEnabled()
    original = window.page_simulation.config_panel.get_config()
    window._current_experiment = bell_record
    window._display_experiment(bell_record)
    assert guide.route_buttons['results'].isEnabled()
    assert window._experiment_name(bell_record) in guide.result_hint.text()
    for destination in ('results', 'bloch'):
        window.onboarding.open_guide()
        guide.route_buttons[destination].click()
        assert window.is_page_active(destination)
        assert window._current_experiment is bell_record
        assert window.page_simulation.config_panel.get_config() == original
    assert window._current_worker is None


def test_search_reopens_guide_and_an_already_selected_concept(window):
    window._open_commands()
    palette = window.command_palette
    palette.search.setText('primeiros passos')
    guide_item = next(palette.list.item(i) for i in range(palette.list.count())
                      if palette.list.item(i).data(Qt.UserRole) == 'getting-started')
    palette.list.setCurrentItem(guide_item)
    palette._activate()
    assert window.page_docs.sections.currentWidget() is window.page_docs.guide
    window._command('concept:qubit')
    assert window.page_docs.sections.currentWidget() is window.page_docs.splitter
    window.onboarding.open_guide()
    window._command('concept:qubit')
    assert window.page_docs.sections.currentWidget() is window.page_docs.splitter
    assert window.page_docs.concept_list.currentItem().data(Qt.UserRole) == 'qubit'


def test_a_new_window_restores_the_guide_and_does_not_repeat_dismissed_welcome(window, qt_app):
    from gui.main_window import MainWindow

    window.onboarding.show_welcome()
    window.onboarding.dialog.skip.click()
    window.onboarding.open_guide()
    window.page_docs.guide.select_step(3)
    window.page_docs.guide.advance()
    window.close()
    reopened = MainWindow(window.repository, QSettings(window.settings.fileName(), QSettings.IniFormat))
    try:
        reopened.onboarding.offer_on_startup()
        reopened.show()
        settle(qt_app)
        assert reopened.onboarding.dialog is None
        assert reopened.page_docs.guide.step == 3
        assert reopened.page_docs.guide.completed
        assert not reopened.tutorial.started
    finally:
        reopened.close()
        reopened.deleteLater()


@pytest.mark.parametrize('theme', ['dark', 'light', 'navy'])
@pytest.mark.parametrize('size,font_size', [((1440, 900), 15), ((1024, 768), 24)])
def test_guide_and_welcome_keep_navigation_reachable_at_larger_text(window, qt_app, theme, size, font_size):
    window.resize(*size)
    apply_appearance(window, theme, font_size, reduce_motion=True)
    window.onboarding.open_guide()
    guide = window.page_docs.guide
    for index in range(4):
        guide.step_buttons.button(index).click()
        settle(qt_app)
        assert guide.scroll.horizontalScrollBar().maximum() == 0
        assert window.page_docs._scroll.horizontalScrollBar().maximum() == 0
        assert guide.next.visibleRegion().boundingRect().height() == guide.next.height()
        assert guide.next.accessibleName() or guide.next.text()
    window.onboarding.show_welcome()
    settle(qt_app)
    dialog = window.onboarding.dialog
    assert dialog.skip.visibleRegion().boundingRect().height() == dialog.skip.height()
    assert dialog.repeat.isVisible()
    assert dialog.actions['guide'].hasFocus()
    QTest.keyClick(dialog, Qt.Key_Escape)
    settle(qt_app)
    assert window.onboarding.dialog is None
