"""Recorded circuit operations, with an explicit fallback for legacy records."""
from copy import deepcopy
from dataclasses import dataclass
from core.circuits import build_circuit, build_editor_circuit
from core.types import finite


@dataclass(frozen=True)
class CircuitInspection:
    operations: tuple
    global_phase: float | None
    reconstructed: bool


def execution_circuit(config):
    """Rebuild from configuration using the current execution builders."""
    if config.circuit is not None:
        return build_editor_circuit(config.circuit, save_snapshots=False, save_final=False)[0]
    system, protocol = config.system, config.protocol
    return build_circuit(system.num_qubits, system.hamiltonian, system.J, system.h,
                         system.periodic, protocol.total_time, protocol.trotter_steps, False,
                         initial_state=system.initial_state, trotter_order=protocol.trotter_order)[0]


def inspect_circuit(experiment):
    """Prefer recorded evidence; never parse ASCII or run a simulation.

    Reconstruction reflects the current library versions and is not proof of
    the exact historical gate decomposition. Missing phase is not inferred
    when the operations themselves were recorded.
    """
    metadata = experiment.result.metadata
    phase = metadata.get('circuit_global_phase')
    if phase is not None:
        finite(phase, 'Fase global')
        phase = float(phase)
    recorded = metadata.get('operations')
    if recorded:
        return CircuitInspection(tuple(deepcopy(recorded)), phase, False)
    if experiment.result.error:
        return CircuitInspection((), phase, False)
    circuit = execution_circuit(experiment.config)
    origins = circuit.metadata['origins']
    operations = tuple(dict(**origin, name=instruction.operation.name,
                            qubits=[circuit.find_bit(q).index for q in instruction.qubits],
                            parameters=[float(value) for value in instruction.operation.params])
                       for instruction, origin in zip(circuit.data, origins)
                       if not instruction.operation.name.startswith('save_'))
    return CircuitInspection(operations, phase if phase is not None else float(circuit.global_phase), True)
