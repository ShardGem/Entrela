import numpy as np
from qiskit.quantum_info import Statevector
from core.metrics import fidelity, purity, energy_expectation


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
