"""Arquivos de análise são validados antes de substituir evidência existente."""
from copy import deepcopy
from dataclasses import replace
import json

import pytest

from core.analysis import convergence_analysis, parameter_sweep, temporal_analysis
from core.benchmark import mitigation_benchmark
from core.examples import create_example_config
from core.research import equal_budget_study, heatmap_study, zne_stability
from core.simulation import run_experiment
from core.study import trotter_noise_study
from data.analyses import load_analysis, save_analysis, validate_analysis


def minimal(kind):
    rows = {
        "temporal": {"time": 0, "fidelity": 1.0},
        "convergence": {"steps": 1, "infidelity": .01},
        "sweep": {"value": .02, "fidelity": .99},
        "trotter_noise": {"steps": 1, "ideal_infidelity": .01, "noisy_infidelity": .02},
        "heatmap": {"x": 1, "y": .02, "fidelity": .99},
        "zne_stability": {"method": "zne_linear", "rmse": .1},
        "equal_budget": {"method": "none", "rmse": .1},
        "mitigation_benchmark": {
            "method": "zne_linear", "label": "ZNE linear", "status": "available",
            "estimate": 1.2, "fidelity": None,
        },
    }
    data = {"kind": kind, "rows": [rows[kind]], "source_id": "source", "note": "Referência registrada."}
    if kind == "heatmap":
        data["options"] = {"x_parameter": "steps", "y_parameter": "p2"}
    if kind == "mitigation_benchmark":
        data.update(actual_cost={"circuits": 3, "shots": 96, "acquisition_s": .1}, ideal_observable=1.0)
    return data


@pytest.mark.parametrize("kind", ["temporal", "convergence", "sweep", "trotter_noise", "heatmap", "zne_stability", "equal_budget", "mitigation_benchmark"])
def test_historical_renderable_analysis_does_not_require_replay_metadata(tmp_path, kind):
    data = minimal(kind)
    original = deepcopy(data)
    path = save_analysis(data, tmp_path / f"{kind}.json")
    assert load_analysis(path, "source") == original
    assert data == original
    assert "config" not in data and "provenance" not in data


@pytest.mark.parametrize("kind,column,value", [
    ("temporal", "time", "não é tempo"), ("temporal", "time", None),
    ("temporal", "fidelity", "0.99"), ("temporal", "purity", True),
    ("temporal", "entropy_q0", float("nan")), ("temporal", "Z0Z1", {}),
    ("convergence", "steps", []), ("sweep", "value", None),
    ("sweep", "seed", False), ("trotter_noise", "ideal_infidelity", "erro"),
    ("heatmap", "x", [1]), ("heatmap", "y", "ruído"),
    ("zne_stability", "method", None), ("equal_budget", "rmse", "0.1"),
    ("mitigation_benchmark", "method", []), ("mitigation_benchmark", "label", 3),
    ("mitigation_benchmark", "status", None), ("mitigation_benchmark", "estimate", float("inf")),
    ("mitigation_benchmark", "stderr", -.1), ("temporal", "medida_extra", 10**400),
    ("temporal", "time", 10**400),
])
def test_invalid_analysis_never_replaces_existing_file(tmp_path, kind, column, value):
    data = minimal(kind)
    path = save_analysis(data, tmp_path / "analysis.json")
    previous = path.read_bytes()
    damaged = deepcopy(data)
    damaged["rows"][0][column] = value
    with pytest.raises(ValueError):
        save_analysis(damaged, path)
    assert path.read_bytes() == previous
    assert list(tmp_path.iterdir()) == [path]


@pytest.mark.parametrize("kind,field", [
    ("temporal", "time"), ("convergence", "steps"), ("sweep", "value"),
    ("trotter_noise", "ideal_infidelity"), ("trotter_noise", "noisy_infidelity"),
    ("heatmap", "x"), ("heatmap", "y"), ("zne_stability", "method"),
    ("mitigation_benchmark", "status"),
])
def test_missing_plot_coordinate_or_method_is_rejected(kind, field):
    data = minimal(kind)
    data["rows"][0].pop(field)
    with pytest.raises(ValueError):
        validate_analysis(data)


@pytest.mark.parametrize("field,value", [
    ("kind", []), ("note", None), ("rows", []), ("rows", [{0: .9}]),
    ("config", []), ("provenance", None), ("options", []),
    ("protocol", {"fields": []}), ("protocol", {"fields": {"title": 123}}),
    ("created_at", 1), ("source_id", []),
])
def test_invalid_analysis_structure_is_reported_without_modifying_file(tmp_path, field, value):
    data = minimal("temporal")
    data[field] = value
    path = tmp_path / "damaged.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    previous = path.read_bytes()
    with pytest.raises(ValueError):
        load_analysis(path, None)
    assert path.read_bytes() == previous


def test_benchmark_requires_display_cost_and_heatmap_requires_axes():
    for data in [
        {key: value for key, value in minimal("mitigation_benchmark").items() if key != "actual_cost"},
        {**minimal("mitigation_benchmark"), "actual_cost": {"circuits": 3, "shots": 96}},
        {**minimal("mitigation_benchmark"), "ideal_observable": "ideal"},
        {**minimal("heatmap"), "options": {"x_parameter": "steps"}},
    ]:
        with pytest.raises(ValueError):
            validate_analysis(data)


def test_rejects_nonfinite_metadata_and_different_row_columns():
    data = minimal("temporal")
    data["provenance"] = {"value": float("inf")}
    with pytest.raises(ValueError):
        validate_analysis(data)
    data.pop("provenance")
    data["rows"].append({"time": 1})
    with pytest.raises(ValueError):
        validate_analysis(data)


def test_generated_artifacts_of_every_kind_remain_roundtrip_compatible(tmp_path):
    source = run_experiment(replace(create_example_config("depolarizing-bell"), shots=16))
    analyses = [
        temporal_analysis(source), convergence_analysis(source.config, [1]),
        parameter_sweep(source.config, "p2", [.01], seeds=[42]),
        trotter_noise_study(source, [1]), mitigation_benchmark(source, shots=16),
        heatmap_study(source, x_values=[1], y_values=[.01]),
        zne_stability(source, factor_sets=[[1, 3, 5]], shot_counts=[16], repetitions=2),
        equal_budget_study(source, factor_sets=[[1, 3, 5]], total_shots=18, repetitions=2),
    ]
    for data in analyses:
        data.setdefault("source_id", source.id)
        path = save_analysis(data, tmp_path / f"{data['kind']}.json")
        assert load_analysis(path, source.id) == data
