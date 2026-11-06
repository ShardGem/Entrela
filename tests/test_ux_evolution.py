"""Regressions for shared modes and explanatory configuration UI."""

from core.examples import create_example_config
from gui.pages.dashboard import DashboardPage
from gui.pages.simulation import SimulationPage
from gui.panels.config_panel import ConfigPanel


def test_advanced_has_no_inactive_steps_and_preserves_guided_position(qt_app):
    panel = ConfigPanel()
    panel.load_config(create_example_config("thermal-ising"))
    panel.spin_J.setValue(0.123456789012345)
    panel.set_section("noise")
    expected = panel.get_config()
    panel.resize(1000, 600)
    panel.show()
    try:
        assert panel.section_nav.isVisible()
        panel.set_mode("advanced")
        assert not panel.section_nav.isVisible()
        assert not panel.btn_back.isVisible()
        assert not panel.btn_next.isVisible()
        assert all(widget.isVisible() for widget in panel.sections.values())
        assert panel.get_config() == expected
        panel.set_mode("guided")
        assert panel.section_nav.isVisible()
        assert panel.current_section == "noise"
        assert panel.sections["noise"].isVisible()
        assert not panel.sections["system"].isVisible()
        assert panel.get_config() == expected
    finally:
        panel.close()


def test_initial_preview_does_not_change_state_or_run_simulation(qt_app):
    panel = ConfigPanel()
    requested = []
    panel.simulacao_acionada.connect(lambda: requested.append(True))
    panel.load_config(create_example_config("bell"))
    config = panel.get_config()
    assert "vetor de Bloch local" in panel.initial_preview.text()
    panel.set_mode("advanced")
    panel.set_mode("guided")
    assert panel.get_config() == config
    assert requested == []
    panel.spin_qubits.setValue(3)
    assert "exatamente dois" in panel.initial_preview.text()
    assert requested == []
    panel.close()


def test_summary_explains_invalid_seed_and_updates_without_running(qt_app):
    page = SimulationPage()
    requested = []
    page.run_requested.connect(requested.append)
    page.config_panel.input_seed.setText("invalid")
    assert "Semente" in page.configuration_feedback.text()
    page.config_panel.input_seed.setText("0")
    assert "Configuração válida" in page.configuration_feedback.text()
    assert "semente 0" in page._summary_rows["shots"].text()
    assert requested == []
    page.close()


def test_dashboard_beginner_help_is_optional_and_shortcuts_keep_contract(qt_app):
    page = DashboardPage()
    page.show()
    try:
        assert not page.concepts.isVisible()
        page.concept_toggle.click()
        assert page.concepts.isVisible()
        page.concept_toggle.click()
        assert not page.concepts.isVisible()
        expected = []
        page.examples_requested.connect(lambda: expected.append("examples"))
        page.tutorial_requested.connect(lambda: expected.append("tutorial"))
        from PySide6.QtWidgets import QPushButton

        buttons = {button.text(): button for button in page.findChildren(QPushButton)}
        buttons["Explorar exemplos"].click()
        buttons["Aprender fazendo"].click()
        assert expected == ["examples", "tutorial"]
    finally:
        page.close()


def test_dashboard_names_preserve_technical_selection(qt_app):
    from core.simulation import run_experiment

    source = run_experiment(create_example_config("bell"))
    page = DashboardPage()
    page.load_recent([source])
    page.set_annotations({source.id: {"title": "Bell · referência da pesquisa"}})
    button = page.recent.body().itemAt(1).widget()
    assert "Bell · referência da pesquisa" in button.text()
    assert source.id not in button.text()
    assert source.id in button.toolTip()
    selected = []
    page.experiment_selected.connect(selected.append)
    button.click()
    assert selected == [source.id]
    page.set_annotations({})
    assert "Bell · referência da pesquisa" not in page.recent.body().itemAt(1).widget().text()
    page.close()


def test_projector_layout_does_not_compress_summary_text(window, qt_app):
    window.resize(1024, 768)
    window._show_page("simulation")
    page = window.page_simulation
    page.config_panel.set_mode("advanced")
    qt_app.processEvents()
    qt_app.processEvents()
    for label in page._summary_rows.values():
        assert label.height() >= label.fontMetrics().height()
    assert page._scroll.horizontalScrollBar().maximum() == 0
    assert page.summary_scroll.horizontalScrollBar().maximum() == 0


def test_guided_sections_wrap_without_cutting_buttons(qt_app):
    panel = ConfigPanel()
    panel.show()
    try:
        for width in (320, 600, 1000):
            panel.resize(width, 600)
            qt_app.processEvents()
            if panel.section_selector.isVisible():
                assert not panel.section_nav.isVisible()
                assert panel.section_selector.count() == len(panel.sections)
                panel.section_selector.setCurrentIndex(4)
                assert panel.current_section == "execution"
                assert panel.sections["execution"].isVisible()
                continue
            bounds = panel.section_nav.rect()
            buttons = list(panel.section_buttons.values())
            assert all(bounds.contains(button.geometry()) for button in buttons)
            for index, button in enumerate(buttons):
                assert all(not button.geometry().intersects(other.geometry()) for other in buttons[index + 1:])
    finally:
        panel.close()
