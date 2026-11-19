"""Project workspaces, stored additively in the existing atomic library.

A workbench experiment owns editable drafts and links to immutable executions.
Legacy project names and annotations remain the authoritative associations.
"""
from copy import deepcopy
from datetime import datetime, timezone
from uuid import uuid4
from contextlib import contextmanager
from pathlib import Path
from data.drafts import DraftStore


def now():
    return datetime.now(timezone.utc).isoformat()


class SessionProjects:
    """Explicitly volatile fallback when the execution repository is unavailable."""
    def __init__(self):
        self.raw = {"version": 1, "templates": {}, "projects": {}, "annotations": {}}

    def read(self):
        return deepcopy(self.raw)

    @contextmanager
    def transaction(self):
        raw = self.read()
        yield raw
        self.raw = raw


class ProjectStore:
    def __init__(self, library):
        self.library = library
        self.validator = DraftStore(Path("."))

    def read(self):
        raw = self.library.read()
        works = raw.get("workbench", {})
        if not isinstance(works, dict) or any(
            not isinstance(key, str) or not isinstance(value, dict)
            or value.get("kind") not in ("hamiltonian", "circuit")
            or not isinstance(value.get("draft", {}), dict)
            or not isinstance(value.get("executions", []), list)
            for key, value in works.items()
        ):
            raise ValueError("Bancada inválida; biblioteca preservada. Restaure um backup para recuperar os rascunhos.")
        for work in works.values():
            if (work.get('version', 1) != 1 or not isinstance(work.get('title'), str)
                    or not isinstance(work.get('project'), str)
                    or any(not isinstance(identifier, str) for identifier in work.get('executions', []))):
                raise ValueError('Metadados da bancada inválidos; biblioteca preservada.')
            self.validator.validate_state(work['draft'])
        return raw

    def projects(self):
        raw = self.read()
        names = set(raw["projects"])
        names.update(a.get("project", "") for a in raw["annotations"].values() if a.get("project"))
        names.update(w.get("project", "") for w in raw.get("workbench", {}).values() if w.get("project"))
        return [{**raw["projects"].get(name, {}), "name": name} for name in sorted(names, key=str.casefold)]

    def create_project(self, name, description=""):
        name = name.strip()
        if not name:
            raise ValueError("Informe um nome para o projeto.")
        with self.library.transaction() as raw:
            if name in raw["projects"]:
                raise ValueError("Já existe um projeto com esse nome. Abra-o ou escolha outro nome.")
            raw["projects"][name] = dict(description=description.strip(), created_at=now(), updated_at=now())
        return name

    def annotate_project(self, name, fields):
        if not name:
            raise ValueError("Crie um projeto para registrar anotações da investigação.")
        allowed = {k: str(v) for k, v in fields.items() if k in
                   ("description", "objective", "hypothesis", "methodology", "interpretation", "next_steps")}
        with self.library.transaction() as raw:
            raw["projects"].setdefault(name, {}).update(**allowed, updated_at=now())

    def create_work(self, title, project, kind, draft):
        if kind not in ("hamiltonian", "circuit"):
            raise ValueError("Modalidade de experimento desconhecida.")
        self.validator.validate_state(draft)
        identifier = uuid4().hex
        work = dict(version=1, id=identifier, title=title.strip() or "Novo experimento", project=project,
                    kind=kind, draft=deepcopy(draft), executions=[], created_at=now(), updated_at=now())
        with self.library.transaction() as raw:
            raw.setdefault("workbench", {})[identifier] = work
        return deepcopy(work)

    def save_draft(self, identifier, draft, title=None):
        self.validator.validate_state(draft)
        with self.library.transaction() as raw:
            work = raw.get("workbench", {}).get(identifier)
            if work is None:
                raise ValueError("Experimento não encontrado. O rascunho anterior foi preservado.")
            work.update(draft=deepcopy(draft), updated_at=now())
            if title and title.strip():
                work["title"] = title.strip()[:160]

    def link_execution(self, identifier, execution_id):
        with self.library.transaction() as raw:
            work = raw.get("workbench", {}).get(identifier)
            if work is None:
                raise ValueError("Não foi possível associar a execução ao experimento de origem.")
            if execution_id not in work["executions"]:
                work["executions"].append(execution_id)
            work.update(latest_execution=execution_id, updated_at=now())
            raw["annotations"].setdefault(execution_id, {}).update(
                project=work["project"], workbench_id=identifier)

    def work_for_execution(self, identifier):
        raw = self.read()
        key = raw["annotations"].get(identifier, {}).get("workbench_id")
        return deepcopy(raw.get("workbench", {}).get(key))

    def works(self, project=None):
        works = list(self.read().get("workbench", {}).values())
        return sorted((deepcopy(w) for w in works if project is None or w.get("project", "") == project),
                      key=lambda w: w.get("updated_at", ""), reverse=True)

    def register_artifact(self, sources, path, kind, *, checksum=None):
        """Record a produced file and its sources, without copying or rewriting it."""
        from pathlib import Path
        resolved = Path(path).resolve()
        if not resolved.is_file():
            raise ValueError('O arquivo exportado não foi encontrado; nenhum vínculo foi registrado.')
        entry = dict(id=uuid4().hex, source_ids=list(sources), path=str(resolved),
                     name=resolved.name, kind=kind, created_at=now(), bytes=resolved.stat().st_size,
                     sha256=checksum)
        with self.library.transaction() as raw:
            raw.setdefault('artifacts', {})[entry['id']] = entry
        return entry

    def artifacts(self, source_ids):
        selected = set(source_ids)
        entries = self.read().get('artifacts', {})
        if not isinstance(entries, dict) or any(not isinstance(item, dict) or not isinstance(item.get('path'), str) or not isinstance(item.get('source_ids'), list) for item in entries.values()):
            raise ValueError('Índice de arquivos exportados inválido; arquivos e execuções preservados.')
        return [deepcopy(item) for item in entries.values()
                if selected.intersection(item.get('source_ids', []))]
