"""Modelos de ruído com validação."""
from __future__ import annotations

from qiskit_aer.noise import NoiseModel, depolarizing_error, thermal_relaxation_error

from core.types import NoiseConfig


_GATE_TIME_NS = 50.0

# Gates de 1 qubit que podem aparecer
_SINGLE_QUBIT_GATES = [
    "u", "u1", "u2", "u3",
    "h", "x", "y", "z", "s", "sdg", "t", "tdg", "sx", "sxdg",
    "rx", "ry", "rz", "p",
    "id",
]

# Gates de 2 qubits que podem aparecer (inclui as rotações do PauliEvolutionGate)
_TWO_QUBIT_GATES = [
    "cx", "cz", "cy", "ch", "swap",
    "rxx", "ryy", "rzz", "rzx",
    "crx", "cry", "crz", "cp",
    "cu",
]


def build_noise_model(cfg: NoiseConfig) -> NoiseModel | None:
    """Constrói o NoiseModel do Qiskit Aer. Retorna None se ruído desabilitado."""
    cfg.validate()
    if not cfg.enabled:
        return None

    noise = NoiseModel()

    if cfg.kind == "Despolarizador":
        err1 = depolarizing_error(cfg.p1, 1)
        err2 = depolarizing_error(cfg.p2, 2)
        noise.add_all_qubit_quantum_error(err1, _SINGLE_QUBIT_GATES)
        noise.add_all_qubit_quantum_error(err2, _TWO_QUBIT_GATES)

    else:  # Termico
        t1_ns = cfg.t1_us * 1000.0
        t2_ns = cfg.t2_us * 1000.0
        err1 = thermal_relaxation_error(t1_ns, t2_ns, _GATE_TIME_NS)
        err2 = thermal_relaxation_error(t1_ns, t2_ns, _GATE_TIME_NS).tensor(
            thermal_relaxation_error(t1_ns, t2_ns, _GATE_TIME_NS)
        )
        noise.add_all_qubit_quantum_error(err1, _SINGLE_QUBIT_GATES)
        noise.add_all_qubit_quantum_error(err2, _TWO_QUBIT_GATES)

    return noise
