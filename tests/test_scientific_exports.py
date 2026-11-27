import csv
from dataclasses import replace
import io
import json
import zipfile

import pytest

from core.examples import create_example_config
from core.export import export_analysis, export_experiment_csv, export_run_bundle
from core.simulation import run_experiment


@pytest.fixture
def experiment():
    config = replace(create_example_config("bell"), shots=32, seed=None)
    return run_experiment(config)


def test_experiment_csv_is_self_contained_and_preserves_null_mitigation(experiment, tmp_path):
    path = export_experiment_csv(experiment, tmp_path / "scientific.csv",
                                 {"title": "Bell — preparação", "notes": "Notas do TCC"})
    rows = list(csv.DictReader(path.open(encoding="utf-8", newline="")))
    assert rows
    for row in rows:
        assert row["experiment_id"] == experiment.id
        assert row["title"] == "Bell — preparação"
        assert row["created_at"] == experiment.created_at.isoformat()
        assert int(row["effective_seed"]) == experiment.result.metadata["effective_seed"]
        assert json.loads(row["config_json"])["seed"] is None
        assert json.loads(row["metadata_json"])["versions"] == experiment.result.metadata["versions"]
        assert json.loads(row["mitigation_json"]) is None
        assert json.loads(row["annotation_json"])["notes"] == "Notas do TCC"
        assert float(row["fidelity"]) == experiment.result.fidelity
    assert sum(int(row["counts"]) for row in rows) == experiment.config.shots
    assert sum(float(row["frequency"]) for row in rows) == pytest.approx(1)


def test_analysis_csv_has_complete_adjacent_manifest_and_json_roundtrip(tmp_path):
    data = {
        "kind": "mitigation_benchmark", "source_id": "source",
        "config": {"seed": None, "noise": {"kind": "Termico", "t1_us": 50}},
        "provenance": {"effective_seed": 17, "versions": {"qiskit": "test"}},
        "samples": [{"factor": 3, "seed": 18, "counts": {"00": 7, "11": 3}}],
        "runs": [{"config": {"seed": 17}, "counts": {"00": 10}}],
        "rows": [{"method": "baseline", "estimate": 0.4, "fidelity": 0.9},
                 {"method": "zne_linear", "estimate": 0.7, "fidelity": None}],
    }
    path = export_analysis(data, tmp_path / "benchmark.csv")
    metadata_path = path.with_suffix(".metadata.json")
    manifest = json.loads(metadata_path.read_text(encoding="utf-8"))
    assert all(manifest[key] == value for key, value in data.items() if key != "rows")
    assert manifest["csv_export"]["row_count"] == 2
    rows = list(csv.DictReader(path.open(encoding="utf-8", newline="")))
    assert [row["method"] for row in rows] == ["baseline", "zne_linear"]
    assert rows[1]["fidelity"] == ""
    json_path = export_analysis(data, tmp_path / "benchmark.json")
    assert json.loads(json_path.read_text(encoding="utf-8")) == data


def test_bundle_annotation_and_analysis_keep_original_snapshot_schema(experiment, tmp_path):
    analysis = {"kind": "trotter_noise", "source_id": experiment.id,
                "rows": [{"steps": 1, "noisy_infidelity": 0.2}],
                "provenance": {"seed": experiment.result.metadata["effective_seed"]}}
    annotation = {"title": "Estudo 1", "project": "TCC", "notes": "Detalhes"}
    bundle = export_run_bundle(experiment, tmp_path / "run.zip", annotation, analysis)
    with zipfile.ZipFile(bundle) as archive:
        assert archive.testzip() is None
        assert json.loads(archive.read("analyses.json")) == analysis
        manifest = json.loads(archive.read("manifest.json"))
        assert manifest["annotation"] == annotation
        assert manifest["title"] == "Estudo 1"
        original = json.loads(archive.read("experimento.json"))
        assert original["id"] == experiment.id
        assert "title" not in original
        assert original["result"]["metadata"]["effective_seed"] == experiment.result.metadata["effective_seed"]
        csv_rows = list(csv.DictReader(io.StringIO(archive.read("resultados.csv").decode("utf-8"))))
        assert csv_rows[0]["experiment_id"] == experiment.id


def test_nonfinite_analysis_does_not_replace_existing_outputs(tmp_path):
    path = tmp_path / "study.csv"
    path.write_text("original", encoding="utf-8")
    manifest = path.with_suffix(".metadata.json")
    manifest.write_text("original manifest", encoding="utf-8")
    with pytest.raises(ValueError):
        export_analysis({"rows": [{"value": float("nan")}]}, path)
    assert path.read_text(encoding="utf-8") == "original"
    assert manifest.read_text(encoding="utf-8") == "original manifest"
    assert not list(tmp_path.glob("*.tmp"))


def test_export_failures_propagate_and_leave_no_staging_files(tmp_path, monkeypatch):
    from pathlib import Path
    def fail(*args, **kwargs):
        raise OSError("disk full")
    monkeypatch.setattr(Path, "replace", fail)
    with pytest.raises(OSError, match="disk full"):
        export_analysis({"rows": [{"value": 1}]}, tmp_path / "study.json")
    assert not list(tmp_path.iterdir())
