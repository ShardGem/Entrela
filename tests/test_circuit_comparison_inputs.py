"""Compare only execution inputs which actually affect the selected run type."""

from dataclasses import replace
import numpy as np
import pytest

from core.circuit_document import CircuitDocument, CircuitGate
from core.comparison import incompatibility, prepare_comparison
from core.simulation import run_experiment
from core.types import ExperimentConfig, SystemConfig, SimulationProtocol, NoiseConfig


def circuit_config():
    return ExperimentConfig(
        SystemConfig(2), SimulationProtocol(2., 2, True, 2),
        NoiseConfig(enabled=False), shots=32, seed=42,
        circuit=CircuitDocument(2, (CircuitGate("h", (0,)), CircuitGate("cx", (0, 1)))),
    )


def test_free_circuits_ignore_unused_hamiltonian_state_and_trotter_fields():
    config = circuit_config()
    a = run_experiment(config)
    b = run_experiment(replace(
        config,
        system=SystemConfig(2, "XY", J=17, h=-3, periodic=True, initial_state="plus"),
        protocol=replace(config.protocol, trotter_order=4),
    ))
    np.testing.assert_allclose(a.result.final_state.data, b.result.final_state.data)
    assert a.result.counts == b.result.counts
    assert incompatibility(a, b) == ""
    data = prepare_comparison([a, b])
    assert data["synchronous"]
    assert all(point["energy"] is None for curve in data["curves"] for point in curve)
    assert "mesmo Hamiltoniano" in incompatibility(a, b, mode="trotter")


def test_free_circuits_still_require_same_document_and_qubit_count():
    config = circuit_config()
    a = run_experiment(config)
    b = run_experiment(replace(config, circuit=CircuitDocument(2, (CircuitGate("x", (0,)), CircuitGate("cx", (0, 1))))))
    assert "Circuitos diferentes" in incompatibility(a, b)
    one = run_experiment(ExperimentConfig(
        SystemConfig(1), SimulationProtocol(1., 1), NoiseConfig(enabled=False), 32, 42,
        CircuitDocument(1, (CircuitGate("h", (0,)),)),
    ))
    assert "quantidades diferentes" in incompatibility(a, one)
    with pytest.raises(ValueError, match="Circuitos diferentes"):
        prepare_comparison([a, b])


def test_run_types_failure_and_self_comparison_remain_rejected():
    a = run_experiment(circuit_config())
    hamiltonian = run_experiment(replace(circuit_config(), circuit=None))
    assert "Tipos de execução diferentes" in incompatibility(a, hamiltonian)
    assert "dois registros diferentes" in incompatibility(a, a)
    failed = replace(a, id="another", result=replace(a.result, error="Falhou"))
    assert "erro" in incompatibility(a, failed)
    assert "Modo de comparação inválido" in incompatibility(a, failed, mode="unknown")


def test_hamiltonian_comparison_preserves_system_and_protocol_controls():
    config = replace(circuit_config(), circuit=None)
    a = run_experiment(config)
    other_h = run_experiment(replace(config, system=replace(config.system, h=.8)))
    assert "Sistemas diferentes" in incompatibility(a, other_h)
    assert "Sistemas diferentes" in incompatibility(a, other_h, mode="trotter")
    other_depth = run_experiment(replace(config, protocol=replace(config.protocol, trotter_steps=3)))
    assert "Protocolos" in incompatibility(a, other_depth)
    assert incompatibility(a, other_depth, mode="trotter") == ""
