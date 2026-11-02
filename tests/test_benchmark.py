"""Independent channel predictions, applicability and replay of mitigation studies."""

from dataclasses import replace
from copy import deepcopy
import json
import numpy as np
import pytest

from core.benchmark import mitigation_benchmark
from core.circuit_document import CircuitDocument, CircuitGate
from core.examples import create_example_config
from core.simulation import run_experiment, SimulationCancelled
from core.types import ExperimentConfig, NoiseConfig, SimulationProtocol, SystemConfig, config_from_dict


def x_run(noise=None, seed=42, shots=4096):
    document = CircuitDocument(1, (CircuitGate("x", (0,)),))
    return run_experiment(ExperimentConfig(
        SystemConfig(1), SimulationProtocol(1., 1, False),
        noise or NoiseConfig(p1=.2, p2=0), shots=shots, seed=seed, circuit=document,
    ))


def test_shared_samples_against_analytic_depolarization_and_physical_conditioning():
    source = x_run()
    result = mitigation_benchmark(source)
    assert result["kind"] == "mitigation_benchmark"
    np.testing.assert_allclose(
        [s["estimate"] for s in result["samples"]], [-.8, -.8**3, -.8**5], atol=.04,
    )
    assert [s["gate_counts"] for s in result["samples"]] == [{"u": 1}, {"u": 3}, {"u": 5}]
    baseline, linear, quadratic, parity = result["rows"]
    assert baseline["fidelity"] == pytest.approx(.9)
    assert baseline["purity"] == pytest.approx(.82)
    assert baseline["energy"] is None
    assert baseline["estimate"] == result["samples"][0]["estimate"]
    assert baseline["absolute_error"] == pytest.approx(abs(baseline["estimate"] + 1))
    assert linear["fidelity"] is quadratic["fidelity"] is None
    assert linear["shared_samples"] == quadratic["shared_samples"] == [1, 3, 5]
    assert linear["acquisition_s"] == quadratic["acquisition_s"]
    assert parity["status"] == "available"
    assert parity["estimate"] == pytest.approx(-1)
    assert parity["fidelity"] == pytest.approx(1)
    assert parity["purity"] == pytest.approx(1)
    assert parity["acceptance"] == parity["retained_shots"] / source.config.shots
    assert result["symmetry"]["ensemble_acceptance"] == pytest.approx(.9)
    assert result["actual_cost"]["circuits"] == 3
    assert result["actual_cost"]["shots"] == 3 * source.config.shots
    for row in result["rows"]:
        assert row["duration_s"] == pytest.approx(row["acquisition_s"] + row["processing_s"])


def test_thermal_reference_and_parity_projection_are_separate_from_shot_statistics():
    result = mitigation_benchmark(x_run(NoiseConfig(kind="Termico", t1_us=.1, t2_us=.1)))
    assert result["rows"][0]["fidelity"] == pytest.approx(np.exp(-.5))
    assert result["rows"][-1]["fidelity"] == pytest.approx(1)
    assert result["provenance"]["noise"]["kind"] == "Termico"
    assert result["provenance"]["thermal_gate_time_ns"] == 50


def test_noiseless_deterministic_circuit_and_json_roundtrip_replay():
    source = x_run(NoiseConfig(enabled=False), seed=None, shots=128)
    before = deepcopy(source.result.counts)
    benchmark = mitigation_benchmark(source)
    encoded = json.loads(json.dumps(benchmark, allow_nan=False))
    assert encoded["provenance"]["effective_seed"] == source.result.metadata["effective_seed"]
    assert encoded["config"]["seed"] == source.result.metadata["effective_seed"]
    assert encoded["provenance"]["versions"]["qiskit-aer"]
    assert source.result.counts == before
    for row in benchmark["rows"]:
        assert row["estimate"] == pytest.approx(-1)
        assert row["absolute_error"] == pytest.approx(0, abs=1e-12)
    replay_source = run_experiment(config_from_dict(encoded["config"]))
    replay = mitigation_benchmark(replay_source)
    assert [s["counts"] for s in benchmark["samples"]] == [s["counts"] for s in replay["samples"]]
    assert [s["effective_seed"] for s in benchmark["samples"]] == [s["effective_seed"] for s in replay["samples"]]
    assert benchmark["provenance"]["fingerprint"] == replay["provenance"]["fingerprint"]


def test_parity_not_invented_when_ideal_is_not_parity_eigenstate():
    source = run_experiment(replace(
        create_example_config("spin-oscillation"), shots=128,
    ))
    result = mitigation_benchmark(source)
    parity = result["rows"][-1]
    assert parity["status"] == "unavailable"
    assert parity["estimate"] is parity["fidelity"] is None
    assert result["symmetry"]["sector"] is None
    assert result["rows"][0]["energy"] is not None


def test_zero_accepted_shots_is_explicitly_unavailable(monkeypatch):
    import core.benchmark as module
    source = x_run(shots=1)
    # Force one sampled outcome rejected by the odd parity sector, independently
    # of the density matrix, to exercise the finite-shot failure path.
    real_simulator = module.AerSimulator

    class Execution:
        success = True
        def __init__(self, result): self.result = result
        def get_counts(self): return {"0": 1}
        def data(self): return self.result.data()

    class Job:
        def __init__(self, job): self.job = job
        def result(self): return Execution(self.job.result())

    class Simulator:
        def __init__(self, **kwargs): self.real = real_simulator(**kwargs)
        def run(self, *args, **kwargs): return Job(self.real.run(*args, **kwargs))

    monkeypatch.setattr(module, "AerSimulator", Simulator)
    result = mitigation_benchmark(source)
    parity = result["rows"][-1]
    assert parity["status"] == "unavailable"
    assert parity["retained_shots"] == 0
    assert parity["fidelity"] is None


@pytest.mark.parametrize("kwargs", [
    {"qubit": 1}, {"shots": 0}, {"shots": 1_000_001}, {"seed": 2**32},
    {"scale_factors": [1, 2, 3]}, {"scale_factors": [1, 3]},
    {"scale_factors": [1, 3, 11]}, {"scale_factors": [1, 3, 3]},
])
def test_benchmark_rejects_unsupported_or_unbounded_inputs(kwargs):
    with pytest.raises(ValueError):
        mitigation_benchmark(x_run(shots=16), **kwargs)


def test_cancel_before_and_between_samples():
    source = x_run(shots=16)
    with pytest.raises(SimulationCancelled):
        mitigation_benchmark(source, is_cancelled=lambda: True)
    progress = []
    with pytest.raises(SimulationCancelled):
        mitigation_benchmark(source, progress=progress.append,
                             is_cancelled=lambda: bool(progress and progress[-1] >= 30))


def test_run_reproduction_uses_effective_seed_and_has_no_mitigation_claim():
    source = x_run(seed=None, shots=32)
    metadata = source.result.metadata
    replay = metadata["reproduction"]
    assert replay["config"]["seed"] == metadata["effective_seed"]
    assert replay["mitigation_method"] == "none"
    assert replay["simulation_method"] == "density_matrix"
    assert config_from_dict(replay["config"]).noise == source.config.noise


def test_bell_parity_conditional_fidelity_against_independent_channel_prediction():
    source = run_experiment(replace(
        create_example_config("bell"), shots=1024,
        noise=NoiseConfig(p1=.1, p2=.2),
    ))
    result = mitigation_benchmark(source)
    baseline, _, _, parity = result["rows"]
    # One local depolarizing channel after H, then a two-qubit channel after CX.
    expected_fidelity = (1 - .2) * (1 - .1 / 2) + .2 / 4
    expected_acceptance = 1 - .2 / 2
    assert baseline["fidelity"] == pytest.approx(expected_fidelity)
    assert result["symmetry"]["ensemble_acceptance"] == pytest.approx(expected_acceptance)
    assert parity["fidelity"] == pytest.approx(expected_fidelity / expected_acceptance)


def test_benchmark_rejects_failed_source():
    source = x_run(shots=16)
    source.result.error = "Falha anterior"
    with pytest.raises(ValueError, match="origem falhou"):
        mitigation_benchmark(source)


def test_standalone_zne_retains_replayable_raw_samples():
    from qiskit import QuantumCircuit
    from core.mitigation import run_zne
    circuit = QuantumCircuit(1)
    circuit.x(0)
    result = run_zne(circuit, None, shots=16, seed=2**32 - 1)
    assert [s["effective_seed"] for s in result["samples"]] == [2**32 - 1, 0, 1]
    assert [s["counts"] for s in result["samples"]] == [{"1": 16}] * 3
    assert result["optimization_level"] == 0
    assert result["native_circuit"]["operations"][0]["name"] == "u"
    assert isinstance(result["native_circuit"]["global_phase"], float)
