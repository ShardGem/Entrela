"""Integration: artifacts stay attached to their immutable scientific source."""

from dataclasses import replace
import json
import pytest

from core.examples import create_example_config
from data.analyses import load_analysis, save_analysis
from tests.qt_helpers import execute, wait_until


@pytest.mark.parametrize("kind, options, row_count", [
    ("mitigation_benchmark", {"shots": 128}, 4),
    ("trotter_noise", {"steps": [1, 3]}, 2),
])
def test_study_worker_save_reopen_replay(window, kind, options, row_count):
    window.page_simulation.config_panel.load_config(replace(create_example_config("depolarizing-bell"), shots=128))
    source = execute(window)
    counts = dict(source.result.counts)
    window._run_analysis(kind, options)
    wait_until(lambda: window._current_worker is None)
    page = window.page_analysis
    data = page.data
    assert data["kind"] == kind
    assert data["source_id"] == source.id
    assert len(data["rows"]) == row_count
    assert page.saved.count() == 2
    assert source.result.counts == counts
    page.saved.setCurrentIndex(1)
    assert page.data["analysis_id"] == data["analysis_id"]
    page.replay_button.click()
    wait_until(lambda: window._current_worker is None)
    replay = page.data
    assert replay["analysis_id"] != data["analysis_id"]
    if kind == "mitigation_benchmark":
        assert [s["counts"] for s in replay["samples"]] == [s["counts"] for s in data["samples"]]
        assert all(r["fidelity"] is None for r in replay["rows"] if r["method"].startswith("zne_"))
    else:
        assert [r["noisy_infidelity"] for r in replay["rows"]] == pytest.approx([r["noisy_infidelity"] for r in data["rows"]])
    assert window._current_experiment is source


def test_named_record_report_and_zne_reproduction(window, tmp_path, monkeypatch):
    from gui.main_window import QFileDialog

    window.page_simulation.config_panel.load_config(replace(create_example_config("bell"), shots=64))
    source = execute(window)
    window.page_library.run_title.setText("Bell · referência da pesquisa")
    window._annotate_current("TCC", "Controle ideal", ["referência"])
    assert window.page_results._title.text() == "Bell · referência da pesquisa"
    window.page_history.search.setText("referência da pesquisa")
    assert window.page_history.table.rowCount() == 1
    destination = tmp_path / "report.pdf"
    monkeypatch.setattr(QFileDialog, "getSaveFileName", lambda *args: (str(destination), "PDF (*.pdf)"))
    window._export_report()
    wait_until(lambda: window._current_worker is None)
    assert destination.read_bytes().startswith(b"%PDF")
    assert window._current_experiment is source
    window._run_mitigation(1, "quadratic", 128)
    wait_until(lambda: window._current_worker is None)
    mitigated = window._current_experiment
    assert mitigated.result.metadata["reproduction"]["mitigation_method"] == "zne"
    assert source.result.metadata["reproduction"]["mitigation_method"] == "none"
    assert mitigated.result.mitigation["samples"][0]["counts"]
    window._open_experiment(mitigated.id)
    assert window.page_mitigation.qubit.value() == 1
    assert window.page_mitigation.method.currentData() == "quadratic"
    assert window.page_mitigation.shots.value() == 128
    window._rerun_current()
    wait_until(lambda: window._current_worker is None)
    reproduced = window._current_experiment.result.mitigation
    assert reproduced["method"] == "quadratic"
    assert reproduced["qubit"] == 1
    assert reproduced["shots"] == 128
    assert [s["counts"] for s in reproduced["samples"]] == [s["counts"] for s in mitigated.result.mitigation["samples"]]


def test_analysis_save_is_atomic_and_rejects_wrong_source(tmp_path, monkeypatch):
    from pathlib import Path

    data = {"kind": "sweep", "source_id": "source1", "note": "ensemble", "rows": [{"value": 0, "fidelity": 1.0}]}
    path = tmp_path / "analysis.json"
    save_analysis(data, path)
    original = path.read_bytes()
    with pytest.raises(ValueError, match="outra execução"):
        load_analysis(path, "different")
    monkeypatch.setattr(Path, "replace", lambda *args: (_ for _ in ()).throw(OSError("disk failure")))
    with pytest.raises(OSError):
        save_analysis({**data, "note": "changed"}, path)
    assert path.read_bytes() == original
    assert list(tmp_path.iterdir()) == [path]


def test_cancelled_analysis_preserves_source_and_previous_data(window):
    window.page_simulation.config_panel.load_config(replace(create_example_config("bell"), shots=64))
    source = execute(window)
    window._run_analysis("mitigation_benchmark", {"shots": 64})
    window.page_analysis.btn_cancel.click()
    wait_until(lambda: window._current_worker is None)
    assert window._current_experiment is source
    assert window.page_analysis.data is None
    assert not list((window.repository.base_dir / ".analyses" / source.id).glob("*.json"))


def test_export_is_available_when_workspace_storage_fails(window, tmp_path, monkeypatch):
    from gui.main_window import QFileDialog
    window.page_simulation.config_panel.load_config(replace(create_example_config("bell"), shots=64))
    source = execute(window)
    window.repository = None
    destination = tmp_path / "recovered.csv"
    monkeypatch.setattr(QFileDialog, "getSaveFileName", lambda *args: (str(destination), "CSV (*.csv)"))
    window._export_counts()
    assert source.id in destination.read_text(encoding="utf-8")
    assert "config_json" in destination.read_text(encoding="utf-8")
