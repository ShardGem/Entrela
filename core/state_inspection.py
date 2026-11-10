"""Exact diagnostics of an already simulated state; no execution or tomography."""

from numbers import Integral

import numpy as np
from qiskit.quantum_info import DensityMatrix, Statevector, entropy, negativity, partial_trace

from core.metrics import fidelity, purity


def state_density(state):
    """Validate the supported qubit state and return an independent density matrix."""
    if not isinstance(state, (Statevector, DensityMatrix)):
        raise TypeError("Use um Statevector ou DensityMatrix do estado simulado")
    if state.num_qubits is None or not 1 <= state.num_qubits <= 6 or any(d != 2 for d in state.dims()):
        raise ValueError("O inspetor aceita estados de 1 a 6 qubits")
    if not np.all(np.isfinite(state.data)) or not state.is_valid():
        raise ValueError("Estado inválido: verifique normalização, positividade e traço")
    return DensityMatrix(np.array(DensityMatrix(state).data, copy=True))


def inspect_state(state, ideal=None, partition=None):
    """Return global and selected A|B quantities from the supplied density matrix.

    Coherence is the unnormalised l1 norm of off-diagonal entries in the
    computational basis. Negativity is for the selected bipartition; zero is
    not a general proof of separability. No positivity projection is applied.
    """
    rho = state_density(state)
    n = rho.num_qubits
    target = state_density(ideal) if ideal is not None else None
    if target is not None and target.dim != rho.dim:
        raise ValueError("A referência ideal deve ter a mesma quantidade de qubits")
    matrix = rho.data
    result = {
        "num_qubits": n,
        "density_matrix": matrix.copy(),
        "purity": purity(rho),
        "entropy_bits": float(entropy(rho, base=2)),
        "coherence_l1": float(np.abs(matrix - np.diag(np.diag(matrix))).sum()),
        "eigenvalues": np.linalg.eigvalsh(matrix)[::-1],
        "fidelity": fidelity(rho, target) if target is not None else None,
        "partition": None,
    }
    if n == 1:
        if partition is not None:
            raise ValueError("Uma bipartição exige pelo menos dois qubits")
        return result
    selected = (0,) if partition is None else tuple(partition)
    if (not selected or len(selected) >= n or len(set(selected)) != len(selected)
            or any(not isinstance(q, Integral) or isinstance(q, bool) or not 0 <= q < n for q in selected)):
        raise ValueError("Selecione uma parte A não vazia e diferente do sistema completo")
    selected = tuple(sorted(int(q) for q in selected))
    other = tuple(q for q in range(n) if q not in selected)
    rho_a, rho_b = partial_trace(rho, other), partial_trace(rho, selected)
    entropy_a, entropy_b = float(entropy(rho_a, base=2)), float(entropy(rho_b, base=2))
    result["partition"] = {
        "a": selected,
        "b": other,
        "purity_a": purity(rho_a),
        "entropy_a_bits": entropy_a,
        "entropy_b_bits": entropy_b,
        "negativity": float(negativity(rho, selected)),
        "mutual_information_bits": entropy_a + entropy_b - result["entropy_bits"],
    }
    return result
