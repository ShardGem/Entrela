from dataclasses import asdict, replace
import json

import pytest

from core.analysis import convergence_analysis, parameter_sweep, temporal_analysis
from core.examples import create_example_config
from core.simulation import run_experiment
from core.types import config_from_dict


def test_sweep_records_actual_point_configs_seeds_and_environment():
    config = replace(create_example_config("depolarizing-bell"), shots=32, seed=None)
    source_config = asdict(config)
    data = parameter_sweep(config, "p2", [0.02, 0.07], seeds=[19, 23])
    assert data["config"] == source_config
    assert len(data["runs"]) == len(data["rows"]) == 4
    for record, row in zip(data["runs"], data["rows"]):
        point = config_from_dict(record["config"])
        assert point.seed == row["seed"]
        assert point.noise.p2 == row["value"]
        assert point.protocol.save_snapshots is False
        assert sum(record["counts"].values()) == point.shots
        assert record["metadata"]["effective_seed"] == point.seed
        assert record["metadata"]["versions"]
        replay = run_experiment(point)
        assert replay.result.counts == record["counts"]
        assert replay.result.fidelity == pytest.approx(row["fidelity"])
    assert data["provenance"]["analysis_environment"]["versions"]["scipy"]
    assert asdict(config) == source_config
    json.dumps(data, allow_nan=False)


def test_convergence_records_its_overrides_in_actual_configs():
    config = replace(create_example_config("depolarizing-bell"), shots=128, seed=99)
    data = convergence_analysis(config, steps=[1, 3])
    assert data["config"]["shots"] == 128
    assert data["config"]["seed"] == 99
    assert data["config"]["noise"]["enabled"] is True
    for record, steps in zip(data["runs"], [1, 3]):
        actual = config_from_dict(record["config"])
        assert actual.seed == 42
        assert actual.shots == 1
        assert actual.noise.enabled is False
        assert actual.protocol.trotter_steps == steps
        assert actual.protocol.save_snapshots is False
        assert record["metadata"]["effective_seed"] == 42
        assert sum(record["counts"].values()) == 1


def test_temporal_provenance_distinguishes_current_calculations_from_historical_source():
    experiment = run_experiment(replace(create_example_config("bell"), shots=16))
    historical = {"qiskit": "historical-version"}
    experiment.result.metadata["versions"] = historical
    experiment.result.metadata["entrela_version"] = "0.1-historical"
    data = temporal_analysis(experiment)
    provenance = data["provenance"]
    assert provenance["source_environment"]["versions"] == historical
    assert provenance["source_environment"]["entrela_version"] == "0.1-historical"
    assert provenance["analysis_environment"]["versions"]["qiskit"] != "historical-version"
    assert provenance["source_effective_seed"] == experiment.result.metadata["effective_seed"]
    assert provenance["created_at"]
