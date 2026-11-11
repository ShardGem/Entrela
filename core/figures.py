"""Portable scientific figures; no widgets, fabricated states or interpolation."""

import numpy as np
from matplotlib.figure import Figure
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.patches import Rectangle, Circle
from core.metrics import bloch_vector, fidelity, purity, energy_expectation

COLORS = ("#007ea7", "#8157c4", "#cb6500", "#16834a", "#c63e62", "#3a62b0")
MAX_PLOT_SNAPSHOTS = 101


def figure(width=7, height=4):
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


def bloch_figure(experiments, indices=None, *, qubits=None):
    indices = [None] * len(experiments) if indices is None else indices
    if len(experiments) not in (1, 2) or len(indices) != len(experiments):
        raise ValueError("Selecione uma ou duas execuções e seus snapshots.")
    max_qubits = max(e.config.system.num_qubits for e in experiments)
    selected=list(range(max_qubits)) if qubits is None else list(qubits)
    if not selected or any(type(q) is not int or q<0 or q>=max_qubits for q in selected) or len(set(selected))!=len(selected):
        raise ValueError("Selecione qubits existentes para a figura de Bloch.")
    cols = min(4, len(selected))
    per_run_rows = int(np.ceil(len(selected) / cols))
    fig = figure(7, 3.0 * per_run_rows * len(experiments))
    u, v = np.meshgrid(np.linspace(0, 2*np.pi, 20), np.linspace(0, np.pi, 13))
    for run, (exp, index) in enumerate(zip(experiments, indices)):
        state, ideal, actual, time = snapshot(exp, index)
        for position,q in enumerate(selected):
            if q>=exp.config.system.num_qubits:
                continue
            ax = fig.add_subplot(per_run_rows * len(experiments), cols, run * per_run_rows * cols + position + 1, projection="3d")
            ax.plot_wireframe(np.cos(u)*np.sin(v), np.sin(u)*np.sin(v), np.cos(v), color="#b5c3cf", linewidth=.4, alpha=.6)
            vector = bloch_vector(state, q)
            ax.plot([0, vector[0]], [0, vector[1]], [0, vector[2]], color=COLORS[q], linewidth=3, label="Simulado")
            if ideal is not None:
                target = bloch_vector(ideal, q)
                ax.plot([0, target[0]], [0, target[1]], [0, target[2]], "--", color="#333333", linewidth=1.5, label="Circuito ideal")
            ax.set(xlim=(-1.1, 1.1), ylim=(-1.1, 1.1), zlim=(-1.1, 1.1), xlabel="X", ylabel="Y", zlabel="Z")
            ax.set_box_aspect((1,1,1))
            when = "estado final" if actual is None else f"snapshot {actual} · {'porta' if exp.config.circuit else 't'}={time:g}"
            ax.set_title(f"{'AB'[run]} · q{q}\n{when}", fontsize=9)
            ax.tick_params(labelsize=7)
            if position == 0:
                ax.legend(loc="upper left", fontsize=7)
    fig.suptitle("Estados locais de Bloch · comprimento não mede sozinho emaranhamento", fontsize=11)
    return fig


def draw_histograms(fig, counts_by_run, *, side_by_side=False, frequency=True,
                    colors=COLORS, labels=None, label_size=8, title=None):
    """One distribution renderer for screens and portable exports."""
    fig.clear()
    if not 1 <= len(counts_by_run) <= 2:
        raise ValueError("Selecione uma ou duas distribuições.")
    labels = labels or [f"Execução {'AB'[i]}" for i in range(len(counts_by_run))]
    keys = sorted(set().union(*(set(counts or {}) for counts in counts_by_run)))
    for i, counts in enumerate(counts_by_run):
        counts = counts or {}
        ax = fig.add_subplot(1, len(counts_by_run), i + 1) if side_by_side else (fig.axes[0] if fig.axes else fig.add_subplot(111))
        total = sum(counts.values())
        width = .8 if side_by_side or len(counts_by_run) == 1 else .36
        xs = np.arange(len(keys)) + (0 if side_by_side or len(counts_by_run) == 1 else (i - .5) * width)
        values = [counts.get(key, 0) / total if total else 0 for key in keys] if frequency else [counts.get(key, 0) for key in keys]
        bars = ax.bar(xs, values, width=width, color=colors[i], label=labels[i])
        for key, bar in zip(keys, bars):
            bar._observed = ('AB'[i], key, counts.get(key, 0), total)
        ax.set_xticks(range(len(keys)), keys, rotation=90 if len(keys) > 8 else 0, fontsize=label_size)
        ax.set_ylabel("Frequência observada (0–1)" if frequency else "Contagens")
        ax.set_xlabel("Estado (q0 à direita)")
        if frequency:
            ax.set_ylim(0, 1.05)
        else:
            ax.set_ylim(bottom=0)
        if keys:
            ax.legend(fontsize=label_size)
        elif not ax.texts:
            ax.text(.5, .5, "Sem contagens", ha="center", va="center", transform=ax.transAxes)
        ax.grid(axis='y', alpha=.2)
        if title:
            ax.set_title(title, parse_math=False)
    return fig


def histogram_figure(experiments, side_by_side=False, *, fig=None, colors=COLORS, label_size=8):
    fig = figure() if fig is None else fig
    draw_histograms(fig, [exp.result.counts for exp in experiments], side_by_side=side_by_side,
                    colors=colors, label_size=label_size)
    fig.suptitle("Contagens normalizadas pelo total observado de cada execução", fontsize=10)
    return fig


def temporal_figure(experiments, series=None, *, reference="circuit", fig=None, curves=None, colors=COLORS, label_size=8):
    from core.circuits import _build_hamiltonian
    from core.figure_labels import field_label, axis_label
    if reference not in ("circuit", "exact"):
        raise ValueError("Referência temporal desconhecida")
    if reference == "exact" and any(exp.config.circuit is not None for exp in experiments):
        raise ValueError("A referência exata exige evolução por Hamiltoniano")
    if len({exp.config.circuit is not None for exp in experiments}) > 1:
        raise ValueError("Curvas temporais exigem o mesmo tipo de eixo: tempo de evolução ou índice da porta.")
    keys = [series] if isinstance(series, str) else list(series) if series else ["fidelity", "purity", "energy"]
    keys = ["fidelity_exact" if key == "fidelity" and reference == "exact" else key for key in keys]
    fig = figure(7, 2.6 * len(keys)) if fig is None else fig
    fig.clear()
    if curves is None:
        curves = []
        for exp in experiments:
            r, c = exp.result, exp.config
            rows = []
            if r.states:
                H = None if c.circuit is not None else _build_hamiltonian(c.system.num_qubits, c.system.hamiltonian, c.system.J, c.system.h, c.system.periodic)
                targets = r.ideal_statevectors
                if reference == "exact":
                    from core.analysis import exact_states
                    targets = exact_states(c, r.times)
                for i, state in enumerate(r.states):
                    target = targets[i] if targets and len(targets) == len(r.states) else None
                    rows.append(dict(time=r.times[i], purity=purity(state), energy=None if H is None else energy_expectation(state, H),
                                     **{("fidelity_exact" if reference == "exact" else "fidelity"): fidelity(state, target) if target is not None else None}))
            curves.append(rows)
    for position, key in enumerate(keys):
        ax = fig.add_subplot(len(keys), 1, position + 1)
        for i, (exp, rows) in enumerate(zip(experiments, curves)):
            if not exp.result.states:
                continue
            indices = np.unique(np.linspace(0, len(rows) - 1, min(MAX_PLOT_SNAPSHOTS, len(rows)), dtype=int)) if rows else []
            points = [rows[k] for k in indices]
            if any(row.get(key) is not None for row in points):
                ax.plot([r['time'] for r in points], [np.nan if r.get(key) is None else r[key] for r in points], label=f"Execução {'AB'[i]}", color=colors[i], marker='.' if len(points) < 30 else None)
        ax.set_ylabel(field_label(key))
        ax.set_xlabel(axis_label('time', {'circuit': experiments[0].config.circuit}))
        ax.grid(alpha=.2)
        if ax.lines:
            ax.legend(fontsize=label_size)
        else:
            ax.text(.5, .5, "Métrica indisponível para estes registros.", ha='center', va='center', transform=ax.transAxes)
    return fig


def analysis_figure(data, key=None, fig=None, *, colors=COLORS, label_size=8):
    from core.figure_labels import field_label, axis_label, STUDY_TITLES
    rows, kind = data['rows'], data['kind']
    fig = figure() if fig is None else fig
    fig.clear()
    ax = fig.add_subplot(111)
    config = data.get('config', {})
    if kind == 'heatmap':
        key = key or ('fidelity_exact' if any(r.get('fidelity_exact') is not None for r in rows) else 'fidelity')
        xs, ys = sorted({r['x'] for r in rows}), sorted({r['y'] for r in rows})
        grid = np.full((len(ys), len(xs)), np.nan)
        for row in rows:
            if row.get(key) is not None:
                grid[ys.index(row['y']), xs.index(row['x'])] = row[key]
        artist = ax.imshow(grid, origin='lower', aspect='auto', cmap='viridis')
        ax.set_xticks(range(len(xs)), [format(x, '.5g') for x in xs])
        ax.set_yticks(range(len(ys)), [format(y, '.5g') for y in ys])
        ax.set_xlabel(axis_label('x', parameter=data['options']['x_parameter']) + ' · pontos calculados')
        ax.set_ylabel(axis_label('y', parameter=data['options']['y_parameter']))
        fig.colorbar(artist, ax=ax, label=field_label(key))
    elif kind in ('zne_stability', 'equal_budget', 'mitigation_benchmark'):
        key = key or ('absolute_error' if kind == 'mitigation_benchmark' else 'rmse')
        selected = [r for r in rows if r.get(key) is not None and (kind != 'mitigation_benchmark' or r.get('status') == 'available')]
        xs = list(range(len(selected)))
        ax.bar(xs, [r[key] for r in selected], color=[colors[i % len(colors)] for i in xs])
        labels = [r.get('label', r['method']) + ('\n' + str(r.get('factors', '')) + ' · ' + str(r.get('shots_setting', '')) if kind != 'mitigation_benchmark' else '') for r in selected]
        ax.set_xticks(xs, labels, rotation=25, ha='right', fontsize=label_size)
        if key == 'estimate' and kind == 'mitigation_benchmark':
            ax.errorbar(xs, [r[key] for r in selected], yerr=[r.get('stderr') or 0 for r in selected], fmt='none', color=colors[-1], capsize=5)
            ax.axhline(data['ideal_observable'], color=colors[2], ls='--', label='Referência ideal')
            ax.legend(fontsize=label_size)
        ax.set_xlabel('Método · somente resultados disponíveis' if kind == 'mitigation_benchmark' else 'Método · fatores · shots configurados')
        ax.set_ylabel(field_label(key))
    else:
        xkey = {'temporal': 'time', 'convergence': 'steps', 'trotter_noise': 'steps', 'sweep': 'value'}[kind]
        fields = ['ideal_infidelity', 'noisy_infidelity'] if key == 'paired_infidelity' or (not key and kind == 'trotter_noise') else [key] if key else ['infidelity'] if kind == 'convergence' else ['fidelity', 'purity']
        seeds = sorted({r.get('seed') for r in rows}, key=lambda value: -1 if value is None else value) if kind == 'sweep' else [None]
        for field_index, field in enumerate(fields):
            for seed_index, seed in enumerate(seeds):
                selected = [r for r in rows if kind != 'sweep' or r.get('seed') == seed]
                if any(row.get(field) is not None for row in selected):
                    suffix = (f' · semente {seed}' if seed is not None else ' · semente não registrada') if kind == 'sweep' else ''
                    ax.plot([r[xkey] for r in selected], [np.nan if r.get(field) is None else r[field] for r in selected], '.-', color=colors[(field_index * len(seeds) + seed_index) % len(colors)], label=field_label(field) + suffix)
        ax.set_xlabel(axis_label(xkey, config, data.get('parameter') if xkey == 'value' else None))
        ax.set_ylabel(field_label(key) if key else 'Métrica do estado' if len(fields) > 1 else field_label(fields[0]))
        ax.grid(alpha=.2)
        if ax.lines:
            ax.legend(fontsize=label_size)
    if not ax.lines and not ax.patches and not ax.images:
        ax.text(.5, .5, 'Não há valores disponíveis para esta métrica.', ha='center', transform=ax.transAxes)
    ax.set_title(data.get('protocol', {}).get('fields', {}).get('title') or STUDY_TITLES.get(kind, kind), fontsize=11, parse_math=False)
    return fig


def circuit_figure(experiment, limit=80, *, start=0, per_row=16):
    from core.circuit_inspection import inspect_circuit
    inspected = inspect_circuit(experiment)
    operations = inspected.operations
    # All operations remain in raw JSON; the presentation is explicitly bounded.
    ops = operations[start:start+limit]
    n = experiment.config.system.num_qubits
    blocks = max(1,int(np.ceil(len(ops)/per_row)))
    fig = figure(7,max(2.8,blocks*(.4*n+1.2)))
    if not ops:
        ax=fig.add_subplot(111)
        ax.axis("off")
        ax.text(.5,.5,"Não há operações registradas para este diagrama.",ha="center",va="center",transform=ax.transAxes)
        return fig
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
        ax.set_title(f"Operações {start+block*per_row+1}–{start+min(len(ops),(block+1)*per_row)}",fontsize=8)
    fig.suptitle(f"Circuito · operações {start+1}–{start+len(ops)} de {len(operations)}; parâmetros completos no JSON"
                 + ("\nReconstruído da configuração com as bibliotecas atuais" if inspected.reconstructed else ""), fontsize=10)
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
    if not rows:
        return
    columns=[key for key in preferred if key in rows[0]][:5]
    if not columns:
        columns=list(rows[0])[:5]
    import textwrap
    formatted=[]
    for row in rows:
        cells=[]
        for key in columns:
            value="—" if row.get(key) is None else format(row[key],".7g") if isinstance(row[key],float) else str(row[key])
            value=value[:77]+"…" if len(value)>80 else value
            cells.append(textwrap.fill(value,20))
        formatted.append(cells)
    start=0
    while start<len(rows):
        stop=start
        used=4
        while stop<len(rows):
            height=max(cell.count("\n")+1 for cell in formatted[stop])+1
            if used+height>42 and stop>start:
                break
            used+=height
            stop+=1
        fig=figure(210/25.4,297/25.4)
        ax=fig.add_subplot(111)
        ax.axis("off")
        table=ax.table(cellText=formatted[start:stop],colLabels=[textwrap.fill(key.replace("_"," "),20) for key in columns],loc="center",cellLoc="center")
        table.auto_set_font_size(False)
        table.set_fontsize(8)
        for (row, col), cell in table.get_celld().items():
            # 42 line units fit inside the reserved page body. Each row is tall
            # enough for its tallest wrapped cell, including long method names.
            lines=3 if row==0 else max(c.count("\n")+1 for c in formatted[start+row-1])+1
            cell.set_height(lines/48)
            cell.set_edgecolor("#d1dfe8")
            if row == 0:
                cell.set_facecolor("#e8f3f9")
                cell.set_text_props(weight="bold",color="#18364e")
        reference=data.get("protocol",{}).get("fields",{}).get("evidence_ref","")
        fig.suptitle(f"{data['kind']}\n{reference} · linhas {start+1}–{stop} do JSON",fontsize=11,parse_math=False)
        ax.text(.5,-.02,"Colunas e textos selecionados; dados e precisão integrais nos CSV/JSON.",ha="center",transform=ax.transAxes,fontsize=8)
        yield fig
        start=stop
