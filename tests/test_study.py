from dataclasses import asdict, replace
import json

import pytest

from core.analysis import exact_states
from core.metrics import fidelity
from core.simulation import SimulationCancelled, run_experiment
from core.study import trotter_noise_study
from core.types import (
    ExperimentConfig,
    NoiseConfig,
    SimulationProtocol,
    SystemConfig,
    config_from_dict,
)


def source(noise=None, seed=42):
    return run_experiment(
        ExperimentConfig(
            SystemConfig(),
            SimulationProtocol(total_time=1, trotter_steps=2, save_snapshots=False),
            noise or NoiseConfig(enabled=False),
            shots=32,
            seed=seed,
        )
    )


def test_paired_study_converges_against_exact_and_preserves_source():
    experiment = source()
    original = asdict(experiment.config)
    counts = dict(experiment.result.counts)
    study = trotter_noise_study(experiment, steps=[1, 2, 8])
    assert study["kind"] == "trotter_noise"
    assert study["source_id"] == experiment.id
    assert asdict(experiment.config) == original
    assert experiment.result.counts == counts
    assert study["rows"][-1]["ideal_infidelity"] < study["rows"][0]["ideal_infidelity"]
    for row in study["rows"]:
        assert row["fidelity_ideal_exact"] == pytest.approx(row["fidelity_noisy_exact"])
        assert row["fidelity_noisy_ideal"] == pytest.approx(1)
        assert row["gate_count"] > 0
    assert study["provenance"]["best_evaluated"]["steps"] in [1, 2, 8]
    json.dumps(study, allow_nan=False)


def test_noisy_study_records_replayable_effective_configs_and_raw_measurements():
    experiment = source(NoiseConfig(p1=0.02, p2=0.05), seed=None)
    study = trotter_noise_study(experiment, steps=[1, 3])
    assert len(study["runs"]) == 4
    assert study["provenance"]["source_effective_seed"] == experiment.result.metadata["effective_seed"]
    record = study["runs"][-1]
    replay = run_experiment(config_from_dict(record["config"]))
    assert replay.result.counts == record["counts"]
    exact = exact_states(experiment.config, [1])[0]
    assert study["rows"][-1]["fidelity_noisy_exact"] == pytest.approx(
        fidelity(replay.result.final_state, exact)
    )
    assert record["metadata"]["versions"]
    assert study["rows"][-1]["purity"] < 1


@pytest.mark.parametrize("steps", [[], [1, 1], [0], [201], [True], [1.5], list(range(1, 12))])
def test_study_rejects_invalid_points_before_work(steps, monkeypatch):
    experiment = source()
    def unexpected(*args, **kwargs):
        raise AssertionError("Must validate all points before simulation")
    monkeypatch.setattr("core.study.run_experiment", unexpected)
    with pytest.raises(ValueError):
        trotter_noise_study(experiment, steps)


def test_study_propagates_cancellation_and_rejects_free_circuit():
    experiment = source()
    with pytest.raises(SimulationCancelled):
        trotter_noise_study(experiment, is_cancelled=lambda: True)
    from core.circuit_document import CircuitDocument
    config = replace(experiment.config, circuit=CircuitDocument(num_qubits=2),
                     protocol=SimulationProtocol(total_time=1, trotter_steps=1))
    free = run_experiment(config)
    with pytest.raises(ValueError, match="Hamiltoniano"):
        trotter_noise_study(free)
