"""Regressions reproduced by the TCC audit and new scientific invariants."""

from dataclasses import replace
from types import SimpleNamespace
import json
import numpy as np
import pytest
from core.examples import create_example_config
from core.simulation import run_experiment, SimulationCancelled
from core.analysis import (
    temporal_analysis,
    convergence_analysis,
    parameter_sweep,
)
from core.report import report_html, export_report
from data.repository import ExperimentRepository
from data.workspace import WorkspaceLibrary
from tests.qt_helpers import execute, wait_until


@pytest.fixture
def bell():
    return run_experiment(replace(create_example_config("bell"), shots=64))


@pytest.mark.parametrize(
    "field,value",
    [
        ("metadata", None),
        ("metadata", []),
        ("circuit_text", None),
        ("circuit_depth", -1),
        ("error", 42),
        ("times", [0, float("nan")]),
    ],
)
def test_invalid_result_contract_rejected(bell, field, value):
    raw = ExperimentRepository._serialize(bell)
    raw["result"][field] = value
    with pytest.raises(ValueError):
        ExperimentRepository._deserialize(raw)


@pytest.mark.parametrize(
    "field,value",
    [
        ("duration_s", -1),
        ("duration_s", float("inf")),
        ("tags", None),
        ("tags", [1]),
        ("id", "../outside"),
    ],
)
def test_invalid_record_contract_rejected(bell, field, value):
    raw = ExperimentRepository._serialize(bell)
    raw[field] = value
    with pytest.raises(ValueError):
        ExperimentRepository._deserialize(raw)


@pytest.mark.parametrize("number", [0.12345678901234566, 1e-25, -np.pi])
def test_form_roundtrip_preserves_float(window, number):
    config = replace(
        create_example_config("bell"),
        system=replace(create_example_config("bell").system, J=number),
    )
    panel = window.page_simulation.config_panel
    panel.load_config(config)
    assert panel.get_config() == config
    assert float(panel.spin_J.text()) == number


def test_playback_stops_and_slider_agrees_during_play(window, bell):
    page = window.page_bloch
    page.load_statevectors(bell.result.states, bell.result.times)
    page._toggle_play()
    page.slider.setValue(2)
    assert page.current_frame == page.slider.value() == 2
    for _ in range(20):
        page._on_tick()
    assert not page.playing
    assert page.current_frame == len(bell.result.states) - 1
    page._next()
    assert page.current_frame == len(bell.result.states) - 1
    page._stop()
    page.loop.setChecked(True)
    page._toggle_play()
    page.current_frame = len(bell.result.states) - 1
    page._on_tick()
    assert page.current_frame == 0
    assert len(page.canvas._trail_data[0]) == 1
    page._pause()


def test_camera_changes_projection_preserves_quantum_data(window, bell):
    page = window.page_bloch
    page.load_statevectors(
        bell.result.states, bell.result.times, bell.result.ideal_statevectors
    )
    before = page.canvas.ax.get_proj().copy()
    state = bell.result.states[0].data.copy()
    page.canvas._on_scroll(SimpleNamespace(inaxes=page.canvas.ax, step=1))
    assert not np.allclose(page.canvas.ax.get_proj(), before)
    for _ in range(100):
        page.canvas.zoom_by(2)
    assert page.canvas.zoom == 3
    page.canvas.set_focus(1)
    page.canvas.pan(0.25)
    page.canvas.reset_camera()
    assert page.canvas.zoom == 1
    np.testing.assert_array_equal(bell.result.states[0].data, state)
    page.focus_combo.setCurrentIndex(1)
    assert page.canvas.focus == 0


def test_temporal_bell_entanglement_and_exact_reference(bell):
    data = temporal_analysis(bell)
    for row in data["rows"]:
        assert row["purity"] == pytest.approx(1)
        assert row["fidelity_exact"] == pytest.approx(1)
        assert row["entropy_q0"] == pytest.approx(1)
        assert row["negativity_q0_rest"] == pytest.approx(0.5)
        assert row["Z0Z1"] == pytest.approx(1)


def test_convergence_against_exact_and_source_preserved():
    cfg = replace(
        create_example_config("bell"),
        system=replace(
            create_example_config("bell").system, J=1, h=0.7, initial_state="zero"
        ),
    )
    original = cfg
    rows = convergence_analysis(cfg, [1, 2, 4, 8])["rows"]
    assert rows[-1]["infidelity"] < rows[0]["infidelity"] / 100
    assert cfg == original


def test_sweep_validates_all_points_before_running_and_cancels(monkeypatch):
    cfg = replace(create_example_config("bell"), shots=64)
    calls = []
    monkeypatch.setattr(
        "core.analysis.run_experiment", lambda *args, **kwargs: calls.append(1)
    )
    with pytest.raises(ValueError):
        parameter_sweep(cfg, "p1", [0.01, 2])
    assert not calls
    with pytest.raises(SimulationCancelled):
        parameter_sweep(cfg, "J", [0, 1], is_cancelled=lambda: True)
    assert not calls


def test_sweep_seed_and_deterministic_ensemble():
    cfg = replace(create_example_config("depolarizing-bell"), shots=128)
    rows = parameter_sweep(cfg, "p2", [0, 0.05], seeds=[7, 8])["rows"]
    assert len(rows) == 4
    assert rows[0]["fidelity"] == pytest.approx(rows[1]["fidelity"])
    assert rows[2]["fidelity"] < rows[0]["fidelity"]
    assert {row["seed"] for row in rows} == {7, 8}


def test_history_uses_summary_without_decoding_states(tmp_path, bell, monkeypatch):
    repo = ExperimentRepository(tmp_path)
    repo.save(bell)
    monkeypatch.setattr(
        "data.repository.decode_state",
        lambda _: pytest.fail("History decoded state arrays"),
    )
    records = repo.list_summaries()
    assert len(records) == 1
    assert not records[0].result.states
    assert records[0].result.fidelity == bell.result.fidelity


def test_summary_invalidates_after_source_changes(tmp_path, bell):
    repo = ExperimentRepository(tmp_path)
    path = repo.save(bell)
    raw = json.loads(path.read_text())
    raw["result"]["metadata"] = None
    path.write_text(json.dumps(raw))
    assert repo.list_summaries() == []
    assert repo.load_errors


def test_library_annotations_do_not_change_scientific_record(tmp_path, bell):
    repo = ExperimentRepository(tmp_path / "runs")
    path = repo.save(bell)
    before = path.read_bytes()
    library = WorkspaceLibrary(tmp_path / "library")
    library.save_template("Bell", bell.config)
    library.annotate(bell.id, "TCC", "Hipótese <x>", ["base"])
    assert library.template("Bell") == bell.config
    assert library.read()["annotations"][bell.id]["project"] == "TCC"
    assert path.read_bytes() == before


def test_report_escapes_external_text_and_exports_pdf(qt_app, tmp_path, bell):
    bell.result.metadata["external"] = "<script>alert(1)</script>"
    html = report_html(bell)
    assert "<script>" not in html
    assert "&lt;script&gt;" in html
    assert "data:image/png;base64," in html
    path = export_report(bell, tmp_path / "report.pdf")
    assert path.read_bytes().startswith(b"%PDF")


def test_gui_analysis_rerun_and_library(window):
    window.page_simulation.config_panel.load_config(
        replace(create_example_config("bell"), shots=64, seed=None)
    )
    source = execute(window)
    window._run_analysis("temporal", {})
    wait_until(lambda: window._current_worker is None)
    assert len(window.page_analysis.data["rows"]) == 5
    window._save_template("Meu Bell")
    assert window._workspace_library().template("Meu Bell") == source.config
    window._annotate_current("TCC", "Notas", ["Bell"])
    window.page_history.search.setText("TCC")
    assert window.page_history.table.rowCount() == 1
    window._rerun_current()
    wait_until(lambda: window._current_worker is None)
    rerun = window._current_experiment
    assert rerun.id != source.id
    assert rerun.config.seed == source.result.metadata["effective_seed"]
    assert rerun.result.counts == source.result.counts


def test_preferences_theme_and_restart(window, qt_app):
    from gui.main_window import MainWindow
    from gui.theme import PALETTE

    window.page_settings.theme.setCurrentIndex(1)
    window.page_settings.font_size.setValue(15)
    window.page_bloch.speed_combo.setCurrentText("2x")
    window.page_bloch.loop.setChecked(True)
    assert PALETTE.bg == "#f3f6fb"
    repo, settings = window.repository, window.settings
    window.close()
    other = MainWindow(repo, settings)
    try:
        assert other.page_settings.theme.currentData() == "light"
        assert other.page_settings.font_size.value() == 15
        assert other.page_bloch.loop.isChecked()
        assert other.page_bloch.speed_combo.currentText() == "2x"
    finally:
        other.close()


@pytest.mark.parametrize(
    "kind,options,count",
    [
        ("convergence", {"steps": [1, 2, 4]}, 3),
        ("sweep", {"parameter": "p2", "values": [0, 0.05], "seeds": [7, 8]}, 4),
    ],
)
def test_analysis_ui_roundtrip(window, kind, options, count):
    window.page_simulation.config_panel.load_config(
        replace(create_example_config("bell"), shots=64)
    )
    source = execute(window)
    window._run_analysis(kind, options)
    wait_until(lambda: window._current_worker is None)
    assert len(window.page_analysis.data["rows"]) == count
    assert window.page_analysis.saved.count() == 2
    assert window._current_experiment.id == source.id
    window._open_experiment(source.id)
    window.page_analysis.saved.setCurrentIndex(1)
    assert window.page_analysis.data["kind"] == kind
    assert len(window.page_analysis.data["rows"]) == count


def test_bloch_probability_overlay_matches_snapshot(window, bell):
    page = window.page_bloch
    page.load_statevectors(
        bell.result.states, bell.result.times, bell.result.ideal_statevectors
    )
    page.visual_tabs.setCurrentIndex(1)
    page.slider.setValue(2)
    bars = page.probabilities_canvas.fig.axes[0].patches
    np.testing.assert_allclose(
        [p.get_height() for p in bars[:4]], [0.5, 0, 0, 0.5], atol=1e-12
    )
    assert sum(p.get_height() for p in bars) == pytest.approx(2)


@pytest.mark.parametrize(
    "operations",
    [
        None,
        [{}],
        [
            {
                "stage": "evolution",
                "step": 99,
                "name": "rx",
                "qubits": [0],
                "parameters": [1],
            }
        ],
    ],
)
def test_untrusted_circuit_metadata_rejected_before_display(bell, operations):
    raw = ExperimentRepository._serialize(bell)
    raw["result"]["metadata"]["operations"] = operations
    with pytest.raises(ValueError):
        ExperimentRepository._deserialize(raw)


def test_zne_diagnostics_include_exact_reference(window):
    window.page_simulation.config_panel.load_config(
        replace(create_example_config("depolarizing-bell"), shots=64)
    )
    execute(window)
    window._run_mitigation(0, "quadratic", 128)
    wait_until(lambda: window._current_worker is None)
    data = window._current_experiment.result.mitigation
    assert data["ideal_observable"] == pytest.approx(0, abs=1e-12)
    assert data["degrees_of_freedom"] == 0
    assert len(data["coefficients"]) == 3
    assert max(abs(x) for x in data["residuals"]) < 1e-12
    assert window.page_mitigation.canvas.fig.axes[0].lines


def test_history_pagination_and_project_search(window, bell):
    records = [replace(bell, id=f"run{i}") for i in range(205)]
    page = window.page_history
    page.load(records)
    assert page.table.rowCount() == 100
    page.next.click()
    assert page.table.rowCount() == 100
    page.next.click()
    assert page.table.rowCount() == 5
    page.search.setText("run204")
    assert page.table.rowCount() == 1
