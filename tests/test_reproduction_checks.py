from copy import deepcopy
from dataclasses import replace
import numpy as np
import pytest

from core.examples import create_example_config
from core.simulation import run_experiment
from core.reproduction import compare_reproduction, scientific_context
from core.types import NoiseConfig, ExperimentConfig, SystemConfig, SimulationProtocol, config_from_dict
from tests.qt_helpers import execute, wait_until


def test_reproduction_separates_state_agreement_from_sampling():
    config = replace(create_example_config("depolarizing-bell"),shots=32)
    source = run_experiment(config)
    reproduced = run_experiment(config)
    check = compare_reproduction(source,reproduced)
    assert check["status"] == "matched" and check["counts_match"]
    altered = replace(reproduced,result=replace(reproduced.result,counts={"00":32}))
    assert compare_reproduction(source,altered)["status"] == "matched"
    assert not compare_reproduction(source,altered)["counts_match"]
    different = run_experiment(replace(config,noise=replace(config.noise,p1=.15)))
    assert compare_reproduction(source,different)["status"] == "different"
    without = replace(source,result=replace(source.result,final_state=None))
    assert compare_reproduction(without,reproduced)["status"] == "unavailable"


def test_same_seed_does_not_define_ensemble_uncertainty():
    source = run_experiment(replace(create_example_config("depolarizing-bell"),shots=32,seed=42))
    other = run_experiment(replace(source.config,seed=108))
    np.testing.assert_allclose(source.result.final_state.data,other.result.final_state.data)
    assert source.result.fidelity == pytest.approx(other.result.fidelity)
    assert source.result.metadata["input_fingerprint"] != other.result.metadata["input_fingerprint"]
    assert "seed afeta" in scientific_context(source)


def test_ui_reexecute_records_numerical_check(window):
    window.page_simulation.config_panel.load_config(replace(create_example_config("bell"),shots=32))
    source = execute(window)
    original = window.repository._path(source.id).read_bytes()
    window._rerun_current()
    wait_until(lambda: window._current_worker is None)
    check = window._current_experiment.result.metadata["reproduction_check"]
    assert check["source_id"] == source.id and check["status"] == "matched"
    assert "compatível" in window.page_results.reproduction_status.text()
    assert window.repository._path(source.id).read_bytes() == original


def test_thermal_gate_duration_is_physical_and_backwards_compatible():
    config = ExperimentConfig(SystemConfig(1,J=0,h=0,initial_state="plus"),SimulationProtocol(),
                              NoiseConfig(kind="Termico",t1_us=1,t2_us=1,gate_time_1q_ns=100),shots=32)
    source = run_experiment(config)
    other = run_experiment(replace(config,noise=replace(config.noise,gate_time_1q_ns=1000)))
    assert source.result.fidelity > other.result.fidelity
    assert source.result.metadata["thermal_gate_durations_ns"] == {"1q":100,"2q":50}
    assert "100 ns" in scientific_context(source)
    from dataclasses import asdict
    raw = asdict(config)
    raw["noise"].pop("gate_time_1q_ns")
    raw["noise"].pop("gate_time_2q_ns")
    assert config_from_dict(raw).noise.gate_time_1q_ns == 50
    with pytest.raises(ValueError,match="positivas"):
        replace(config.noise,gate_time_1q_ns=0).validate()


def test_reproducing_zne_checks_estimator_instead_of_inherited_state(window):
    window.page_simulation.config_panel.load_config(replace(create_example_config("depolarizing-bell"),shots=32))
    execute(window)
    window._run_mitigation(0,"linear",64)
    wait_until(lambda: window._current_worker is None)
    source = window._current_experiment
    assert source.result.mitigation["provenance"]["simulation_method"] == "density_matrix"
    window._rerun_current()
    wait_until(lambda: window._current_worker is None)
    copied = window._current_experiment
    check = copied.result.metadata["reproduction_check"]
    assert check["kind"] == "zne" and check["status"] == "matched"
    assert copied.id != source.id and check["source_id"] == source.id
    assert "Reprodução da ZNE" in window.page_results.reproduction_status.text()


def test_two_qubit_thermal_duration_matches_independent_amplitude_decay():
    from core.circuit_document import CircuitDocument, CircuitGate
    document = CircuitDocument(2,(CircuitGate("x",(0,)),CircuitGate("cx",(0,1))))
    noise = NoiseConfig(kind="Termico",t1_us=1,t2_us=1,gate_time_1q_ns=100,gate_time_2q_ns=300)
    config = ExperimentConfig(SystemConfig(2),SimulationProtocol(2,2),noise,32,42,document)
    result = run_experiment(config).result
    assert result.final_state.probabilities()[3] == pytest.approx(np.exp(-.1)*np.exp(-2*.3),abs=1e-12)
    assert result.metadata["thermal_gate_time_ns"] is None
