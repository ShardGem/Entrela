"""Compatibility and derived state data for side-by-side inspection."""

import numpy as np
from core.analysis import checkpoint, exact_states
from core.circuits import _build_hamiltonian
from core.metrics import bloch_vector, fidelity, purity, energy_expectation


def incompatibility(a,b, *, mode="controlled"):
    if mode not in ("controlled", "trotter"):
        return "Modo de comparação inválido."
    if a.id == b.id:
        return "Selecione dois registros diferentes."
    if a.result.error or b.result.error:
        return "Execuções com erro não são comparáveis."
    free_a, free_b = a.config.circuit is not None, b.config.circuit is not None
    if free_a != free_b:
        return "Tipos de execução diferentes: compare dois circuitos livres ou duas evoluções de Hamiltoniano."
    if free_a and a.config.system.num_qubits != b.config.system.num_qubits:
        return "Circuitos com quantidades diferentes de qubits."
    # Free circuits start from |0…0> and use the document's gates. Hamiltonian,
    # J, h, boundary and SystemConfig.initial_state do not enter that execution.
    if not free_a and a.config.system != b.config.system:
        return "Sistemas diferentes: iguale qubits, Hamiltoniano, J, h, fronteira e estado inicial."
    if a.config.circuit != b.config.circuit:
        return "Circuitos diferentes: compare a mesma sequência de portas."
    pa,pb=a.config.protocol,b.config.protocol
    if mode == "trotter" and (a.config.circuit is not None or pa.total_time != pb.total_time):
        return "Compare evoluções do mesmo Hamiltoniano e tempo total para variar passos ou ordem de Trotter."
    if mode == "controlled" and not free_a and (pa.total_time,pa.trotter_steps,pa.trotter_order)!=(pb.total_time,pb.trotter_steps,pb.trotter_order):
        return "Protocolos de evolução diferentes: iguale tempo, passos e ordem."
    return ""


def prepare_comparison(experiments,progress=None,is_cancelled=None, *, mode="controlled"):
    a,b=experiments
    error=incompatibility(a,b,mode=mode)
    if error:
        raise ValueError(error)
    vectors, ideals, curves=[],[],[]
    for i,exp in enumerate(experiments):
        r,c=exp.result,exp.config
        states=r.states or ([r.final_state] if r.final_state is not None else [])
        if not states:
            raise ValueError("Um dos registros não contém estados; reexecute a simulação para comparar Bloch.")
        targets=r.ideal_statevectors or ([r.ideal_final_state] if r.ideal_final_state is not None else [])
        H=None if c.circuit else _build_hamiltonian(c.system.num_qubits,c.system.hamiltonian,c.system.J,c.system.h,c.system.periodic)
        exact = exact_states(c,r.times if r.states else [c.protocol.total_time]) if mode == "trotter" else None
        local,reference,series=[],[],[]
        for index,state in enumerate(states):
            checkpoint(is_cancelled,progress,int(50*i+50*index/len(states)))
            target=targets[index] if len(targets)==len(states) else None
            local.append([bloch_vector(state,q) for q in range(c.system.num_qubits)])
            reference.append([bloch_vector(target,q) for q in range(c.system.num_qubits)] if target is not None else None)
            series.append(dict(time=r.times[index] if r.states else c.protocol.total_time,
                               fidelity=None if target is None else fidelity(state,target),
                               purity=purity(state),energy=None if H is None else energy_expectation(state,H)))
            if exact is not None:
                series[-1]["fidelity_exact"] = fidelity(state,exact[index])
        vectors.append(local)
        ideals.append(reference)
        curves.append(series)
    synchronous=(bool(a.result.states) and bool(b.result.states) and len(a.result.states)==len(b.result.states)
                 and np.allclose(a.result.times,b.result.times,rtol=0,atol=1e-12))
    checkpoint(is_cancelled,progress,100)
    return dict(experiments=list(experiments),vectors=vectors,ideal_vectors=ideals,curves=curves,synchronous=bool(synchronous),mode=mode)
