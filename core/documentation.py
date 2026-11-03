"""Documentable exports assembled from immutable runs and real snapshots."""

import csv
from datetime import datetime, timezone
from hashlib import sha256
from io import BytesIO, StringIO
import json
import re
from pathlib import Path
import tempfile
import textwrap
import zipfile
import numpy as np
from PIL import Image
from matplotlib.backends.backend_pdf import PdfPages
from core import __version__
from core.analysis import checkpoint
from core.export import export_experiment_json, export_experiment_csv, export_analysis, _atomic_text
from core.figures import (figure, snapshot, bloch_figure, histogram_figure, temporal_figure,
                          analysis_figure, circuit_figure)
from core.figures import analysis_table_figures
from core.figures import zne_comparison_figure
from core.metrics import bloch_vector


def latex_escape(value):
    substitutions = {"\\":r"\textbackslash{}", "&":r"\&", "%":r"\%", "$":r"\$", "#":r"\#", "_":r"\_", "{":r"\{", "}":r"\}", "~":r"\textasciitilde{}", "^":r"\textasciicircum{}"}
    return "".join(substitutions.get(char,char) for char in str(value))


def export_latex(data, filepath):
    rows = data.get("rows", [])
    if not rows:
        raise ValueError("Não há linhas para exportar.")
    priority = ("snapshot","time","steps","x","y","value","method","factors","shots_setting",
                "rmse","bias","sample_variance","ideal_infidelity","noisy_infidelity",
                "fidelity_ideal_exact","fidelity_noisy_exact","fidelity_exact","fidelity",
                "purity","energy","mean_estimate","absolute_error","estimate","stderr","infidelity","depth")
    columns = [key for key in priority if key in rows[0]][:8]
    if not columns:
        columns = list(rows[0])[:8]
    identifier=str(data.get("analysis_id") or data.get("id") or sha256(json.dumps({k:data.get(k) for k in ("source_id","kind","options")},sort_keys=True).encode()).hexdigest()[:12])
    label="tab:entrela-"+re.sub(r"[^A-Za-z0-9:-]","-",identifier)[:80]
    lines = [r"% Requer \usepackage{longtable}; preserve o JSON completo e o manifesto.",
             "% Fonte: "+latex_escape(data.get("source_id","—")),
             "% Análise: "+latex_escape(data.get("analysis_id",data.get("id","—"))),
             "% Referência no TCC: "+latex_escape(data.get("protocol",{}).get("fields",{}).get("evidence_ref","")),
             r"\begin{longtable}{"+"l"*len(columns)+"}",
             r"\caption{"+latex_escape(data.get("protocol",{}).get("fields",{}).get("title") or data["kind"])+r"}\label{"+label+r"}\\",
             " & ".join(latex_escape(key) for key in columns)+r" \\ \hline",r"\endfirsthead",
             " & ".join(latex_escape(key) for key in columns)+r" \\ \hline",r"\endhead"]
    for index,row in enumerate(rows):
        values = ["—" if row.get(key) is None else format(row[key],".8g") if isinstance(row[key],float) else str(row[key]) for key in columns]
        lines.append(" & ".join(latex_escape(value) for value in values)+r" \\"+f" % linha {index+1} do JSON")
    lines.extend([r"\end{longtable}","% "+latex_escape(data.get("note","")),"% Colunas selecionadas; todas as colunas e a precisão integral permanecem no CSV/JSON."])
    path=Path(filepath)
    _atomic_text(path,"\n".join(lines)+"\n")
    return path


def animation_indices(experiments, max_frames=40):
    if not 1 <= len(experiments) <= 2:
        raise ValueError("Selecione uma ou duas execuções para o GIF.")
    if type(max_frames) is not int or not 2 <= max_frames <= 80:
        raise ValueError("Use de 2 a 80 quadros por animação.")
    first = experiments[0]
    n = len(first.result.states)
    if n < 2:
        raise ValueError("GIF requer pelo menos dois snapshots reais; ative snapshots e execute novamente.")
    for exp in experiments[1:]:
        if len(exp.result.states) != n or not np.allclose(exp.result.times,first.result.times,rtol=0,atol=1e-12):
            raise ValueError("GIF comparativo exige snapshots nos mesmos instantes; não há interpolação.")
        if bool(exp.config.circuit) != bool(first.config.circuit):
            raise ValueError("Eixos de tempo incompatíveis para animação.")
    return np.unique(np.linspace(0,n-1,min(n,max_frames),dtype=int)).tolist()


def export_animation(experiments, filepath, max_frames=40, frame_ms=350, progress=None, is_cancelled=None, frames_directory=None):
    if type(frame_ms) is not int or not 100 <= frame_ms <= 3000:
        raise ValueError("Duração didática deve estar entre 100 e 3000 ms por quadro.")
    indices = animation_indices(experiments,max_frames)
    path = Path(filepath)
    frames=[]
    metadata = dict(schema_version=1,kind="bloch_animation",entrela_version=__version__,
                    source_ids=[e.id for e in experiments],indices=indices,frame_duration_ms=frame_ms,
                    times=[experiments[0].result.times[i] for i in indices],
                    configs=[__import__("dataclasses").asdict(e.config) for e in experiments],
                    source_versions=[e.result.metadata.get("versions",{}) for e in experiments],
                    effective_seeds=[e.result.metadata.get("effective_seed") for e in experiments],
                    note="Enquadramento de documentação padronizado; somente snapshots simulados, sem interpolação. Duração didática, não tempo físico. Reprodução única, sem ligação artificial fim→início.")
    if frames_directory is not None:
        frames_directory=Path(frames_directory)
        frames_directory.mkdir(parents=True,exist_ok=True)
        metadata["frame_files"]=[f"frame_{index:04d}.png" for index in indices]
    with tempfile.TemporaryDirectory(prefix=".entrela-gif-",dir=path.parent) as directory:
        for k,index in enumerate(indices):
            checkpoint(is_cancelled,progress,int(95*k/len(indices)))
            fig=bloch_figure(experiments,[index]*len(experiments))
            buffer=BytesIO()
            fig.savefig(buffer,format="png",dpi=80)
            fig.clear()
            if frames_directory is not None:
                (frames_directory/f"frame_{index:04d}.png").write_bytes(buffer.getvalue())
            with Image.open(BytesIO(buffer.getvalue())) as image:
                frames.append(image.convert("RGB").quantize(colors=128))
        checkpoint(is_cancelled,progress,98)
        temporary=Path(directory)/"animation.gif"
        # Omit loop: play once rather than imply a simulated closing trajectory.
        frames[0].save(temporary,format="GIF",save_all=True,append_images=frames[1:],duration=frame_ms,
                       disposal=2,comment=json.dumps(metadata,ensure_ascii=False,allow_nan=False).encode("utf-8"))
        checkpoint(is_cancelled,None,0)
        temporary.replace(path)
    if progress:
        progress(100)
    return metadata


def _text_page(title, text):
    fig=figure(8.27,11.69)
    fig.text(.07,.96,title,va="top",fontsize=16,color="#006e96",parse_math=False)
    fig.text(.07,.9,text,va="top",fontsize=8,family="monospace",linespacing=1.6,parse_math=False)
    return fig


def _save_formats(fig, folder, name):
    for extension in ("png","svg","pdf"):
        fig.savefig(folder/(name+"."+extension),dpi=140)
    fig.clear()


def _cover(experiments,annotations):
    fig=figure(8.27,11.69)
    fig.set_layout_engine(None)
    fig.text(.08,.95,"ENTRELA",fontsize=11,color="#007ea7",weight="bold")
    fig.text(.08,.90,"Relatório científico",fontsize=26,color="#18364e",weight="bold")
    fig.text(.08,.865,"Experimentos, resultados e evidências reproduzíveis",fontsize=11,color="#526a7c")
    for i,exp in enumerate(experiments):
        y=.79-i*.17
        name=(annotations or {}).get(exp.id,{}).get("title") or ("Circuito livre" if exp.config.circuit else exp.config.system.hamiltonian)
        name=name[:117]+"..." if len(name)>120 else name
        fig.text(.08,y,"AB"[i]+" · "+textwrap.fill(name,60),fontsize=14,color="#006e96",va="top",parse_math=False)
        details=(f"ID {exp.id} · {exp.created_at.isoformat()}\n"
                 f"{exp.config.system.num_qubits} qubits · {exp.config.shots} shots · seed efetiva {exp.result.metadata.get('effective_seed','—')}\n"
                 +("Ruído: "+exp.config.noise.kind if exp.config.noise.enabled else "Condição ideal, sem ruído"))
        fig.text(.08,y-.045,details,fontsize=9,color="#243d52",va="top",linespacing=1.6)
    ax=fig.add_axes((.08,.39,.84,.12))
    ax.axis("off")
    rows=[]
    for i,exp in enumerate(experiments):
        values=[exp.result.fidelity,exp.result.purity,exp.result.energy]
        rows.append(["AB"[i]]+["—" if value is None else format(value,".8g") for value in values])
    table=ax.table(cellText=rows,colLabels=["Execução","F ao circuito ideal","Pureza global","Energia média"],loc="center",cellLoc="center")
    table.auto_set_font_size(False)
    table.set_fontsize(10)
    table.scale(1,1.9)
    for (row,col),cell in table.get_celld().items():
        cell.set_edgecolor("#d1dfe8")
        if row==0:
            cell.set_facecolor("#e8f3f9")
            cell.set_text_props(weight="bold",color="#18364e")
    note=("Fidelidade usa o circuito ideal da própria execução; não equivale ao erro contra exp(−iHt). "
          "ZNE de observáveis não fornece estado mitigado. Estados locais de Bloch não demonstram sozinhos emaranhamento global. "
          "Figuras usam snapshots reais. Preserve o pacote ZIP para os dados integrais, configurações, versões e análises.")
    fig.text(.08,.32,"Referências e interpretação",fontsize=12,color="#006e96",weight="bold")
    fig.text(.08,.285,textwrap.fill(note,91),fontsize=9,color="#344e63",va="top",linespacing=1.7)
    fig.text(.08,.075,"Entrela "+__version__+" · documentação computacional",fontsize=9,color="#526a7c")
    return fig


def _bloch_csv(experiment, filepath):
    out=StringIO(newline="")
    writer=csv.writer(out)
    writer.writerow(["source_id","snapshot","time","qubit","reference","X","Y","Z","local_purity"])
    indices=list(range(len(experiment.result.states))) or [None]
    for index in indices:
        state,ideal,actual,time=snapshot(experiment,index)
        for reference,selected in (("simulated",state),("ideal",ideal)):
            if selected is None:
                continue
            for q in range(experiment.config.system.num_qubits):
                v=bloch_vector(selected,q)
                writer.writerow([experiment.id,actual,time,q,reference,*v,(1+float(v@v))/2])
    _atomic_text(filepath,out.getvalue())


def export_pdf(experiments, filepath, analyses=(), annotations=None, progress=None, is_cancelled=None):
    if not 1 <= len(experiments) <= 2:
        raise ValueError("Selecione uma ou duas execuções para o PDF.")
    ids={e.id for e in experiments}
    if any(data.get("source_id") not in ids for data in analyses):
        raise ValueError("Análise não pertence às fontes do PDF.")
    path=Path(filepath)
    with tempfile.TemporaryDirectory(prefix=".entrela-pdf-",dir=path.parent) as directory:
        temp=Path(directory)/"report.pdf"
        with PdfPages(temp) as pdf:
            def page(fig):
                checkpoint(is_cancelled,None,0)
                pdf.savefig(fig)
                fig.clear()
            page(_cover(experiments,annotations))
            page(histogram_figure(experiments,side_by_side=len(experiments)==2))
            page(temporal_figure(experiments))
            if any(e.result.mitigation for e in experiments):
                page(zne_comparison_figure(experiments))
            if all(e.result.final_state is not None or e.result.states for e in experiments):
                page(bloch_figure(experiments))
            for i,e in enumerate(experiments):
                checkpoint(is_cancelled,progress,int(50*(i+1)/len(experiments)))
                page(circuit_figure(e))
                content=json.dumps(dict(source_id=e.id,config=__import__("dataclasses").asdict(e.config),
                                        versions=e.result.metadata.get("versions"),
                                        annotation=(annotations or {}).get(e.id)),ensure_ascii=False,indent=2)
                lines=[]
                for line in content.splitlines():
                    lines.extend(textwrap.wrap(line,width=95,replace_whitespace=False) or [""])
                for start in range(0,len(lines),47):
                    page(_text_page("Configuração e proveniência · "+e.id,"\n".join(lines[start:start+47])))
            for data in analyses:
                page(analysis_figure(data))
                for fig in analysis_table_figures(data):
                    page(fig)
                fields=data.get("protocol",{}).get("fields",{})
                text=json.dumps(dict(analysis_id=data.get("analysis_id"),source_id=data.get("source_id"),protocol=fields),ensure_ascii=False,indent=2)
                wrapped=[]
                for line in (text+"\n\n"+data.get("note","")).splitlines():
                    wrapped.extend(textwrap.wrap(line,width=95) or [""])
                for start in range(0,len(wrapped),47):
                    page(_text_page("Referência e interpretação do estudo", "\n".join(wrapped[start:start+47])))
        checkpoint(is_cancelled,progress,100)
        temp.replace(path)
    return path


def export_documentation(experiments, filepath, analyses=(), annotations=None, protocols=(),
                         include_gif=True, max_frames=40, frame_ms=350, progress=None, is_cancelled=None):
    if not 1 <= len(experiments) <= 2:
        raise ValueError("Escolha uma ou duas execuções.")
    ids={e.id for e in experiments}
    if len(ids)!=len(experiments):
        raise ValueError("Escolha execuções distintas para comparar.")
    annotations={key:value for key,value in (annotations or {}).items() if key in ids}
    protocols=[p for p in protocols if p.get("source_id") in ids]
    if any(data.get("source_id") not in ids for data in analyses):
        raise ValueError("Análise não pertence às fontes exportadas.")
    path=Path(filepath)
    omissions=[]
    with tempfile.TemporaryDirectory(prefix=".entrela-doc-",dir=path.parent) as directory:
        folder=Path(directory)/"contents"
        folder.mkdir()
        for i,exp in enumerate(experiments):
            checkpoint(is_cancelled,progress,int(20*i/len(experiments)))
            target=folder/("run_"+exp.id)
            target.mkdir()
            export_experiment_json(exp,target/"experiment.json")
            export_experiment_csv(exp,target/"results.csv",(annotations or {}).get(exp.id))
            _atomic_text(target/"circuit.txt",exp.result.circuit_text)
            if exp.result.states or exp.result.final_state is not None:
                _bloch_csv(exp,target/"bloch.csv")
                _save_formats(bloch_figure([exp]),target,"bloch_final")
            _save_formats(histogram_figure([exp]),target,"distribution")
            _save_formats(temporal_figure([exp]),target,"temporal")
            _save_formats(circuit_figure(exp),target,"circuit_preview")
            if exp.result.mitigation:
                _save_formats(zne_comparison_figure([exp]),target,"zne_observable")
        checkpoint(is_cancelled,progress,30)
        if len(experiments)==2:
            _save_formats(histogram_figure(experiments,side_by_side=True),folder,"comparison_distributions")
            _save_formats(temporal_figure(experiments),folder,"comparison_temporal")
            if all(e.result.states or e.result.final_state is not None for e in experiments):
                _save_formats(bloch_figure(experiments),folder,"comparison_bloch")
        studyfolder=folder/"analyses"
        studyfolder.mkdir()
        for i,data in enumerate(analyses):
            checkpoint(is_cancelled,progress,35+int(20*i/max(1,len(analyses))))
            name=f"analysis_{i+1:03}"
            export_analysis(data,studyfolder/(name+".json"))
            export_analysis(data,studyfolder/(name+".csv"))
            export_latex(data,studyfolder/(name+".tex"))
            _save_formats(analysis_figure(data),studyfolder,name)
        _atomic_text(folder/"protocols.json",json.dumps(list(protocols),ensure_ascii=False,indent=2,allow_nan=False))
        _atomic_text(folder/"README.md", """# Pacote de reprodução Entrela

Consulte manifest.json: fontes, análises, referências no TCC e hashes SHA-256.
Cada run_<id>/experiment.json contém os estados completos; results.csv inclui
configuração e proveniência. bloch.csv contém coordenadas e pureza local reais.
As análises incluem JSON integral, CSV + manifesto, LaTeX e figuras PNG/SVG/PDF.
Use as versões registradas nos metadados; seeds não garantem identidade entre
versões/plataformas. Importar um experimento no aplicativo cria uma cópia com ID novo.

Para reproduzir uma simulação por Python, com o Entrela instalado:

```python
import json
from dataclasses import replace
from core.types import config_from_dict
from core.simulation import run_experiment
raw = json.load(open('run_<id>/experiment.json', encoding='utf-8'))
config = config_from_dict(raw['config'])
config = replace(config, seed=raw['result']['metadata']['effective_seed'])
reproduced = run_experiment(config)
```

Reprodução de ZNE e demais estudos é separada da simulação fonte. Seus fatores,
métodos, seeds e contagens estão nos JSON das análises/result.mitigation. A tela
Análises permite Reproduzir análise ao reabrir a fonte e o estudo no workspace.
GIFs usam somente os snapshots indicados no comentário JSON embutido, reprodução
única e duração didática. Diagramas são prévias; as operações completas estão no JSON.
""")
        export_pdf(experiments,folder/"report.pdf",analyses,annotations,is_cancelled=is_cancelled)
        checkpoint(is_cancelled,progress,65)
        animation=None
        if include_gif:
            try:
                animation_indices(experiments,max_frames)
            except ValueError as exc:
                omissions.append("GIF: "+str(exc))
            else:
                animation=export_animation(experiments,folder/"bloch.gif",max_frames,frame_ms,
                    progress=lambda p: progress(65+int(.3*p)) if progress else None,is_cancelled=is_cancelled,
                    frames_directory=folder/"frames")
        manifest=dict(schema_version=1,kind="documentation",entrela_version=__version__,
                      created_at=datetime.now(timezone.utc).isoformat(),source_ids=[e.id for e in experiments],
                      annotations=annotations or {},animation=animation,omissions=omissions,
                      lineage=[dict(source_id=d.get("source_id"),analysis_id=d.get("analysis_id",d.get("id")),
                                    protocol_id=d.get("protocol",{}).get("protocol_id"),
                                    evidence_ref=d.get("protocol",{}).get("fields",{}).get("evidence_ref"),
                                    artifact_prefix=f"analyses/analysis_{i+1:03}") for i,d in enumerate(analyses)],
                      note="JSON contém os estados e operações integrais. Diagramas mostram até 80 operações; GIF seleciona até o limite de snapshots reais. PDFs e imagens não substituem os dados brutos.")
        manifest["files"]=[dict(path=file.relative_to(folder).as_posix(),sha256=sha256(file.read_bytes()).hexdigest(),bytes=file.stat().st_size) for file in sorted(folder.rglob("*")) if file.is_file()]
        _atomic_text(folder/"manifest.json",json.dumps(manifest,ensure_ascii=False,indent=2,allow_nan=False))
        temporary=Path(directory)/"documentation.zip"
        with zipfile.ZipFile(temporary,"w",zipfile.ZIP_DEFLATED) as archive:
            for file in sorted(folder.rglob("*")):
                if file.is_file():
                    archive.write(file,file.relative_to(folder).as_posix())
        checkpoint(is_cancelled,progress,100)
        temporary.replace(path)
    return path
