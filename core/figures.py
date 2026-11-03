"""Portable scientific figures; no widgets, fabricated states or interpolation."""

import numpy as np
from matplotlib.figure import Figure
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.patches import Rectangle, Circle
from core.metrics import bloch_vector, fidelity, purity, energy_expectation

COLORS = ("#007ea7", "#8157c4", "#cb6500", "#16834a", "#c63e62", "#3a62b0")


def figure(width=9, height=4):
    fig = Figure(figsize=(width, height), layout="constrained", facecolor="white")
    FigureCanvasAgg(fig)
    return fig


def snapshot(experiment, index=None):
    states = experiment.result.states
    if not states:
        if index is not None:
            raise ValueError("Esta execução não possui snapshots.")
        if experiment.result.final_state is None:
            raise ValueError("Estado final indisponível neste registro.")
        return experiment.result.final_state, experiment.result.ideal_final_state, None, None
    index = len(states) - 1 if index is None else index
    if type(index) is not int or not 0 <= index < len(states):
        raise ValueError("Snapshot fora da execução.")
    ideal = experiment.result.ideal_statevectors
    return states[index], ideal[index] if ideal and len(ideal) == len(states) else None, index, experiment.result.times[index]


def bloch_figure(experiments, indices=None):
    indices = [None] * len(experiments) if indices is None else indices
    if len(experiments) not in (1, 2) or len(indices) != len(experiments):
        raise ValueError("Selecione uma ou duas execuções e seus snapshots.")
    max_qubits = max(e.config.system.num_qubits for e in experiments)
    cols = min(3, max_qubits)
    per_run_rows = int(np.ceil(max_qubits / cols))
    fig = figure(10 if len(experiments) == 1 else 12, 3.0 * per_run_rows * len(experiments))
    u, v = np.meshgrid(np.linspace(0, 2*np.pi, 20), np.linspace(0, np.pi, 13))
    for run, (exp, index) in enumerate(zip(experiments, indices)):
        state, ideal, actual, time = snapshot(exp, index)
        for q in range(exp.config.system.num_qubits):
            ax = fig.add_subplot(per_run_rows * len(experiments), cols, run * per_run_rows * cols + q + 1, projection="3d")
            ax.plot_wireframe(np.cos(u)*np.sin(v), np.sin(u)*np.sin(v), np.cos(v), color="#b5c3cf", linewidth=.4, alpha=.6)
            vector = bloch_vector(state, q)
            ax.plot([0, vector[0]], [0, vector[1]], [0, vector[2]], color=COLORS[q], linewidth=3, label="Simulado")
            if ideal is not None:
                target = bloch_vector(ideal, q)
                ax.plot([0, target[0]], [0, target[1]], [0, target[2]], "--", color="#333333", linewidth=1.5, label="Circuito ideal")
            ax.set(xlim=(-1.1, 1.1), ylim=(-1.1, 1.1), zlim=(-1.1, 1.1), xlabel="X", ylabel="Y", zlabel="Z")
            ax.set_box_aspect((1,1,1))
            when = "estado final" if actual is None else f"snapshot {actual} · {'porta' if exp.config.circuit else 't'}={time:g}"
            ax.set_title(f"{'AB'[run]} · q{q} · {exp.id}\n{when}", fontsize=9)
            ax.tick_params(labelsize=7)
            if q == 0:
                ax.legend(loc="upper left", fontsize=7)
    fig.suptitle("Estados locais de Bloch · comprimento não mede sozinho emaranhamento", fontsize=11)
    return fig


def histogram_figure(experiments, side_by_side=False):
    fig = figure()
    keys = sorted(set().union(*(set(e.result.counts or {}) for e in experiments)))
    if not keys:
        return fig
    for i, exp in enumerate(experiments):
        ax = fig.add_subplot(1, len(experiments), i+1) if side_by_side else (fig.axes[0] if fig.axes else fig.add_subplot(111))
        total = sum((exp.result.counts or {}).values())
        width = .8 if side_by_side or len(experiments) == 1 else .36
        xs = np.arange(len(keys)) + (0 if side_by_side or len(experiments) == 1 else (i-.5)*width)
        ax.bar(xs, [exp.result.counts.get(k,0)/total if total else 0 for k in keys], width=width, color=COLORS[i], label=f"{'AB'[i]} · {exp.id}")
        ax.set_xticks(range(len(keys)), keys, rotation=90 if len(keys)>8 else 0, fontsize=8)
        ax.set_ylabel("Frequência observada")
        ax.set_xlabel("Bitstring · q0 à direita")
        ax.legend(fontsize=8)
        ax.grid(axis="y", alpha=.2)
    return fig


def temporal_figure(experiments, series=None):
    from core.circuits import _build_hamiltonian
    keys = [series] if series else ["fidelity", "purity", "energy"]
    fig = figure(9, 2.6 * len(keys))
    labels = {"fidelity": "Fidelidade ao circuito ideal", "purity": "Pureza global", "energy": "Energia ⟨H⟩"}
    for j, key in enumerate(keys):
        ax = fig.add_subplot(len(keys), 1, j+1)
        for i, exp in enumerate(experiments):
            r, c = exp.result, exp.config
            if not r.states or not r.times:
                continue
            H = None if c.circuit else _build_hamiltonian(c.system.num_qubits,c.system.hamiltonian,c.system.J,c.system.h,c.system.periodic)
            if key == "energy" and H is None:
                continue
            indices = np.unique(np.linspace(0,len(r.states)-1,min(201,len(r.states)),dtype=int))
            values = []
            for k in indices:
                if key == "fidelity":
                    ideal = r.ideal_statevectors[k] if r.ideal_statevectors else (r.states[k] if not c.noise.enabled else None)
                    value = None if ideal is None else fidelity(r.states[k], ideal)
                elif key == "purity":
                    value = purity(r.states[k])
                else:
                    value = energy_expectation(r.states[k], H)
                values.append(float("nan") if value is None else value)
            ax.plot([r.times[k] for k in indices],values, label=f"{'AB'[i]} · {exp.id}",color=COLORS[i],marker="." if len(indices)<30 else None)
        ax.set_ylabel(labels[key])
        ax.set_xlabel("Índice da porta" if experiments[0].config.circuit else "Tempo adimensional (ℏ=1)")
        ax.grid(alpha=.2)
        if ax.lines:
            ax.legend(fontsize=8)
        else:
            ax.text(.5,.5,"Snapshots / referência indisponíveis",ha="center",transform=ax.transAxes)
    return fig


def analysis_figure(data, key=None, fig=None):
    rows, kind = data["rows"], data["kind"]
    if fig is None:
        fig = figure()
    else:
        fig.clear()
    ax = fig.add_subplot(111)
    if kind == "heatmap":
        key = key or ("fidelity_exact" if any(r.get("fidelity_exact") is not None for r in rows) else "fidelity")
        xs, ys = sorted({r["x"] for r in rows}), sorted({r["y"] for r in rows})
        grid = np.full((len(ys),len(xs)),np.nan)
        for r in rows:
            if r.get(key) is not None:
                grid[ys.index(r["y"]),xs.index(r["x"])] = r[key]
        # Cell labels are actual coordinates; spacing is categorical, explicit.
        artist = ax.imshow(grid,origin="lower",aspect="auto",cmap="viridis")
        ax.set_xticks(range(len(xs)),[format(x,".5g") for x in xs])
        ax.set_yticks(range(len(ys)),[format(y,".5g") for y in ys])
        ax.set_xlabel(data["options"]["x_parameter"] + " · pontos calculados")
        ax.set_ylabel(data["options"]["y_parameter"])
        fig.colorbar(artist,ax=ax,label=key)
    elif kind in ("zne_stability","equal_budget","mitigation_benchmark"):
        key = key or ("absolute_error" if kind == "mitigation_benchmark" else "rmse")
        selected = [r for r in rows if r.get(key) is not None]
        ax.bar(range(len(selected)),[r[key] for r in selected],color=[COLORS[i%6] for i in range(len(selected))])
        labels = [r.get("label",r["method"])+("\n"+str(r.get("factors",""))+" · "+str(r.get("shots_setting","")) if kind != "mitigation_benchmark" else "") for r in selected]
        ax.set_xticks(range(len(selected)),labels,rotation=25,ha="right",fontsize=8)
        ax.set_ylabel(key)
    else:
        xkey = {"temporal":"time","convergence":"steps","trotter_noise":"steps","sweep":"value"}[kind]
        keys = [key] if key else (["ideal_infidelity","noisy_infidelity"] if kind == "trotter_noise" else ["infidelity"] if kind == "convergence" else ["fidelity","purity"])
        for field in keys:
            seeds = sorted({r.get("seed") for r in rows}) if kind == "sweep" else [None]
            for seed in seeds:
                selected = [r for r in rows if r.get(field) is not None and (kind != "sweep" or r.get("seed") == seed)]
                if selected:
                    ax.plot([r[xkey] for r in selected],[r[field] for r in selected],".-",label=field+(f" · seed {seed}" if seed is not None else ""))
        if ax.lines:
            ax.legend(fontsize=8)
        ax.set_xlabel("Índice da porta" if xkey == "time" and data.get("config",{}).get("circuit") else xkey)
        ax.grid(alpha=.2)
    ax.set_title(data["kind"]+" · fonte "+data.get("source_id","—"),fontsize=11)
    return fig


def circuit_figure(experiment, limit=80):
    operations = experiment.result.metadata.get("operations", [])
    # All operations remain in raw JSON; the presentation is explicitly bounded.
    ops = operations[:limit]
    per_row = 16
    n = experiment.config.system.num_qubits
    blocks = max(1,int(np.ceil(len(ops)/per_row)))
    fig = figure(12,max(2.5,blocks*(.4*n+1.2)))
    for block in range(blocks):
        ax = fig.add_subplot(blocks,1,block+1)
        for q in range(n):
            ax.hlines(q,-.8,per_row-.1,color="#9aaaba",linewidth=.6)
        for i,op in enumerate(ops[block*per_row:(block+1)*per_row]):
            qs=op["qubits"]
            name=op["name"]
            ax.vlines(i,min(qs),max(qs),color="#007ea7")
            targets=qs
            if name in ("cx","cy","cz","ch","ccx"):
                for q in qs[:-1]:
                    ax.plot(i,q,"o",color="#007ea7",markersize=5)
                targets=qs[-1:]
                if name in ("cx","ccx"):
                    q=targets[0]
                    ax.add_patch(Circle((i,q),.19,fill=False,edgecolor="#007ea7"))
                    ax.plot([i-.12,i+.12],[q,q],color="#007ea7")
                    ax.plot([i,i],[q-.15,q+.15],color="#007ea7")
                    targets=[]
            if name=="swap":
                for q in qs:
                    ax.plot(i,q,"x",color="#007ea7",markersize=7)
                targets=[]
            for q in targets:
                ax.add_patch(Rectangle((i-.35,q-.22),.7,.44,facecolor="#e7f3fa",edgecolor="#007ea7"))
                ax.text(i,q,name[-1].upper() if name in ("cy","cz","ch") else name.upper(),ha="center",va="center",fontsize=6)
                if op.get("parameters"):
                    ax.text(i,q+.33,",".join(format(v,".3g") for v in op["parameters"][:2]),ha="center",fontsize=4.5)
        ax.set(xlim=(-.8,per_row-.1),ylim=(n-.5,-.6),yticks=range(n),yticklabels=[f"q{q}" for q in range(n)],xticks=[])
        ax.set_title(f"Operações {block*per_row+1}–{min(len(ops),(block+1)*per_row)}",fontsize=8)
    fig.suptitle(f"{experiment.id} · primeiras {len(ops)} de {len(operations)} operações; parâmetros completos no JSON",fontsize=10)
    return fig


def zne_comparison_figure(experiments,fig=None):
    fig=figure(9,4) if fig is None else fig
    fig.clear()
    ax=fig.add_subplot(111)
    labels=[]
    position=0
    for i,exp in enumerate(experiments):
        m=exp.result.mitigation
        if not m:
            continue
        baseline=m["scale_factors"].index(1)
        ax.errorbar([position,position+1],[m["measured"][baseline],m["extrapolated"]],
                    yerr=[m["stderr"][baseline],m["extrapolated_stderr"]],fmt="o",capsize=5,color=COLORS[i])
        labels.extend([f"{'AB'[i]} · fator 1\nZ(q{m['qubit']})",f"{'AB'[i]} · ZNE {m['method']}\nZ(q{m['qubit']})"])
        if m.get("ideal_observable") is not None:
            ax.plot([position-.3,position+1.3],[m["ideal_observable"]]*2,"--",color=COLORS[i],label=f"Ideal {'AB'[i]} · q{m['qubit']}")
        position+=2
    ax.set_xticks(range(position),labels,fontsize=8)
    ax.set_ylabel("Estimativa de ⟨Z⟩ ± erro padrão de amostragem")
    ax.set_title("Observáveis ZNE · baseline compilado do próprio ajuste; não é estado mitigado",fontsize=10)
    if ax.lines:
        ax.legend(fontsize=8)
    return fig


def analysis_table_figures(data):
    preferred=("snapshot","time","steps","x","y","method","factors","shots_setting","rmse","bias","sample_variance",
               "ideal_infidelity","noisy_infidelity","fidelity_ideal_exact","fidelity_noisy_exact",
               "fidelity_exact","fidelity","purity","energy","absolute_error","estimate","stderr","infidelity","depth")
    rows=data["rows"]
    columns=[key for key in preferred if key in rows[0]][:7]
    if not columns:
        columns=list(rows[0])[:7]
    for start in range(0,len(rows),22):
        fig=figure(11.69,8.27)
        ax=fig.add_subplot(111)
        ax.axis("off")
        cells=[]
        for row in rows[start:start+22]:
            cells.append(["—" if row.get(key) is None else format(row[key],".7g") if isinstance(row[key],float) else str(row[key]) for key in columns])
        table=ax.table(cellText=cells,colLabels=columns,loc="center",cellLoc="center")
        table.auto_set_font_size(False)
        table.set_fontsize(8)
        table.scale(1,1.6)
        reference=data.get("protocol",{}).get("fields",{}).get("evidence_ref","")
        fig.suptitle(f"{data['kind']} · fonte {data.get('source_id','—')}\n{reference} · linhas {start+1}–{min(start+22,len(rows))} do JSON",fontsize=12,parse_math=False)
        fig.text(.05,.035,"Colunas selecionadas. Todos os valores e metadados integrais permanecem nos CSV/JSON. Análise: "+str(data.get("analysis_id",data.get("id","—"))),fontsize=8)
        yield fig
