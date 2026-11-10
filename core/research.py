"""Bounded, reproducible investigations of sampling, extrapolation and noise."""

from dataclasses import asdict, replace
from secrets import randbits
from time import perf_counter
import numpy as np
from qiskit.quantum_info import Statevector, SparsePauliOp
from qiskit_aer import AerSimulator
from core.analysis import checkpoint, analysis_provenance, analysis_run_record, exact_states
from core.benchmark import _unitary
from core.metrics import fidelity
from core.mitigation import compile_unitary, _insert_identity_pairs, _expectation_z, fit_zne_samples, z_sampling_metadata
from core.noise import build_noise_model
from core.simulation import run_experiment
from core.types import integer


PARAMETERS = ("trotter_steps", "p1", "p2", "t1_us", "t2_us", "J", "h")


def varied_config(config, parameter, value):
    if parameter not in PARAMETERS or isinstance(value, bool) or not np.isfinite(value):
        raise ValueError("Parâmetro ou valor de estudo inválido.")
    if config.circuit is not None and parameter in ("J", "h", "trotter_steps"):
        raise ValueError("Circuito livre não possui parâmetros de Hamiltoniano/Trotter.")
    if parameter == "trotter_steps":
        if int(value) != value:
            raise ValueError("Passos devem ser inteiros.")
        result = replace(config, protocol=replace(config.protocol, trotter_steps=int(value)))
    elif parameter in ("J", "h"):
        result = replace(config, system=replace(config.system, **{parameter: float(value)}))
    else:
        kind = "Termico" if parameter in ("t1_us", "t2_us") else "Despolarizador"
        result = replace(config, noise=replace(config.noise, enabled=True, kind=kind, **{parameter: float(value)}))
    result.validate()
    return result


def heatmap_study(experiment, x_parameter="trotter_steps", x_values=(1, 2, 4, 8),
                  y_parameter="p2", y_values=(0, .02, .05, .1), progress=None, is_cancelled=None, *, seed=None):
    config = experiment.config
    config.validate()
    if experiment.result.error:
        raise ValueError("Escolha uma execução concluída.")
    xs, ys = list(x_values), list(y_values)
    if x_parameter == y_parameter:
        raise ValueError("Escolha dois parâmetros distintos.")
    if {x_parameter, y_parameter} & {"p1", "p2"} and {x_parameter, y_parameter} & {"t1_us", "t2_us"}:
        raise ValueError("Não misture parâmetros de dois modelos de ruído no mesmo mapa.")
    if any(not values or len(values) > 8 or len(set(values)) != len(values) for values in (xs, ys)):
        raise ValueError("Use de 1 a 8 valores distintos por eixo; máximo 64 pontos.")
    if seed is None:
        seed = experiment.result.metadata.get("effective_seed", config.seed)
    seed = randbits(32) if seed is None else seed
    integer(seed,"Semente",0)
    if seed>=2**32:
        raise ValueError("Semente deve ser menor que 2³².")
    configs = []
    for y in ys:
        for x in xs:
            cfg = replace(config, seed=seed, protocol=replace(config.protocol, save_snapshots=False))
            # Apply both thermal parameters together before validating the pair.
            if {x_parameter, y_parameter} == {"t1_us", "t2_us"}:
                cfg = replace(cfg, noise=replace(cfg.noise, enabled=True, kind="Termico", **{x_parameter: float(x), y_parameter: float(y)}))
                cfg.validate()
            else:
                cfg = varied_config(varied_config(cfg, x_parameter, x), y_parameter, y)
            configs.append((x, y, cfg))
    rows, runs = [], []
    for i, (x, y, cfg) in enumerate(configs):
        checkpoint(is_cancelled, progress, int(100 * i / len(configs)))
        exp = run_experiment(cfg, is_cancelled=is_cancelled)
        target = exact_states(cfg, [cfg.protocol.total_time])[0] if cfg.circuit is None else None
        rows.append(dict(x=float(x), y=float(y), fidelity=exp.result.fidelity,
                         purity=exp.result.purity, energy=exp.result.energy,
                         fidelity_exact=None if target is None else fidelity(exp.result.final_state, target),
                         depth=exp.result.circuit_depth, seed=seed, duration_s=exp.duration_s))
        runs.append(analysis_run_record(exp))
    checkpoint(is_cancelled, progress, 100)
    return dict(kind="heatmap", source_id=experiment.id, config=asdict(config),
                options=dict(x_parameter=x_parameter, x_values=xs, y_parameter=y_parameter, y_values=ys,seed=seed),
                rows=rows, runs=runs, provenance=analysis_provenance(experiment),
                note="Mapa de pontos efetivamente calculados, sem interpolação física. Fidelidade compara o circuito ideal do próprio ponto; fidelity_exact usa exp(−iHt). Variar ruído ativa o modelo correspondente. Cores de métricas do ensemble não representam incerteza de shots.")


def _prepare(experiment, qubit, seed, factors):
    config = experiment.config
    config.validate()
    if experiment.result.error:
        raise ValueError("Escolha uma execução concluída sem erro.")
    integer(qubit, "Qubit", 0)
    if qubit >= config.system.num_qubits:
        raise ValueError("Qubit fora do sistema.")
    if seed is None:
        seed = experiment.result.metadata.get("effective_seed", config.seed)
    seed = randbits(32) if seed is None else seed
    integer(seed, "Semente", 0)
    if seed >= 2**32:
        raise ValueError("Semente deve ser menor que 2³².")
    for fs in factors:
        if not 3 <= len(fs) <= 5 or len(set(fs)) != len(fs) or 1 not in fs:
            raise ValueError("Use de 3 a 5 fatores distintos, incluindo 1.")
        for f in fs:
            integer(f, "Fator")
            if f % 2 != 1 or f > 9:
                raise ValueError("Fatores devem ser ímpares entre 1 e 9.")
    native = compile_unitary(_unitary(config), seed)
    if len(native.data) * max(max(fs) for fs in factors) > 100000:
        raise ValueError("Limite de 100.000 portas por circuito folded.")
    label = ["I"] * native.num_qubits
    label[-1 - qubit] = "Z"
    ideal = float(np.real(Statevector.from_instruction(native).expectation_value(SparsePauliOp("".join(label)))))
    return native, ideal, seed


def _acquire(simulator, native, factor, shots, seed):
    folded = _insert_identity_pairs(native, (factor - 1) // 2)
    gates = dict(folded.count_ops())
    folded.measure_all()
    start = perf_counter()
    execution = simulator.run(folded, shots=shots, seed_simulator=seed).result()
    if not execution.success:
        raise RuntimeError(str(execution.status))
    counts = dict(execution.get_counts())
    return dict(scale_factor=factor, shots=shots, effective_seed=seed, counts=counts,
                acquisition_s=perf_counter() - start, gate_counts=gates)


def _summary(estimates, target):
    data = np.asarray(estimates, float)
    errors = data - target
    return dict(mean_estimate=float(data.mean()), bias=float(errors.mean()),
                sample_variance=float(data.var(ddof=1)), mse=float(np.mean(errors**2)),
                rmse=float(np.sqrt(np.mean(errors**2))), mean_absolute_error=float(np.abs(errors).mean()),
                stderr_mean=float(data.std(ddof=1) / np.sqrt(len(data))),
                out_of_range=int(np.sum(np.abs(data) > 1 + 1e-10)))


def sampling_study(experiment, *, mode="stability", factor_sets=((1, 3, 5), (1, 3, 7)),
                   shot_counts=(256, 1024), total_shots=3072, repetitions=5,
                   qubit=0, seed=None, progress=None, is_cancelled=None):
    """Independent sampled replicates; ZNE fits share samples within each replicate.

    Equal budget allocates exactly total_shots to baseline and to each ZNE fit.
    Linear/quadratic fits share acquisition, not independent method samples.
    """
    if mode not in ("stability", "budget"):
        raise ValueError("Estudo não suportado.")
    integer(repetitions, "Repetições", 2)
    if repetitions > 10:
        raise ValueError("Use de 2 a 10 repetições independentes.")
    sets = [list(fs) for fs in factor_sets]
    counts = list(shot_counts)
    if not sets or len(sets) > 3 or len({tuple(fs) for fs in sets}) != len(sets):
        raise ValueError("Use de 1 a 3 conjuntos distintos de fatores.")
    if mode == "budget":
        integer(total_shots, "Orçamento total", max(len(fs) for fs in sets))
        counts = [total_shots]
    if not counts or len(counts) > 3 or len(set(counts)) != len(counts):
        raise ValueError("Use de 1 a 3 quantidades distintas de shots.")
    for shots in counts:
        integer(shots, "Shots")
        if shots > 1_000_000:
            raise ValueError("Limite de 1.000.000 shots.")
    if len(sets) * len(counts) * repetitions > 60:
        raise ValueError("Limite de 60 aquisições de conjuntos por estudo.")
    checkpoint(is_cancelled, progress, 0)
    native, target, base_seed = _prepare(experiment, qubit, seed, sets)
    simulator = AerSimulator(method="density_matrix", noise_model=build_noise_model(experiment.config.noise), max_parallel_threads=2)
    rows, runs = [], []
    job = 0
    total = len(sets) * len(counts) * repetitions
    for factors in sets:
        for shots in counts:
            estimates = {"zne_linear": [], "zne_quadratic": []}
            if mode == "budget":
                estimates["none"] = []
            reported = {method: [] for method in estimates}
            acquisition = {method: 0.0 for method in estimates}
            processing = {method: 0.0 for method in estimates}
            elapsed = 0.0
            allocation = [shots] * len(factors) if mode == "stability" else [shots // len(factors) + (i < shots % len(factors)) for i in range(len(factors))]
            for repeat in range(repetitions):
                checkpoint(is_cancelled, progress, int(100 * job / total))
                run_seed = (base_seed + 17 * job) % 2**32
                samples = []
                if mode == "budget":
                    sample = _acquire(simulator, native, 1, shots, run_seed)
                    sample.update(z_sampling_metadata([sample], native.num_qubits, qubit))
                    mean = _expectation_z(sample["counts"], native.num_qubits, qubit)
                    estimates["none"].append(mean)
                    reported["none"].append(float(np.sqrt(max(0., 1 - mean**2) / shots)))
                    samples.append(dict(sample, role="baseline"))
                    acquisition["none"] += sample["acquisition_s"]
                means, errors = [], []
                for i, (factor, allocated) in enumerate(zip(factors, allocation)):
                    checkpoint(is_cancelled, None, 0)
                    sample = _acquire(simulator, native, factor, allocated, (run_seed + i + 1) % 2**32)
                    sample.update(z_sampling_metadata([sample], native.num_qubits, qubit))
                    mean = _expectation_z(sample["counts"], native.num_qubits, qubit)
                    means.append(mean)
                    errors.append(float(np.sqrt(max(0., 1 - mean**2) / allocated)))
                    samples.append(dict(sample, role="zne"))
                fits = {}
                sampling = z_sampling_metadata([s for s in samples if s["role"] == "zne"], native.num_qubits, qubit)
                for method in ("linear", "quadratic"):
                    fit_start=perf_counter()
                    fit = fit_zne_samples(factors, means, errors, method)
                    fit.update(sampling)
                    processing["zne_"+method] += perf_counter()-fit_start
                    acquisition["zne_"+method] += sum(s["acquisition_s"] for s in samples if s["role"]=="zne")
                    fits[method] = fit
                    estimates["zne_" + method].append(fit["extrapolated"])
                    reported["zne_" + method].append(fit["extrapolated_stderr"])
                elapsed += sum(s["acquisition_s"] for s in samples)
                runs.append(dict(repeat=repeat, factors=factors, shots_setting=shots,
                                 samples=samples, fits=fits, effective_seed=run_seed, **sampling))
                job += 1
            for method, values in estimates.items():
                rows.append(dict(method=method, factors="/".join(map(str, factors)),
                                 shots_setting=shots, repetitions=repetitions,
                                 shots_per_method=shots if mode == "budget" else shots * len(factors),
                                 circuits_per_method=1 if method == "none" else len(factors),
                                 **_summary(values, target),
                                 mean_reported_stderr=float(np.mean(reported[method])),
                                 degrees_of_freedom=None if method == "none" else len(factors) - (2 if method == "zne_linear" else 3),
                                 mean_acquisition_s=acquisition[method]/repetitions,
                                 mean_processing_s=processing[method]/repetitions,
                                 mean_duration_s=(acquisition[method]+processing[method])/repetitions,
                                 acquisition_group_s=elapsed))
    options = dict(factor_sets=sets, shot_counts=counts, total_shots=total_shots,
                   repetitions=repetitions, qubit=qubit, seed=base_seed)
    operations = [dict(name=ins.operation.name, qubits=[native.find_bit(q).index for q in ins.qubits], parameters=[float(v) for v in ins.operation.params]) for ins in native.data]
    low_samples = sum(bool(s["sampling_diagnostics"]["low_shots_factors"]) for run in runs for s in run["samples"])
    boundary_samples = sum(bool(s["sampling_diagnostics"]["boundary_factors"]) for run in runs for s in run["samples"])
    checkpoint(is_cancelled, progress, 100)
    return dict(kind="zne_stability" if mode == "stability" else "equal_budget",
                source_id=experiment.id, config=asdict(experiment.config), options=options,
                ideal_observable=target, rows=rows, runs=runs,
                provenance={**analysis_provenance(experiment), "effective_seed": base_seed,
                            "native_circuit": dict(num_qubits=native.num_qubits, global_phase=float(native.global_phase), operations=operations),
                            "seed_policy": "seed base + 17×grupo; baseline +0, fatores +1…+5, módulo 2³²",
                            "reference": "Mesmo circuito compilado U/CX sem ruído; não exp(−iHt)",
                            "actual_shots": sum(s["shots"] for run in runs for s in run["samples"])},
                note=("Repetições com sementes distintas avaliam flutuação de amostragem de ⟨Z⟩, não incerteza do modelo nem das fidelidades do ensemble. Viés é média estimada menos referência ideal; variância amostral usa n−1; MSE é média empírica dos erros quadráticos. Ajustes compartilham medições; custos não são somados entre variantes. O tempo adicional de processamento mede o ajuste polinomial, sem setup nem estatísticas agregadas; baseline não possui esse ajuste. Três fatores com ajuste quadrático têm zero grau de liberdade residual. "
                      + f"Diagnóstico: {low_samples} amostras com menos de 30 shots; {boundary_samples} sem variação observada. "
                      + "Erro padrão plug-in zero não comprova certeza. Wilson aproximado 95% é registrado por fator, sem propagação à ZNE e sem cobrir viés. "
                      + ("Cada método dispõe do mesmo total de shots por repetição, distribuído entre os fatores da ZNE; isso não iguala profundidade nem tempo." if mode == "budget" else "Os pontos com mais shots têm maior custo; compare precisão e custo conjuntamente.")))


def zne_stability(experiment, **kwargs):
    return sampling_study(experiment, mode="stability", **kwargs)


def equal_budget_study(experiment, **kwargs):
    return sampling_study(experiment, mode="budget", **kwargs)
