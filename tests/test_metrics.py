import numpy as np
import pytest
from qiskit.quantum_info import Statevector, DensityMatrix, SparsePauliOp
from core.metrics import fidelity, purity, energy_expectation, bloch_vector


def test_fidelity_identical():
    sv = Statevector([1, 0])
    assert abs(fidelity(sv, sv) - 1.0) < 1e-9


def test_fidelity_orthogonal():
    a = Statevector([1, 0])
    b = Statevector([0, 1])
    assert abs(fidelity(a, b)) < 1e-9


def test_purity_pure_state():
    sv = Statevector([1 / np.sqrt(2), 1 / np.sqrt(2)])
    assert abs(purity(sv) - 1.0) < 1e-9


def test_y_observable_and_bloch_orientation_are_consistent():
    # A Z-basis histogram cannot determine this expectation value.
    state = Statevector([1, 1j]) / np.sqrt(2)
    assert energy_expectation(state, SparsePauliOp("Y")) == pytest.approx(1)
    assert bloch_vector(state, 0) == pytest.approx([0, 1, 0])


def test_entangled_pure_state_has_mixed_local_qubits():
    state = Statevector([1, 0, 0, 1]) / np.sqrt(2)
    assert purity(state) == pytest.approx(1)
    assert bloch_vector(state, 0) == pytest.approx([0, 0, 0])
    assert bloch_vector(state, 1) == pytest.approx([0, 0, 0])


@pytest.mark.parametrize("state", [Statevector([1, 1]), DensityMatrix([[1.1, 0], [0, -0.1]])])
def test_metrics_reject_nonphysical_states(state):
    for function in (purity, lambda value: bloch_vector(value, 0),
                     lambda value: energy_expectation(value, np.eye(2))):
        with pytest.raises(ValueError, match="inválido"):
            function(state)


@pytest.mark.parametrize("observable", [np.array([[0, 1], [0, 0]]), np.diag([1, 1j])])
def test_energy_rejects_nonhermitian_observables(observable):
    with pytest.raises(ValueError, match="hermitiano"):
        energy_expectation(Statevector([1, 0]), observable)


@pytest.mark.parametrize("observable", [np.eye(4), np.diag([1, np.nan])])
def test_energy_rejects_wrong_dimension_or_nonfinite_observables(observable):
    with pytest.raises(ValueError, match="dimensão"):
        energy_expectation(Statevector([1, 0]), observable)
