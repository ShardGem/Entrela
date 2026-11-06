"""User workflows remain usable through responsive layout and model changes."""
from dataclasses import replace
import pytest
from PySide6.QtCore import QPoint
from PySide6.QtWidgets import QMessageBox

from core.examples import create_example_config
from core.simulation import run_experiment
from gui.controllers.appearance import apply_appearance
from gui.main_window import MainWindow
from gui.pages.simulation import SimulationPage


def test_applicable_parameters_preserve_precision_and_do_not_execute(qt_app):
    page = SimulationPage()
    panel = page.config_panel
    panel.load_config(create_example_config('thermal-ising'))
    panel.spin_t1.setValue(73.1234567890123)
    panel.spin_p1.setValue(.01234567890123)
    panel.spin_h.setValue(.34567890123456)
    panel.set_section('noise')
    panel.resize(900, 700)
    page.show()
    requested = []
    page.run_requested.connect(requested.append)
    try:
        expected = panel.get_config()
        assert not panel.spin_t1.isHidden()
        assert panel.spin_p1.isHidden()
        panel.combo_modelo.setCurrentIndex(0)
        assert panel.spin_t1.isHidden()
        assert not panel.spin_p1.isHidden()
        panel.check_ruido.setChecked(False)
        assert panel.spin_p1.isHidden()
        panel.check_ruido.setChecked(True)
        panel.combo_modelo.setCurrentIndex(1)
        assert panel.get_config() == expected
        panel.set_section('hamiltonian')
        panel.combo_ham.setCurrentText('XY')
        assert panel.spin_h.isHidden()
        assert 'h=' not in page._summary_rows['sistema'].text()
        panel.combo_ham.setCurrentText('Ising')
        assert panel.get_config() == expected
        assert requested == []
    finally:
        page.close()


def test_invalid_configuration_disables_execution_and_reveals_correction(qt_app):
    page = SimulationPage()
    page.resize(780, 720)
    page.show()
    qt_app.processEvents()
    panel = page.config_panel
    panel.load_config(create_example_config('bell'))
    panel.spin_qubits.setValue(3)
    page.compact_tabs.setCurrentWidget(page.summary_scroll)
    requested = []
    page.run_requested.connect(requested.append)
    try:
        assert not page.btn_run.isEnabled()
        assert 'Bell' in page.configuration_feedback.text()
        page.btn_run.click()
        assert requested == []
        page.revise_button.click()
        assert page.compact_tabs.currentWidget() is panel
        assert panel.current_section == 'system'
        assert panel.sections['system'].content.isVisible()
        # A guided section cannot accidentally be collapsed by its heading.
        panel.sections['system'].header.click()
        assert panel.sections['system'].content.isVisible()
        panel.spin_qubits.setValue(2)
        assert page.btn_run.isEnabled()
        page.btn_run.click()
        assert len(requested) == 1
    finally:
        page.close()


@pytest.mark.parametrize('font_size', [15, 24])
def test_resize_and_font_changes_preserve_form_and_visible_execution(window, qt_app, font_size):
    page = window.page_simulation
    panel = page.config_panel
    panel.load_config(create_example_config('thermal-ising'))
    panel.spin_J.setValue(.123456789012345)
    expected = panel.get_config()
    window._show_page('simulation')
    try:
        apply_appearance(window, 'dark', font_size)
        for width, height in [(1024, 768), (1920, 1080), (1024, 768), (1920, 1080)]:
            window.resize(width, height)
            for _ in range(4):
                qt_app.processEvents()
            assert page.config_panel is panel
            assert panel.get_config() == expected
            assert panel.isVisible()
            assert panel.width() > 250
            if not page._compact:
                assert page.summary_scroll.isVisible()
                assert page.summary_scroll.width() > 250
            assert page.btn_run.isVisible()
            corner = page.btn_run.mapTo(window, QPoint(page.btn_run.width()-1, page.btn_run.height()-1))
            assert window.rect().contains(corner)
            assert page._scroll.horizontalScrollBar().maximum() == 0
            assert page._scroll.verticalScrollBar().maximum() == 0
    finally:
        apply_appearance(window)


def test_example_menu_respects_draft_protection_and_never_runs(window, monkeypatch):
    page = window.page_simulation
    panel = page.config_panel
    panel.spin_J.setValue(.321)
    expected = panel.get_config()
    action = next(action for action in page.examples_button.menu().actions() if 'Bell' in action.text())
    monkeypatch.setattr(QMessageBox, 'question', lambda *args: QMessageBox.Cancel)
    action.trigger()
    assert panel.get_config() == expected
    monkeypatch.setattr(QMessageBox, 'question', lambda *args: QMessageBox.Yes)
    action.trigger()
    assert panel.get_config() == create_example_config('bell')
    assert window._current_worker is None
    assert not window.repository.list_summaries()


def test_expanded_sections_and_presentation_survive_restart(window, qt_app):
    page = window.page_simulation
    panel = page.config_panel
    panel.load_config(create_example_config('thermal-ising'))
    panel.set_mode('advanced')
    panel.set_section('noise')
    panel.sections['system'].set_expanded(False, animate=False)
    panel.sections['execution'].set_expanded(True, animate=False)
    page.experiment_description.setText('Hipótese ainda em edição')
    page.description_toggle.setChecked(False)
    page.science.set_expanded(True, animate=False)
    expected = panel.get_config()
    window.close()
    other = MainWindow(window.repository, window.settings)
    try:
        restored = other.page_simulation
        assert restored.config_panel.get_config() == expected
        assert restored.config_panel.current_mode == 'advanced'
        assert restored.config_panel.current_section == 'noise'
        assert restored.config_panel.sections['noise'].is_expanded
        assert restored.config_panel.sections['execution'].is_expanded
        assert not restored.config_panel.sections['system'].is_expanded
        assert restored.experiment_description.text() == 'Hipótese ainda em edição'
        assert not restored.description_toggle.isChecked()
        assert restored.science.is_expanded
        assert other._current_worker is None
    finally:
        other.close()


def test_result_actions_use_available_width_and_stay_inside_header(window, qt_app):
    page = window.page_results
    window._show_page('results')
    try:
        for size, width in [(15, 1440), (24, 920)]:
            apply_appearance(window, 'dark', size)
            window.resize(width, 900)
            for _ in range(4):
                qt_app.processEvents()
            buttons = [item.widget() for item in page._actions_slot.items]
            for index, button in enumerate(buttons):
                assert page._header.rect().contains(button.geometry())
                assert all(not button.geometry().intersects(other.geometry()) for other in buttons[index+1:])
            if size == 15:
                assert len({button.y() for button in buttons}) == 1
    finally:
        apply_appearance(window)


def test_three_dimensional_and_circuit_controls_fit_large_text(window, qt_app):
    record = run_experiment(replace(create_example_config('bell'), shots=16))
    window._display_experiment(record)
    circuit = window.page_circuit
    circuit.show_experiment(record, 'Bell · controle da pesquisa')
    assert 'Bell · controle da pesquisa' in circuit.context.text()
    assert record.id not in circuit.context.text()
    assert record.id in circuit.context.toolTip()
    try:
        apply_appearance(window, 'light', 24)
        window.resize(1024, 768)
        for key in ('bloch', 'circuit'):
            window._show_page(key)
            for _ in range(4):
                qt_app.processEvents()
            assert window.pages[key]._scroll.horizontalScrollBar().maximum() == 0
        circuit.tabs.setCurrentWidget(circuit.editor)
        for _ in range(4):
            qt_app.processEvents()
        assert circuit._scroll.horizontalScrollBar().maximum() == 0
        assert circuit.experiment is record
    finally:
        apply_appearance(window)


def test_reduced_motion_collapses_parameters_without_changing_configuration(window, qt_app):
    window._show_page('simulation')
    panel = window.page_simulation.config_panel
    panel.set_mode('advanced')
    panel.set_section('noise')
    expected = panel.get_config()
    try:
        apply_appearance(window, reduce_motion=True)
        section = panel.sections['noise']
        section.header.click()
        assert not section.is_expanded
        assert not section.content.isVisible()
        assert panel.get_config() == expected
        section.header.click()
        assert section.content.isVisible()
        assert panel.get_config() == expected
    finally:
        apply_appearance(window)
