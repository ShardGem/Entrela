"""Squared Uhlmann fidelity and exact state observables."""
from qiskit.quantum_info import Statevector, DensityMatrix, state_fidelity
from qiskit.quantum_info import purity as qiskit_purity
from qiskit.quantum_info import partial_trace
import numpy as np

def bloch_vector(state, qubit):
    if type(qubit) is not int or not 0 <= qubit < state.num_qubits:
        raise ValueError("Qubit fora do sistema")
    rho = DensityMatrix(partial_trace(state, [q for q in range(state.num_qubits) if q != qubit])).data
    return np.array([2 * rho[0, 1].real, -2 * rho[0, 1].imag, (rho[0, 0] - rho[1, 1]).real], float)

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
