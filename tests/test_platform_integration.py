"""Real persistence and worker flows for the platform evolution."""
from dataclasses import replace

from gui.main_window import MainWindow
from core.examples import create_example_config
from tests.qt_helpers import execute, wait_until


def test_named_run_and_research_notes_preserve_scientific_record(window):
    page = window.page_simulation
    page.experiment_name.setText("Bell · hipótese de decoerência")
    page.experiment_description.setText("Comparar a referência ideal ao ruído.")
    page.config_panel.load_config(replace(create_example_config("bell"), shots=64))
    experiment = execute(window)
    record_path = window.repository._path(experiment.id)
    before = record_path.read_bytes()
    assert window._current_annotation()["title"] == "Bell · hipótese de decoerência"
    assert "referência ideal" in window._current_annotation()["description"]
    assert experiment.id not in window.page_results._subtitle.text()
    window._workspace_library().annotate(experiment.id, "TCC", "Nova interpretação", ["Bell"],
                                        objective="Investigar perda de pureza", hypothesis="Ruído reduz fidelidade")
    window._refresh_library()
    assert record_path.read_bytes() == before
    assert window._current_annotation()["title"] == "Bell · hipótese de decoerência"


def test_extended_preferences_survive_restart_and_restore_defaults(window):
    page = window.page_settings
    values = dict(page.collect_values(), theme="light", accent="violet", density="spacious",
                  font_size=18, reduce_motion=True, high_contrast=True,
                  completion_notifications=False, export_dpi=400)
    page.apply_values(values)
    window._apply_preferences()
    window.page_documentation.report_template.setCurrentIndex(1)
    report_options = window.page_documentation.report_options()
    window.page_comparison.apply_view_preferences({"hist_layout": 1, "tab": 4, "camera_sync": False, "focus": 1})
    comparison_options = window.page_comparison.collect_view_preferences()
    window.close()
    window.settings.sync()
    other = MainWindow(window.repository, window.settings)
    try:
        assert other.page_settings.collect_values() == values
        assert other.page_documentation.report_options() == report_options
        assert other.page_comparison.collect_view_preferences() == comparison_options
        other._reset_preferences()
        assert other.page_settings.collect_values() == other.page_settings.DEFAULTS
    finally:
        other.close()


def test_history_detail_load_preserves_current_experiment(window):
    window.page_simulation.config_panel.load_config(replace(create_example_config("bell"), shots=64))
    experiment = execute(window)
    window._request_history_detail(experiment.id)
    wait_until(lambda: window._current_worker is None)
    assert window._current_experiment is experiment
    assert window.repository.load(experiment.id).config == experiment.config
    assert len(window.repository.list_summaries()) == 1


def test_removed_shortcut_and_learning_demo_open_existing_editor(window):
    from core.learning import CONCEPTS
    assert "Ctrl+K" not in [shortcut.key().toString() for shortcut in window.shortcuts]
    concept = next(value for value in CONCEPTS if value.key == "bell")
    document = concept.demonstration
    window._load_demonstration(document)
    assert window._current_page == "circuit"
    assert window.page_circuit.tabs.currentWidget() is window.page_circuit.editor
    assert window.page_circuit.editor.document == document


def test_result_pdf_uses_shared_a4_worker(window, monkeypatch, tmp_path):
    import re
    from PySide6.QtWidgets import QFileDialog
    window.page_simulation.config_panel.load_config(replace(create_example_config("bell"), shots=64))
    execute(window)
    window.page_documentation.report_template.setCurrentIndex(1)
    destination = tmp_path / "relatorio.pdf"
    monkeypatch.setattr(QFileDialog, "getSaveFileName", lambda *args: (str(destination), "PDF (*.pdf)"))
    window._export_report()
    wait_until(lambda: window._current_worker is None)
    data = destination.read_bytes()
    boxes = re.findall(rb"/MediaBox\s*\[([^]]+)\]", data)
    assert boxes
    for box in boxes:
        assert [float(value) for value in box.split()] == __import__("pytest").approx([0, 0, 595.27559055, 841.88976378])
