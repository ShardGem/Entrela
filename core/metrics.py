"""Squared Uhlmann fidelity and exact state observables."""
from qiskit.quantum_info import Statevector, DensityMatrix, state_fidelity
from qiskit.quantum_info import purity as qiskit_purity

def _validate(state):
    if not isinstance(state,(Statevector,DensityMatrix)):
        raise TypeError("Tipo de estado não suportado")
    if not state.is_valid():
        raise ValueError("Estado quântico inválido")

def fidelity(state_a,state_b):
    _validate(state_a)
    _validate(state_b)
    return min(1.,max(0.,float(state_fidelity(state_a,state_b))))

def purity(state):
    _validate(state)
    return min(1.,max(0.,float(qiskit_purity(state).real)))

def energy_expectation(state,hamiltonian):
    _validate(state)
    return float(state.expectation_value(hamiltonian).real)
