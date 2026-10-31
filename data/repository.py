"""Versioned, validated JSON with atomic writes and legacy read support."""
from dataclasses import asdict,fields
from datetime import datetime
from pathlib import Path
import json,os,re,tempfile
import numpy as np
from qiskit.quantum_info import Statevector,DensityMatrix
from core.types import Experiment,ExperimentResult,config_from_dict,finite,integer

STATE_LISTS = ("statevectors","density_matrices","ideal_statevectors")
SINGLE_STATES = ("final_state","ideal_final_state")

def encode_state(state):
    if state is None:
        return None
    if not isinstance(state,(Statevector,DensityMatrix)) or not state.is_valid():
        raise ValueError("Estado quântico inválido")
    return {"kind":"density_matrix" if isinstance(state,DensityMatrix) else "statevector",
            "real":state.data.real.tolist(),"imag":state.data.imag.tolist()}

def decode_state(raw):
    if raw is None:
        return None
    if raw["kind"] not in ("statevector","density_matrix"):
        raise ValueError("Representação de estado desconhecida")
    real,imag=np.asarray(raw["real"],dtype=float),np.asarray(raw["imag"],dtype=float)
    if real.shape!=imag.shape:
        raise ValueError("Dimensões real e imaginária incompatíveis")
    cls=DensityMatrix if raw["kind"]=="density_matrix" else Statevector
    state=cls(real+1j*imag)
    if not state.is_valid():
        raise ValueError("Estado inválido no arquivo")
    return state

def validate_result(config,result):
    expected=2**config.system.num_qubits
    for key in STATE_LISTS:
        for state in getattr(result,key) or []:
            if state.dim!=expected or not state.is_valid():
                raise ValueError("Snapshot incompatível com o sistema")
    for key in SINGLE_STATES:
        state=getattr(result,key)
        if state is not None and (state.dim!=expected or not state.is_valid()):
            raise ValueError("Estado final incompatível com o sistema")
    if result.statevectors and result.density_matrices:
        raise ValueError("Snapshots devem ter representação única")
    if result.times is not None and result.states:
        if len(result.times)!=len(result.states):
            raise ValueError("Tempos e estados têm comprimentos diferentes")
        for value in result.times:
            finite(value,"Tempo")
        if any(a>b for a,b in zip(result.times,result.times[1:])):
            raise ValueError("Tempos não ordenados")
    if result.counts is not None:
        for bits,count in result.counts.items():
            if not isinstance(bits,str) or len(bits)!=config.system.num_qubits or set(bits)-{"0","1"}:
                raise ValueError("Bitstring inválida")
            integer(count,"Contagem",0)
        if sum(result.counts.values())!=config.shots:
            raise ValueError("Contagens diferem dos shots")
    for key in ("fidelity","purity","energy"):
        value=getattr(result,key)
        if value is not None:
            finite(value,key)
            if key!="energy" and not -1e-8<=value<=1+1e-8:
                raise ValueError("Métrica fora do intervalo físico")
    if result.mitigation is not None:
        m=result.mitigation
        if m.get("success") is not True or m.get("method") not in ("linear","quadratic"):
            raise ValueError("Análise ZNE inválida")
        integer(m["qubit"],"Qubit",0)
        if m["qubit"]>=config.system.num_qubits:
            raise ValueError("Qubit fora do sistema")
        fs,ys,es=m["scale_factors"],m["measured"],m["stderr"]
        if len(fs)!=len(ys) or len(fs)!=len(es) or len(set(fs))!=len(fs) or 1 not in fs:
            raise ValueError("Pontos ZNE incompatíveis")
        if len(fs)<(2 if m["method"]=="linear" else 3):
            raise ValueError("Poucos pontos ZNE")
        for f in fs:
            integer(f,"Fator")
            if f%2!=1:raise ValueError("Fatores devem ser ímpares")
        for y in ys:
            finite(y,"Observável")
            if not -1<=y<=1:raise ValueError("Z medido fora de [-1,1]")
        for e in [*es,m["extrapolated_stderr"]]:
            finite(e,"Erro padrão")
            if e<0:raise ValueError("Erro padrão negativo")
        finite(m["extrapolated"],"Extrapolação")
        integer(m["shots"],"Shots")
        if not isinstance(m["source_experiment_id"],str):
            raise ValueError("Fonte ZNE inválida")

class ExperimentRepository:
    def __init__(self,base_dir=None):
        self.base_dir=Path(base_dir if base_dir is not None else
                           os.environ.get("ENTRELA_DATA_DIR",Path.home()/".entrela"/"experiments"))
        self.base_dir.mkdir(parents=True,exist_ok=True)
        self.load_errors=[]

    def _path(self,identifier):
        if not isinstance(identifier,str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,128}",identifier):
            raise ValueError("Identificador inválido")
        return self.base_dir/f"{identifier}.json"

    def save(self,experiment):
        path=self._path(experiment.id)
        payload=self._serialize(experiment)
        temporary=None
        try:
            with tempfile.NamedTemporaryFile(mode="w",encoding="utf-8",dir=self.base_dir,
                                             suffix=".tmp",delete=False) as stream:
                temporary=Path(stream.name)
                json.dump(payload,stream,ensure_ascii=False,indent=2,allow_nan=False)
                stream.flush()
                os.fsync(stream.fileno())
            temporary.replace(path)
        finally:
            if temporary and temporary.exists():temporary.unlink()
        return path

    def load(self,identifier):
        raw=json.loads(self._path(identifier).read_text(encoding="utf-8"))
        if raw["id"]!=identifier:
            raise ValueError("Identificador do arquivo incompatível")
        return self._deserialize(raw)

    def list_all(self,limit=None):
        self.load_errors=[]
        records=[]
        for path in sorted(self.base_dir.glob("*.json"),key=lambda p:p.stat().st_mtime,reverse=True):
            try:records.append(self.load(path.stem))
            except (OSError,ValueError,TypeError,KeyError,AttributeError) as exc:
                self.load_errors.append(f"{path.name}: {exc}")
            if limit is not None and len(records)>=limit:break
        return records

    def delete(self,identifier):
        path=self._path(identifier)
        if not path.exists():return False
        path.unlink()
        return True

    @staticmethod
    def _serialize(exp):
        exp.config.validate()
        validate_result(exp.config,exp.result)
        result={f.name:getattr(exp.result,f.name) for f in fields(ExperimentResult)}
        for key in STATE_LISTS:
            result[key]=[encode_state(s) for s in result[key]] if result[key] is not None else None
        for key in SINGLE_STATES:result[key]=encode_state(result[key])
        return dict(schema_version=2,config=asdict(exp.config),result=result,id=exp.id,
                    created_at=exp.created_at.isoformat(),duration_s=exp.duration_s,tags=exp.tags)

    @staticmethod
    def _deserialize(raw):
        schema=raw.get("schema_version",1)
        if type(schema) is not int or schema not in (1,2):raise ValueError("Versão de arquivo desconhecida")
        config=config_from_dict(raw["config"])
        result=dict(raw.get("result",{}))
        if schema==2:
            for key in STATE_LISTS:
                result[key]=[decode_state(s) for s in result[key]] if result.get(key) is not None else None
            for key in SINGLE_STATES:result[key]=decode_state(result.get(key))
        elif result.get("statevectors"):
            raise ValueError("Estados legados não reconhecidos")
        result=ExperimentResult(**result)
        validate_result(config,result)
        return Experiment(config,result,id=raw["id"],created_at=datetime.fromisoformat(raw["created_at"]),
                          duration_s=raw.get("duration_s",0.),tags=raw.get("tags",[]))
