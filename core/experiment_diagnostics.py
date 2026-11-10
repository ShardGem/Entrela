"""Analytical, non-blocking guidance about the configured ideal experiment.

These checks never run the simulator or alter a configuration. A stationary
exact evolution does not imply stationarity after Trotter approximation or noise.
"""

from dataclasses import dataclass

import numpy as np

from core.analysis import initial_state
from core.circuits import _build_hamiltonian


@dataclass(frozen=True)
class ExperimentDiagnostic:
    code: str
    title: str
    message: str
    severity: str = "info"


def diagnose_experiment(config, *, atol=1e-10):
    """Explain degenerate/reference cases without rejecting valid experiments.

    ``atol`` is an absolute numerical tolerance for the zero-Hamiltonian and
    eigenstate checks. Commutation is checked from the actual Pauli terms.
    Free circuits have no Hamiltonian evolution, so these notices do not apply.
    """
    config.validate()
    if not np.isfinite(atol) or atol <= 0:
        raise ValueError("A tolerância deve ser positiva e finita")
    if config.circuit is not None:
        return ()
    system = config.system
    hamiltonian = _build_hamiltonian(
        system.num_qubits, system.hamiltonian, system.J, system.h, system.periodic
    )
    matrix = hamiltonian.to_matrix()
    state = initial_state(system).data
    notices = []
    is_zero = np.linalg.norm(matrix, ord=2) <= atol
    if is_zero:
        notices.append(ExperimentDiagnostic(
            "zero_hamiltonian", "Hamiltoniano nulo",
            "H é numericamente nulo: a evolução ideal exata mantém o estado inicial. "
            "É um caso de controle válido, mas não revela erro de Trotter. "
            "O ruído nas operações executadas, inclusive na preparação, ainda pode alterar o estado."
        ))
    else:
        applied = matrix @ state
        energy = float(np.vdot(state, applied).real)
        residual = float(np.linalg.norm(applied - energy * state))
        # Relative scaling avoids interpreting a large-energy numerical residual
        # as a physically meaningful departure from an eigenstate.
        stationary = residual <= atol * max(1., float(np.linalg.norm(applied)))
        if stationary:
            notices.append(ExperimentDiagnostic(
                "stationary_initial_state", "Estado inicial é autoestado de H",
                f"A evolução ideal exata permanece no mesmo estado físico, até uma fase global "
                f"(energia {energy:.8g}, resíduo numérico {residual:.3g}). "
                "Uma aproximação de Trotter com termos não comutantes ou o ruído pode produzir mudanças."
            ))
        terms = [(pauli, coefficient) for pauli, coefficient in
                 zip(hamiltonian.paulis, hamiltonian.coeffs) if abs(coefficient) > 0]
        commuting = all(a.commutes(b) for index, (a, _) in enumerate(terms)
                        for b, _ in terms[index + 1:])
        if commuting:
            notices.append(ExperimentDiagnostic(
                "commuting_terms", "Termos do Hamiltoniano comutam",
                "O produto de Trotter representa a evolução ideal exata neste Hamiltoniano, "
                "salvo arredondamento numérico. Aumentar os passos não reduz um erro ideal "
                "de Trotter neste caso e pode aumentar a exposição ao ruído."
            ))
        if not stationary and all(set(pauli.to_label()) <= {"I", "Z"} for pauli, _ in terms):
            notices.append(ExperimentDiagnostic(
                "constant_z_populations", "Probabilidades em Z permanecem constantes no ideal",
                "H é diagonal na base computacional: as fases e coerências podem evoluir "
                "sem mudar as probabilidades em Z. Observe a matriz densidade ou outras bases; "
                "com ruído, as probabilidades também podem mudar."
            ))
    if system.initial_state == "bell":
        notices.append(ExperimentDiagnostic(
            "bell_local_bloch_zero", "Bell ideal tem vetores de Bloch locais nulos",
            "Na preparação ideal de Bell, cada qubit isolado tem ρ = I/2 e vetor de Bloch zero, "
            "embora o estado global seja puro e emaranhado. Inspecione o estado global e suas "
            "correlações. O estado após evolução e ruído deve ser avaliado pelos dados simulados."
        ))
    return tuple(notices)
