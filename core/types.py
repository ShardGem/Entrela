"""Scientific configuration is immutable; results belong to individual runs."""

from __future__ import annotations
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from math import isfinite
from typing import Literal
from uuid import uuid4
from core.circuit_document import CircuitDocument

HamiltonianType = Literal["Ising", "Heisenberg", "XY", "XXZ", "Custom"]
NoiseType = Literal["Despolarizador", "Termico"]


def finite(value, name):
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not isfinite(value)
    ):
        raise ValueError(f"{name} deve ser um número finito")


def integer(value, name, minimum=1):
    if type(value) is not int or value < minimum:
        raise ValueError(f"{name} deve ser inteiro ≥ {minimum}")


@dataclass(frozen=True)
class SystemConfig:
    num_qubits: int = 2
    hamiltonian: HamiltonianType = "Ising"
    J: float = 1.0
    h: float = 0.5
    periodic: bool = False
    initial_state: str = "zero"

    def validate(self):
        integer(self.num_qubits, "Qubits")
        if self.num_qubits > 6:
            raise ValueError("São suportados de 1 a 6 qubits")
        if self.hamiltonian not in ("Ising", "Heisenberg", "XY", "XXZ", "Custom"):
            raise ValueError("Hamiltoniano não suportado")
        finite(self.J, "J")
        finite(self.h, "h")
        if type(self.periodic) is not bool:
            raise ValueError("Condições periódicas inválidas")
        if self.initial_state not in ("zero", "plus", "bell"):
            raise ValueError("Estado inicial não suportado")
        if self.initial_state == "bell" and self.num_qubits != 2:
            raise ValueError("Bell requer exatamente 2 qubits")


@dataclass(frozen=True)
class SimulationProtocol:
    total_time: float = 1.0
    trotter_steps: int = 4
    save_snapshots: bool = True
    trotter_order: int = 2

    def validate(self):
        finite(self.total_time, "Tempo")
        if self.total_time <= 0:
            raise ValueError("Tempo deve ser positivo")
        integer(self.trotter_steps, "Passos")
        if self.trotter_steps > 200:
            raise ValueError("Limite de 200 passos por execução")
        if type(self.trotter_order) is not int or self.trotter_order not in (2, 4):
            raise ValueError("Ordem Suzuki deve ser 2 ou 4")
        if type(self.save_snapshots) is not bool:
            raise ValueError("Salvar estados deve ser booleano")


@dataclass(frozen=True)
class NoiseConfig:
    enabled: bool = True
    kind: NoiseType = "Despolarizador"
    p1: float = 0.01
    p2: float = 0.05
    t1_us: float = 50.0
    t2_us: float = 30.0
    gate_time_1q_ns: float = 50.0
    gate_time_2q_ns: float = 50.0

    def validate(self):
        if type(self.enabled) is not bool or self.kind not in (
            "Despolarizador",
            "Termico",
        ):
            raise ValueError("Modelo de ruído inválido")
        for name in ("p1", "p2", "t1_us", "t2_us", "gate_time_1q_ns", "gate_time_2q_ns"):
            finite(getattr(self, name), name)
        if not self.enabled:
            return
        if self.kind == "Despolarizador":
            for name in ("p1", "p2"):
                value = getattr(self, name)
                finite(value, name)
                if not 0 <= value <= 1:
                    raise ValueError(f"{name} deve estar em [0, 1]")
        else:
            if self.gate_time_1q_ns <= 0 or self.gate_time_2q_ns <= 0:
                raise ValueError("Durações das portas térmicas devem ser positivas")
            finite(self.t1_us, "T₁")
            finite(self.t2_us, "T₂")
            if self.t1_us <= 0 or self.t2_us <= 0:
                raise ValueError("T₁ e T₂ devem ser positivos")
            if self.t2_us > 2 * self.t1_us:
                raise ValueError(
                    f"T₂ deve ser ≤ 2T₁. Máximo permitido: {2 * self.t1_us:g} µs"
                )


@dataclass(frozen=True)
class ExperimentConfig:
    system: SystemConfig
    protocol: SimulationProtocol
    noise: NoiseConfig
    shots: int = 8192
    seed: int | None = None
    circuit: CircuitDocument | None = None

    def validate(self):
        if self.circuit is not None:
            self.circuit.validate()
            if self.protocol.trotter_steps != max(
                1, len(self.circuit.gates)
            ) or self.protocol.total_time != float(max(1, len(self.circuit.gates))):
                raise ValueError(
                    "Circuitos livres usam índices das portas no protocolo"
                )
            if self.circuit.num_qubits != self.system.num_qubits:
                raise ValueError(
                    "Circuito e sistema têm quantidades diferentes de qubits"
                )
        self.system.validate()
        self.protocol.validate()
        self.noise.validate()
        integer(self.shots, "Shots")
        if self.shots > 1_000_000:
            raise ValueError("Limite de 1.000.000 shots por execução")
        if self.seed is not None:
            integer(self.seed, "Semente", 0)
            if self.seed >= 2**32:
                raise ValueError("Semente deve estar entre 0 e 4294967295")


def config_from_dict(raw):
    try:
        config = ExperimentConfig(
            SystemConfig(**raw["system"]),
            SimulationProtocol(**raw["protocol"]),
            NoiseConfig(**raw["noise"]),
            raw.get("shots", 8192),
            raw.get("seed"),
            CircuitDocument.from_dict(raw["circuit"])
            if raw.get("circuit") is not None
            else None,
        )
        config.validate()
        return config
    except (TypeError, KeyError, AttributeError) as exc:
        raise ValueError("Configuração inválida ou incompleta") from exc


@dataclass
class ExperimentResult:
    counts: dict | None = None
    statevectors: list | None = None
    density_matrices: list | None = None
    ideal_statevectors: list | None = None
    final_state: object | None = None
    ideal_final_state: object | None = None
    labels: list | None = None
    times: list | None = None
    fidelity: float | None = None
    purity: float | None = None
    energy: float | None = None
    circuit_text: str = ""
    circuit_depth: int = 0
    metadata: dict = field(default_factory=dict)
    mitigation: dict | None = None
    error: str | None = None

    @property
    def states(self):
        return self.density_matrices or self.statevectors or []


@dataclass
class Experiment:
    config: ExperimentConfig
    result: ExperimentResult = field(default_factory=ExperimentResult)
    id: str = field(default_factory=lambda: uuid4().hex[:12])
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    duration_s: float = 0.0
    tags: list = field(default_factory=list)


def resource_estimate(config):
    """Raw complex-array storage; excludes JSON, solver and GUI overhead."""
    snapshots = (
        config.protocol.trotter_steps + 1 if config.protocol.save_snapshots else 0
    )
    dim = 2**config.system.num_qubits
    stored = (snapshots + 1) * (dim * dim if config.noise.enabled else dim)
    stored += (snapshots + 1) * dim
    return {"snapshots": snapshots, "state_bytes": stored * 16}


def system_label(config):
    return "Circuito livre" if config.circuit is not None else config.system.hamiltonian
