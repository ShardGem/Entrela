"""Portable scientific data exports; JSON never executes user code."""
import csv,json,zipfile
from pathlib import Path
from data.repository import ExperimentRepository

def export_counts_csv(counts,filepath):
    path=Path(filepath)
    with path.open("w",newline="",encoding="utf-8") as stream:
        writer=csv.writer(stream)
        writer.writerow(["Bitstring","Counts"])
        writer.writerows(sorted(counts.items()))
    return path

def export_figure(fig,filepath,dpi=150):
    path=Path(filepath)
    fig.savefig(path,dpi=dpi,bbox_inches="tight",facecolor=fig.get_facecolor())
    return path

def export_experiment_json(experiment,filepath):
    path=Path(filepath)
    path.write_text(json.dumps(ExperimentRepository._serialize(experiment),ensure_ascii=False,
                               indent=2,allow_nan=False),encoding="utf-8")
    return path

def import_experiment_json(filepath):
    try:
        raw=json.loads(Path(filepath).read_text(encoding="utf-8"))
        return ExperimentRepository._deserialize(raw)
    except (KeyError,TypeError,AttributeError,OverflowError) as exc:
        raise ValueError("Arquivo de experimento inválido ou incompleto") from exc

def export_run_bundle(experiment,filepath):
    import io
    path=Path(filepath)
    payload=json.dumps(ExperimentRepository._serialize(experiment),ensure_ascii=False,indent=2,allow_nan=False)
    table=io.StringIO(newline="")
    writer=csv.writer(table)
    writer.writerow(["Bitstring","Counts"])
    writer.writerows(sorted((experiment.result.counts or {}).items()))
    with zipfile.ZipFile(path,"w",zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("experimento.json",payload)
        archive.writestr("contagens.csv",table.getvalue())
        archive.writestr("circuito.txt",experiment.result.circuit_text)
    return path

def result_interpretation(experiment):
    result,config=experiment.result,experiment.config
    if result.error:return "A execução falhou. Nenhuma conclusão científica foi gerada: "+result.error
    lines=[]
    if result.fidelity is not None:
        lines.append(f"Fidelidade {result.fidelity:.4f} em relação ao mesmo circuito Suzuki–Trotter sem ruído. "
                     "Essa comparação não mede o erro de aproximação de Trotter.")
    if result.purity is not None:
        lines.append(f"Pureza global: {result.purity:.4f}. A pureza de cada qubit pode ser diferente da global.")
    counts=result.counts or {}
    total=sum(counts.values())
    if config.system.initial_state=="bell" and config.system.num_qubits==2 and config.system.J==0 and config.system.h==0 and total:
        correlation=(counts.get("00",0)+counts.get("11",0))/total
        lines.append(f"{correlation:.1%} das {total} medições ficaram em 00 ou 11. "
                     "A distribuição em uma única base, isoladamente, não comprova emaranhamento.")
        if counts.get("01",0)+counts.get("10",0):
            lines.append("Há medições 01/10: a correlação perfeita do Bell ideal foi reduzida.")
    if total:
        lines.append(f"Amostragem: {total} shots. Erro padrão máximo de uma frequência binomial: {0.5/total**.5:.2%}.")
    if result.mitigation:
        lines.append("A análise ZNE estima um observável. Os valores de fidelidade e pureza acima pertencem à simulação original.")
    return "\n\n".join(lines) or "Não há dados suficientes para interpretar este registro."
