"""Recoverable local work, kept separate from immutable scientific records."""
from datetime import datetime, timezone
import json
import math
from pathlib import Path

from core.circuit_document import CircuitDocument
from core.export import _atomic_text


class DraftStore:
    MAX_BYTES = 4_000_000

    def __init__(self, directory):
        self.path = Path(directory) / "drafts.json"
        self.previous = self.path.with_name("drafts.previous.json")
        self.warning = ""

    def _read(self, path):
        if path.stat().st_size > self.MAX_BYTES:
            raise ValueError("Rascunhos excedem o limite de 4 MB")
        raw = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(raw, dict) or type(raw.get("schema_version")) is not int or raw["schema_version"] != 1:
            raise ValueError("Formato de rascunho desconhecido")
        state = raw.get("state")
        if not isinstance(state, dict):
            raise ValueError("Conteúdo de rascunho inválido")
        json.dumps(state,allow_nan=False)
        self._text_fields(state,("template_name",))
        history = state.get("editor_history",[])
        if not isinstance(history,list) or len(history)>10:
            raise ValueError("Histórico de recuperação inválido")
        for item in history:
            if not isinstance(item,dict) or not isinstance(item.get("editor"),dict):
                raise ValueError("Estado anterior do editor inválido")
            self._validate_editor(item["editor"])
            self._text_fields(item,("saved_at",))
        if state.get("editor") is not None:
            self._validate_editor(state["editor"])
        simulation = state.get("simulation",{})
        if not isinstance(simulation,dict) or not isinstance(simulation.get("controls",{}),dict):
            raise ValueError("Formulário de rascunho inválido")
        self._text_fields(simulation,("name","description","mode","initial","section","committed_name","committed_description"))
        if "expanded_sections" in simulation and (not isinstance(simulation["expanded_sections"], list) or
                any(not isinstance(key, str) for key in simulation["expanded_sections"])):
            raise ValueError("Seções do formulário inválidas")
        for key in ("description_expanded", "review_expanded"):
            if key in simulation and type(simulation[key]) is not bool:
                raise ValueError("Preferência de seção inválida")
        controls = simulation.get("controls",{})
        self._text_fields(controls,("seed","hamiltoniano","modelo_ruido"))
        for key in ("qubits","J","h","tempo","passos","p1","p2","t1","t2","shots","gate1","gate2"):
            if key in controls and (type(controls[key]) not in (int,float) or not math.isfinite(controls[key])):
                raise ValueError("Campo numérico do rascunho inválido")
        for key in ("ruido_ativo","periodic","salvar_snaps"):
            if key in controls and type(controls[key]) is not bool:
                raise ValueError("Opção do rascunho inválida")
        for key in ("annotations", "protocols"):
            if not isinstance(state.get(key, {}), dict):
                raise ValueError("Anotações de rascunho inválidas")
            for value in state.get(key,{}).values():
                if not isinstance(value,dict):
                    raise ValueError("Anotação de rascunho inválida")
                if key == "annotations":
                    self._text_fields(value,("title","description","notes","project","objective","hypothesis","methodology"))
                    for name in ("tags","categories"):
                        if not isinstance(value.get(name,[]),list) or any(not isinstance(item,str) for item in value.get(name,[])):
                            raise ValueError("Categorias do rascunho inválidas")
                else:
                    fields = value.get("fields",{})
                    if not isinstance(fields,dict) or any(not isinstance(item,str) for item in fields.values()):
                        raise ValueError("Campos de protocolo inválidos")
                    loaded = value.get("loaded")
                    if loaded is not None and (not isinstance(loaded,dict) or not isinstance(loaded.get("fields"),dict)):
                        raise ValueError("Contexto de protocolo inválido")
        return state

    def _validate_editor(self,editor):
        if not isinstance(editor,dict):
            raise ValueError("Rascunho do editor inválido")
        document = CircuitDocument.from_dict(editor["document"])
        self._text_fields(editor,("name","description","phase","seed","gate_type"))
        if type(editor.get("selected",-1)) is not int or not -1 <= editor.get("selected",-1) < max(1,len(document.gates)):
            raise ValueError("Seleção do editor inválida")
        for key,kind in (("parameters",str),("connections",int)):
            values = editor.get(key,[])
            if not isinstance(values,list) or len(values)>3 or any(type(value) is not kind for value in values):
                raise ValueError("Campos do editor inválidos")
        for key in ("shots","p1","p2","t1","t2","gate1","gate2"):
            if key in editor and (type(editor[key]) not in (int,float) or not math.isfinite(editor[key])):
                raise ValueError("Parâmetros do editor inválidos")

    @staticmethod
    def _text_fields(value, names):
        if any(name in value and (not isinstance(value[name],str) or len(value[name])>32767) for name in names):
            raise ValueError("Texto de rascunho inválido")

    def load(self):
        self.warning = ""
        if not self.path.exists():
            if self.previous.exists():
                try:
                    recovered = self._read(self.previous)
                except (OSError, ValueError, TypeError, KeyError):
                    self.warning = "Rascunho principal ausente e cópia anterior ilegível; arquivos preservados."
                else:
                    self.warning = "Rascunho principal ausente; recuperada a última cópia válida."
                    return recovered
            return {}
        try:
            return self._read(self.path)
        except (OSError, ValueError, TypeError, KeyError) as exc:
            self.warning = "O rascunho principal está ilegível e foi preservado: " + str(exc)
            try:
                state = self._read(self.previous)
            except (OSError, ValueError, TypeError, KeyError):
                self.warning += ". A cópia anterior também não está disponível."
                return {}
            self.warning += ". Recuperada a última cópia válida."
            return state

    def save(self, state):
        payload = json.dumps(dict(schema_version=1, saved_at=datetime.now(timezone.utc).isoformat(),
                                  state=state), ensure_ascii=False, allow_nan=False)
        if len(payload.encode("utf-8")) > self.MAX_BYTES:
            raise ValueError("Rascunhos excedem o limite de 4 MB")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if self.path.exists():
            try:
                self._read(self.path)
            except (OSError, ValueError, TypeError, KeyError):
                # Preserve damaged evidence before a new valid draft replaces it.
                stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S-%f")
                self.path.replace(self.path.with_name("drafts-damaged-" + stamp + ".json"))
            else:
                _atomic_text(self.previous, self.path.read_text(encoding="utf-8"))
        _atomic_text(self.path, payload)
