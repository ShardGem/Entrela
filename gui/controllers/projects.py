"""Project/experiment context layered over the existing drafts and execution services."""
from copy import deepcopy
from dataclasses import replace
from PySide6.QtCore import QObject
from PySide6.QtWidgets import QInputDialog
from data.projects import ProjectStore, SessionProjects
from data.workspace import experiment_title
from core.types import ExperimentConfig, SystemConfig, SimulationProtocol, NoiseConfig


class ProjectController(QObject):
    def __init__(self, window, factory):
        super().__init__(window)
        self.window = window
        try:
            library = window._workspace_library()
            self.session_only = False
        except (OSError, ValueError):
            library = SessionProjects()
            self.session_only = True
        self.store = ProjectStore(library)
        self.factory = deepcopy(factory)
        self.project = None
        self.active_id = None
        self.restoring = False
        self.unsaved_runs = {}
        self.results = {}  # Also retains calculated records when a disk write fails.
        self.launch = None
        self.completed = None
        self.completed_studies = {}
        page = window.page_dashboard
        page.new_circuit.connect(lambda: self.create_work('circuit', 'Novo circuito'))
        page.project_create_requested.connect(self.create_project)
        page.project_selected.connect(self.open_project)
        page.work_selected.connect(self.open_work)
        page.all_projects_requested.connect(lambda: self.open_project(None))
        page.notebook_requested.connect(lambda: window._show_page('notebook'))
        page.ideal_requested.connect(self.compare_ideal)
        key = window.settings.value('projects/active_work', '')
        try:
            raw = self.store.read()
            if key in raw.get('workbench', {}):
                self.active_id = key
                self.project = raw['workbench'][key].get('project', '') or None
                if window.drafts.state.get('active_work_id') != key:
                    window.drafts.restore_workbench(raw['workbench'][key]['draft'])
            elif window.drafts.state.get('simulation') or window.drafts.state.get('editor'):
                saved = window.drafts.workbench_state()
                work = self.store.create_work(saved['simulation'].get('name') or 'Rascunho recuperado', '', 'hamiltonian', saved)
                self.active_id = work['id']
            self.refresh()
        except (OSError, ValueError, TypeError) as exc:
            self.error(exc)

    @property
    def active(self):
        try:
            return self.store.read().get('workbench', {}).get(self.active_id)
        except (OSError, ValueError, TypeError):
            return None

    def error(self, exc):
        self.window.statusBar().showMessage(str(exc))
        self.window.page_simulation.status.set_error(str(exc))

    def persist_active(self, snapshot=None):
        if self.restoring or not self.active_id:
            return
        w = self.window
        snapshot = snapshot or w.drafts.workbench_state()
        work = self.active
        if work is None:
            return
        name = w.page_circuit.editor.circuit_name.text() if work['kind'] == 'circuit' else w.page_simulation.experiment_name.text()
        self.store.save_draft(self.active_id, {key: deepcopy(snapshot[key]) for key in ('simulation', 'editor')}, name)
        w.settings.setValue('projects/active_work', self.active_id)
        if self.session_only:
            raise OSError('Projetos mantidos somente nesta sessão. Restabeleça o armazenamento e exporte os resultados antes de fechar.')

    def save_before_switch(self):
        w = self.window
        if not self.active_id and (w._draft_dirty or w.drafts.identity_dirty or bool(w.page_circuit.editor.document.gates)):
            try:
                snapshot = w.drafts.workbench_state()
                kind = 'circuit' if w._current_page == 'circuit' else 'hamiltonian'
                title = snapshot['editor'].get('name') if kind == 'circuit' else snapshot['simulation'].get('name')
                work = self.store.create_work(title or 'Rascunho preservado', self.project or '', kind, snapshot)
                self.active_id = work['id']
            except (OSError, ValueError, TypeError) as exc:
                self.error(exc); return False
        if not self.window.drafts.flush():
            self.window.statusBar().showMessage('Não foi possível salvar o rascunho. Corrija o armazenamento antes de trocar de experimento. ' + self.window.drafts.error)
            return False
        return True

    def refresh(self):
        w = self.window
        try:
            raw = self.store.read()
            works = self.store.works(self.project)
            w.page_dashboard.load_recent(w._history)
            w.page_dashboard.set_annotations(raw['annotations'])
            w.page_dashboard.load_projects(self.store.projects(), works, self.project,
                raw['projects'].get(self.project, {}), self.ideal_pair())
            if hasattr(w, 'page_notebook'):
                w.page_notebook.set_project(self.project, raw['projects'].get(self.project, {}))
            if hasattr(w, 'page_catalog'):
                w.page_catalog.refresh(raw)
        except (OSError, ValueError, TypeError) as exc:
            self.error(exc)

    def create_project(self):
        name, accepted = QInputDialog.getText(self.window, 'Criar projeto', 'Nome da investigação:')
        if not accepted: return
        try:
            name = self.store.create_project(name)
            self.open_project(name)
        except (OSError, ValueError, TypeError) as exc:
            self.error(exc)

    def open_project(self, name):
        if not self.save_before_switch(): return
        changed = name != self.project
        self.project = name
        self.window.page_dashboard.set_mode('overview')
        if changed and name is not None:
            try:
                annotations = self.store.read()['annotations']
                current = self.window._current_experiment
                if current is None or annotations.get(current.id, {}).get('project', '') != name:
                    latest = next((record for record in self.window._history if annotations.get(record.id, {}).get('project', '') == name and not record.result.error), None)
                    if latest: self.show_execution(latest.id, navigate=False)
                    else: self.window.clear_execution_context()
            except (OSError, ValueError, TypeError) as exc: self.error(exc)
        self.refresh()
        self.window._show_page('dashboard')

    def open_tool(self, key):
        if key in ('simulation', 'circuit'):
            kind = 'circuit' if key == 'circuit' else 'hamiltonian'
            active = self.active
            if active and active.get('project', '') != (self.project or ''):
                work = next((work for work in self.store.works(self.project or '') if work['kind'] == kind), None)
                if work: self.open_work(work['id'])
                else: self.create_work(kind)
                return
        self.window.navigation.open_page(key)

    def choose_new(self):
        kind, accepted = QInputDialog.getItem(self.window, 'Novo experimento', 'Como deseja preparar o sistema?',
            ['Evolução por Hamiltoniano', 'Circuito livre de portas'], 0, False)
        if accepted:
            self.create_work('circuit' if kind.startswith('Circuito') else 'hamiltonian')

    def create_work(self, kind='hamiltonian', title='Novo experimento', config=None, description=''):
        w = self.window
        if not self.save_before_switch(): return False
        try:
            work = self.store.create_work(title, self.project or '', kind, self.factory)
            self._activate(work, load_result=False)
            if kind == 'hamiltonian':
                config = config or ExperimentConfig(SystemConfig(), SimulationProtocol(), NoiseConfig(enabled=False), w.page_settings.spin_shots.value(), 42)
                w._apply_draft(config, title)
                w.page_simulation.experiment_name.setText(title)
                w.page_simulation.experiment_description.setText(description)
                w.page_simulation.config_panel.set_section('system')
            else:
                w.page_circuit.editor.circuit_name.setText(title)
            self.persist_active()
            self.refresh()
            w._show_page('circuit' if kind == 'circuit' else 'simulation')
            return True
        except (OSError, ValueError, TypeError, KeyError) as exc:
            self.error(exc); return False

    def ensure_active(self, kind=None):
        w = self.window
        kind = kind or ('circuit' if w._current_page == 'circuit' else 'hamiltonian')
        active = self.active
        if active and active['project'] == (self.project or '') and active['kind'] == kind:
            return active
        snapshot = w.drafts.workbench_state()
        title = w.page_circuit.editor.circuit_name.text() if kind == 'circuit' else w.page_simulation.experiment_name.text()
        work = self.store.create_work(title or ('Circuito livre' if kind == 'circuit' else 'Evolução por Hamiltoniano'), self.project or '', kind, snapshot)
        self.active_id = work['id']; w.settings.setValue('projects/active_work', self.active_id)
        return work

    def _activate(self, work, load_result=True):
        w = self.window
        self.restoring = True
        try:
            self.active_id = work['id']; self.project = work.get('project', '')
            w.drafts.restore_workbench(work['draft'])
            w.settings.setValue('projects/active_work', self.active_id)
            w._current_experiment = None
            w._unsaved_result = False
            w._pending_example_id = None
            w.clear_execution_context()
            w.page_workspace._apply_route('circuit:edit' if work['kind'] == 'circuit' else 'simulation')
            latest = work.get('latest_execution')
            if load_result and latest:
                self.show_execution(latest, navigate=False)
        finally:
            self.restoring = False

    def open_work(self, key):
        if not self.save_before_switch(): return
        try:
            work = self.store.read().get('workbench', {})[key]
            self._activate(work)
            self.refresh()
            self.window._show_page('circuit' if work['kind'] == 'circuit' else 'simulation')
        except (OSError, ValueError, TypeError, KeyError) as exc: self.error(exc)

    def show_execution(self, identifier, navigate=True):
        """Consult immutable data. This intentionally never loads controls into a draft."""
        w = self.window
        try:
            record = self.results.get(identifier) or w.repository.load(identifier)
            self.results[identifier] = record
            w._current_experiment = record
            w._unsaved_result = not any(e.id == identifier for e in w._history)
            w._display_experiment(record)
            if navigate:
                w._show_page('results')
                w.tutorial.record_open(identifier)
            return record
        except (OSError, ValueError, TypeError, KeyError, AttributeError) as exc:
            self.error('Não foi possível abrir a execução: ' + str(exc))

    def open_completed(self, identifier):
        record = self.show_execution(identifier)
        data = self.completed_studies.pop(identifier, None)
        if record is not None and data is not None:
            self.window.page_analysis.show_analysis(data)
            self.window._show_page('analysis')

    def use_configuration(self, identifier):
        w = self.window
        try:
            record = self.results.get(identifier) or w.repository.load(identifier)
            if not w._can_replace(record.config): return
            kind = 'circuit' if record.config.circuit is not None else 'hamiltonian'
            if not self.create_work(kind, w._experiment_name(record) + ' · cópia', None if kind == 'circuit' else record.config): return
            if kind == 'circuit':
                from core.circuit_document import CircuitDocument
                document = record.config.circuit
                w.page_circuit.editor.replace_document(document, 'Usar configuração registrada')
            self.persist_active()
        except (OSError, ValueError, TypeError, KeyError) as exc: self.error(exc)

    def capture_launch(self, worker):
        kind = 'circuit' if worker.config.circuit is not None else 'hamiltonian'
        active = self.ensure_active(kind)
        self.persist_active()
        self.window.page_workspace._last_preparation = 'circuit:edit' if kind == 'circuit' else 'simulation'
        self.launch = dict(work_id=active['id'], project=active.get('project', ''),
            title=self.window.page_circuit.editor.circuit_name.text() if kind == 'circuit' else self.window.page_simulation.experiment_name.text(),
            description=(self.window.page_circuit.editor.circuit_description.text() if kind == 'circuit' else self.window.page_simulation.experiment_description.text()), config=deepcopy(worker.config),
            example_id=self.window._pending_example_id, circuit_context=deepcopy(self.window._pending_circuit_context),
            page=self.window._current_page)
        return deepcopy(self.launch)

    def receive(self, record):
        self.results[record.id] = record
        self.unsaved_runs[record.id] = record
        launch = self.launch
        if not launch: return True
        try:
            self.store.link_execution(launch['work_id'], record.id)
        except (OSError, ValueError, TypeError) as exc:
            self.error('Resultado calculado; vínculo do projeto ainda não salvo: ' + str(exc))
        self.completed = record.id
        self.refresh()
        return (self.active_id == launch['work_id'] and (self.project or '') == launch['project']
                and (self.window._current_page in ('simulation', 'circuit', 'results', 'bloch') or self.window._current_page == launch.get('page')))

    def ideal_pair(self):
        from core.comparison import incompatibility
        records = [r for r in self.window._history if not r.result.error and not r.result.mitigation]
        annotations = self.store.read()['annotations']
        records = [r for r in records if self.project is None or annotations.get(r.id, {}).get('project', '') == self.project]
        for noisy in records:
            if not noisy.config.noise.enabled: continue
            for ideal in records:
                if ideal.config.noise.enabled or ideal.id == noisy.id: continue
                if not incompatibility(ideal, noisy, mode='controlled'):
                    return (ideal.id, noisy.id, experiment_title(ideal, annotations), experiment_title(noisy, annotations))
        return None

    def compare_ideal(self):
        pair = self.ideal_pair()
        if pair: self.window._compare_from_history(*pair[:2])
