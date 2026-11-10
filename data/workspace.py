"""Named personal templates and project annotations, separate from scientific records."""

from pathlib import Path
import json, os, tempfile
from contextlib import contextmanager
from dataclasses import asdict
import threading
from core.types import ExperimentConfig, config_from_dict
from data.file_lock import directory_lock


_transactions = threading.local()


class WorkspaceLibrary:
    def __init__(self, directory, *, lock_timeout=5.0):
        self.path = Path(directory) / "workspace.json"
        self.lock_timeout = lock_timeout

    @contextmanager
    def transaction(self):
        """Read, modify and atomically save under one local-process lock.

        Nested transactions in the same thread share the current document,
        including when two library objects refer to the same directory.
        Exceptions leave the existing file intact.
        """
        key = str(self.path.resolve())
        with directory_lock(self.path.parent, timeout=self.lock_timeout):
            active = getattr(_transactions, "active", None)
            if active is None:
                active = _transactions.active = {}
            if key in active:
                yield active[key]
                return
            raw = self.read()
            active[key] = raw
            try:
                yield raw
                self._write(raw)
            finally:
                active.pop(key, None)

    def read(self):
        if not self.path.exists():
            return {"version": 1, "templates": {}, "projects": {}, "annotations": {}}
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
        except (ValueError, UnicodeError) as exc:
            raise ValueError("Biblioteca pessoal ilegível; arquivo preservado.") from exc
        self._validate(raw)
        return raw

    @staticmethod
    def _validate(raw):
        if (
            not isinstance(raw, dict)
            or type(raw.get("version")) is not int or raw.get("version") != 1
            or any(
                not isinstance(raw.get(k), dict)
                for k in ("templates", "projects", "annotations")
            )
        ):
            raise ValueError("Biblioteca pessoal inválida; arquivo preservado.")
        for name, value in raw["templates"].items():
            if not isinstance(name, str) or not name.strip():
                raise ValueError("Configuração salva sem nome válido; arquivo preservado.")
            try:
                config = config_from_dict(value)
            except (ValueError, OverflowError) as exc:
                raise ValueError(f"Configuração salva '{name}' inválida: {exc}. Arquivo preservado.") from exc
            if config.circuit is not None:
                raise ValueError(
                    f"Configuração salva '{name}' contém um circuito de portas. "
                    "Use a biblioteca do editor para guardar circuitos; arquivo preservado."
                )
        for name, project in raw["projects"].items():
            if (not isinstance(name, str) or not name.strip() or not isinstance(project, dict)
                    or ("description" in project and not isinstance(project["description"], str))):
                raise ValueError("Agrupamento de projeto inválido; arquivo preservado.")
        for identifier, annotation in raw["annotations"].items():
            if not isinstance(identifier, str) or not identifier.strip() or not isinstance(annotation, dict):
                raise ValueError("Caderno de execução inválido; arquivo preservado.")
            for field in ("title", "project", "notes", "description", "objective", "hypothesis", "methodology"):
                if field in annotation and not isinstance(annotation[field], str):
                    raise ValueError(f"Campo '{field}' do caderno deve ser texto; arquivo preservado.")
            for field in ("tags", "categories"):
                if field in annotation and (not isinstance(annotation[field], list) or
                        any(not isinstance(value, str) for value in annotation[field])):
                    raise ValueError(f"Campo '{field}' do caderno deve ser uma lista de textos; arquivo preservado.")

    def _write(self, raw):
        self._validate(raw)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w", encoding="utf-8", dir=self.path.parent, delete=False
            ) as f:
                temporary = Path(f.name)
                json.dump(raw, f, ensure_ascii=False, indent=2, allow_nan=False)
                f.flush()
                os.fsync(f.fileno())
            temporary.replace(self.path)
        finally:
            if temporary:
                temporary.unlink(missing_ok=True)

    def save_template(self, name, config):
        if not isinstance(name, str) or not name.strip():
            raise ValueError("Informe um nome para a configuração.")
        if not isinstance(config, ExperimentConfig):
            raise ValueError("Configuração inválida para o formulário de simulação.")
        if config.circuit is not None:
            raise ValueError("Circuitos de portas devem ser salvos na biblioteca do editor, não como parâmetros do formulário.")
        try:
            config.validate()
        except OverflowError as exc:
            raise ValueError("Os parâmetros da configuração excedem o intervalo numérico suportado.") from exc
        with self.transaction() as raw:
            raw["templates"][name.strip()] = asdict(config)

    def template(self, name):
        return config_from_dict(self.read()["templates"][name])

    def annotate(
        self, identifier, project, notes, tags, title=None, *,
        description=None, objective=None, hypothesis=None, methodology=None,
        categories=None,
    ):
        if not isinstance(identifier, str) or not identifier:
            raise ValueError("Identificador de execução inválido.")
        if title is not None and (not isinstance(title, str) or len(title) > 160):
            raise ValueError("O nome da execução deve ter até 160 caracteres.")
        for label, value in (("Projeto", project), ("Observações", notes)):
            if not isinstance(value, str):
                raise ValueError(f"{label} deve ser texto.")
        if not isinstance(tags, (list, tuple)) or any(not isinstance(tag, str) for tag in tags):
            raise ValueError("Etiquetas devem ser uma lista de textos.")
        extras = dict(description=description, objective=objective, hypothesis=hypothesis, methodology=methodology)
        for key, value in extras.items():
            if value is not None and (not isinstance(value, str) or len(value) > 20_000):
                raise ValueError("Os campos científicos devem conter até 20.000 caracteres.")
        if categories is not None and (
            not isinstance(categories, (list, tuple))
            or any(not isinstance(value, str) for value in categories)
        ):
            raise ValueError("Categorias devem ser uma lista de textos.")
        with self.transaction() as raw:
            if project.strip():
                raw["projects"].setdefault(project.strip(), {"description": ""})
            annotation = dict(raw["annotations"].get(identifier, {}))
            annotation.update({
                "title": (
                    title.strip() if title is not None
                    else raw["annotations"].get(identifier, {}).get("title", "")
                ),
                "project": project.strip(),
                "notes": notes,
                "tags": list(dict.fromkeys(tag.strip() for tag in tags if tag.strip())),
            })
            for key, value in extras.items():
                if value is not None:
                    annotation[key] = value.strip()
            if categories is not None:
                annotation["categories"] = list(dict.fromkeys(value.strip() for value in categories if value.strip()))
            raw["annotations"][identifier] = annotation

    def delete_template(self, name):
        with self.transaction() as raw:
            raw["templates"].pop(name, None)


def experiment_title(experiment, annotations=None):
    """Presentation name; the immutable technical ID remains the lookup key."""
    annotation = (annotations or {}).get(experiment.id, {})
    title = annotation.get("title", "").strip()
    if title:
        return title
    from core.types import system_label

    return f"{system_label(experiment.config)} · {experiment.created_at.astimezone():%d/%m %H:%M}"
