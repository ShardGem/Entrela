from core.types import system_label

"""Application controller: real executions, learning flows and durable records."""

from dataclasses import asdict, replace
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4
import json
from PySide6.QtCore import QSettings, Qt, QTimer, QSignalBlocker
from PySide6.QtGui import QShortcut, QKeySequence
from PySide6.QtWidgets import (
    QMainWindow,
    QWidget,
    QHBoxLayout,
    QVBoxLayout,
    QStackedWidget,
    QStatusBar,
    QDockWidget,
    QTextBrowser,
    QFileDialog,
    QMessageBox,
)
from gui.theme import build_qss
from gui.manual import WELCOME_HTML
from gui.widgets.sidebar import Sidebar
from gui.widgets.topbar import Topbar
from gui.widgets.tutorial import BellTutorial, STEPS
from gui.widgets.command_palette import CommandPalette
from gui.pages.dashboard import DashboardPage
from gui.pages.simulation import SimulationPage
from gui.pages.circuit import CircuitPage
from gui.pages.results import ResultsPage
from gui.pages.bloch import BlochPage
from gui.pages.mitigation import MitigationPage
from gui.pages.history import HistoryPage
from gui.pages.settings import SettingsPage
from gui.pages.docs import DocsPage
from gui.pages.examples import ExamplesPage
from gui.pages.comparison import ComparisonPage
from gui.pages.analysis import AnalysisPage
from gui.pages.library import LibraryPage
from gui.pages.documentation import DocumentationPage
from gui.controllers.appearance import apply_appearance, DARK
from gui.theme import PALETTE
from gui.workers.analysis_worker import AnalysisWorker
from gui.workers.storage_worker import StorageWorker
from gui.workers.report_worker import ReportWorker
from gui.workers.comparison_worker import ComparisonWorker
from gui.workers.documentation_worker import DocumentationWorker
from data.workspace import WorkspaceLibrary
from data.protocols import ProtocolRepository
from core.report import export_rendered_report
from gui.workers.simulation_worker import SimulationWorker
from gui.workers.mitigation_worker import MitigationWorker
from core.types import (
    Experiment,
    ExperimentResult,
    ExperimentConfig,
    SystemConfig,
    SimulationProtocol,
    NoiseConfig,
    config_from_dict,
)
from copy import deepcopy
from core.examples import EXAMPLES, get_example, create_example_config
from core.export import (
    export_experiment_csv,
    export_experiment_json,
    import_experiment_json,
    export_figure,
)
from data.repository import ExperimentRepository

PAGE_META = {
    "documentation": ("Documentação", "Figuras, animações e rastreabilidade"),
    "analysis": ("Análises", "Referência exata, correlações e varreduras"),
    "library": ("Projetos", "Modelos e notas pessoais"),
    "dashboard": ("Início", "Seu laboratório quântico"),
    "examples": ("Exemplos", "Aprenda a partir de experimentos reais"),
    "simulation": ("Experimento", "Configure e execute"),
    "circuit": ("Circuito", "Preparação, evolução e medição"),
    "results": ("Resultados", "Dados da execução selecionada"),
    "bloch": ("Evolução 3D", "Estados efetivamente simulados"),
    "mitigation": ("Mitigação", "Extrapolação de observáveis"),
    "comparison": ("Comparações", "Experimentos compatíveis"),
    "history": ("Histórico", "Resultados preservados"),
    "docs": ("Aprender", "Conceitos e ajuda"),
    "settings": ("Configurações", "Preferências"),
}


class MainWindow(QMainWindow):
    def __init__(self, repository=None, settings=None):
        super().__init__()
        self.setWindowTitle("Entrela · Laboratório quântico")
        self.resize(1440, 900)
        self.setMinimumSize(1020, 720)
        self.settings = (
            settings if settings is not None else QSettings("Entrela", "TCC")
        )
        self.repository = repository
        self._storage_error = ""
        if self.repository is None:
            try:
                self.repository = ExperimentRepository()
            except OSError as exc:
                self._storage_error = str(exc)
        self._storage_worker = None
        self._current_worker = None
        self._current_experiment = None
        self._running_config = None
        self._unsaved_result = False
        self._close_pending = False
        self._loading_draft = True
        self._draft_dirty = False
        self._draft_baseline = None
        self._pending_example_id = None
        self._pending_parent_id = None
        self._current_page = "dashboard"
        self._history = []
        for key, value in DARK.items():
            object.__setattr__(PALETTE, key, value)
        self.setStyleSheet(build_qss())
        self._build_ui()
        self._build_help()
        self._build_tutorial()
        self._wire_signals()
        self._build_commands()
        try:
            shots = int(self.settings.value("shots", 8192))
        except (ValueError, TypeError):
            shots = 8192
        self.page_settings.spin_shots.setValue(shots)
        self.page_simulation.config_panel.spin_shots.setValue(shots)
        self._restore_workspace()
        self._refresh_history()
        self._restore_preferences()
        self._refresh_library()
        self._show_page("dashboard")
        if self._storage_error:
            self.statusBar().showMessage(
                "Armazenamento indisponível: " + self._storage_error
            )

    def _build_ui(self):
        root = QWidget()
        root.setObjectName("RootWidget")
        self.setCentralWidget(root)
        layout = QHBoxLayout(root)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self.sidebar = Sidebar()
        layout.addWidget(self.sidebar)
        right = QWidget()
        body = QVBoxLayout(right)
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(0)
        self.topbar = Topbar()
        body.addWidget(self.topbar)
        self.stack = QStackedWidget()
        body.addWidget(self.stack, 1)
        layout.addWidget(right, 1)
        self.page_dashboard = DashboardPage()
        self.page_examples = ExamplesPage()
        self.page_simulation = SimulationPage()
        self.page_circuit = CircuitPage()
        self.page_results = ResultsPage()
        self.page_bloch = BlochPage()
        self.page_mitigation = MitigationPage()
        self.page_comparison = ComparisonPage()
        self.page_history = HistoryPage()
        self.page_docs = DocsPage(WELCOME_HTML)
        self.page_settings = SettingsPage()
        self.page_analysis = AnalysisPage()
        self.page_library = LibraryPage()
        self.page_documentation = DocumentationPage()
        self.pages = dict(
            dashboard=self.page_dashboard,
            examples=self.page_examples,
            simulation=self.page_simulation,
            circuit=self.page_circuit,
            results=self.page_results,
            bloch=self.page_bloch,
            mitigation=self.page_mitigation,
            comparison=self.page_comparison,
            history=self.page_history,
            docs=self.page_docs,
            settings=self.page_settings,
        )
        self.pages.update(analysis=self.page_analysis, library=self.page_library)
        self.pages["documentation"]=self.page_documentation
        for page in self.pages.values():
            self.stack.addWidget(page)
        self.setStatusBar(QStatusBar())

    def _build_help(self):
        self.help_dock = QDockWidget("Ajuda contextual", self)
        self.help_dock.setObjectName("ScientificHelp")
        self.help_dock.setMinimumWidth(300)
        self.help_browser = QTextBrowser()
        self.help_browser.setHtml(WELCOME_HTML)
        self.help_dock.setWidget(self.help_browser)
        self.addDockWidget(Qt.RightDockWidgetArea, self.help_dock)
        self.help_dock.hide()

    def _build_tutorial(self):
        self.tutorial = BellTutorial()
        self.tutorial_dock = QDockWidget("Aprender fazendo · Bell", self)
        self.tutorial_dock.setObjectName("BellTutorial")
        self.tutorial_dock.setWidget(self.tutorial)
        self.addDockWidget(Qt.RightDockWidgetArea, self.tutorial_dock)
        self.tutorial_dock.hide()
        self.tutorial.section_requested.connect(self._tutorial_section)
        self.tutorial.progress_changed.connect(self._persist_tutorial)
        self.tutorial.paused.connect(self.tutorial_dock.hide)
        self.tutorial.completed.connect(self._tutorial_completed)
        self.tutorial_dock.visibilityChanged.connect(self._tutorial_visibility)

    def _wire_signals(self):
        self.sidebar.compact_requested.connect(self._toggle_sidebar)
        self.sidebar.navigate.connect(self._show_page)
        self.topbar.help_requested.connect(lambda: self._show_help("Início"))
        self.topbar.commands_requested.connect(self._open_commands)
        p = self.page_simulation
        p.run_requested.connect(self._run_simulation)
        p.cancel_requested.connect(self._cancel_simulation)
        p.config_panel.ajuda_acionada.connect(self._show_help)
        p.config_panel.parametros_alterados.connect(self._draft_changed)
        p.config_panel.mode_changed.connect(
            lambda mode: self.settings.setValue("workspace/mode", mode)
        )
        self.page_dashboard.new_simulation.connect(self._new_experiment)
        self.page_dashboard.open_history.connect(lambda: self._show_page("history"))
        self.page_dashboard.examples_requested.connect(
            lambda: self._show_page("examples")
        )
        self.page_dashboard.tutorial_requested.connect(self._begin_tutorial)
        self.page_dashboard.experiment_selected.connect(self._open_experiment)
        self.page_examples.example_requested.connect(self._load_example)
        self.page_examples.tutorial_requested.connect(self._begin_tutorial)
        self.page_history.experiment_selected.connect(self._open_experiment)
        self.page_results.save_requested.connect(self._save_current)
        self.page_results.export_requested.connect(self._export_counts)
        self.page_results.export_experiment_requested.connect(self._export_experiment)
        self.page_results.export_figures_requested.connect(self._export_figures)
        self.page_mitigation.run_requested.connect(self._run_mitigation)
        self.page_settings.spin_shots.valueChanged.connect(self._set_default_shots)
        self.page_settings.appearance_changed.connect(self._apply_preferences)
        self.page_settings.restore_requested.connect(self._reset_preferences)
        self.page_bloch.preferences_changed.connect(self._persist_bloch_preferences)
        self.page_bloch.frame_changed.connect(self.page_analysis.select_frame)
        self.page_bloch.temporal_requested.connect(
            lambda: self._run_analysis("temporal", {})
        )
        self.page_circuit.snapshot_requested.connect(self._show_circuit_snapshot)
        self.page_circuit.run_requested.connect(self._run_editor_circuit)
        self.page_analysis.requested.connect(self._run_analysis)
        self.page_analysis.cancel_requested.connect(self._cancel_simulation)
        self.page_analysis.protocol.save_requested.connect(self._save_protocol)
        self.page_analysis.protocol.load_requested.connect(self._load_protocol)
        self.page_comparison.prepare_requested.connect(self._prepare_comparison)
        self.page_comparison.documentation_requested.connect(self._document_comparison)
        self.page_documentation.export_requested.connect(self._export_documentation)
        self.page_documentation.cancel_requested.connect(self._cancel_simulation)
        self.page_documentation.comparison_changed.connect(self._refresh_documentation)
        self.page_documentation.analysis_selected.connect(self._open_evidence)
        from gui.widgets.button import SecondaryButton
        self.export_bloch_view=SecondaryButton("Exportar vista PNG / SVG / PDF")
        self.export_bloch_view.clicked.connect(self._export_bloch_view)
        self.page_bloch.add_action(self.export_bloch_view)
        self.page_results.rerun_requested.connect(self._rerun_current)
        self.page_results.report_requested.connect(self._export_report)
        self.page_library.template_save_requested.connect(self._save_template)
        self.page_library.template_load_requested.connect(self._load_template)
        self.page_library.annotation_requested.connect(self._annotate_current)
        self.page_library.template_delete_requested.connect(self._delete_template)

    def _build_commands(self):
        self.command_palette = CommandPalette(self)
        self.command_palette.command_requested.connect(self._command)
        self.shortcuts = []
        for key, callback in [
            ("Ctrl+K", self._open_commands),
            ("Ctrl+N", self._new_experiment),
            ("Ctrl+O", self._import_experiment),
            ("Ctrl+Return", self._run_simulation),
            ("F1", lambda: self._show_help("Início")),
            ("F11", self._toggle_presentation),
        ]:
            shortcut = QShortcut(QKeySequence(key), self)
            shortcut.activated.connect(callback)
            self.shortcuts.append(shortcut)

    def _open_commands(self):
        commands = [
            ("new", "Criar experimento", "novo"),
            ("import", "Importar experimento JSON", "abrir arquivo"),
            ("tutorial", "Aprender: tutorial de Bell", "primeiro experimento"),
            ("mode:guided", "Usar modo Guiado", "ajuda etapas"),
            ("mode:advanced", "Usar modo Avançado", "parâmetros"),
        ]
        commands += [
            ("page:" + key, "Abrir " + dict(Sidebar.ITEMS).get(key,title), "navegar "+title+" "+description)
            for key, (title, description) in PAGE_META.items()
        ]
        commands += [
            ("example:" + e.id, "Exemplo: " + e.title, e.description) for e in EXAMPLES
        ]
        commands += [
            ("run:" + e.id, "Abrir execução " + e.id, system_label(e.config))
            for e in self._history[:20]
        ]
        commands += [
            ("help:" + word, "Conceito: " + word, word)
            for word in (
                "Fidelidade",
                "Pureza",
                "Hamiltoniano",
                "T₁",
                "T₂",
                "Shots",
                "Semente",
                "Mitigação",
                "Evolução",
            )
        ]
        self.command_palette.open_commands(commands)

    def _command(self, identifier):
        if identifier == "new":
            self._new_experiment()
        elif identifier == "import":
            self._import_experiment()
        elif identifier == "tutorial":
            self._begin_tutorial()
        elif identifier.startswith("page:"):
            self._show_page(identifier[5:])
        elif identifier.startswith("example:"):
            self._load_example(identifier[8:])
        elif identifier.startswith("run:"):
            self._open_experiment(identifier[4:])
        elif identifier.startswith("help:"):
            self._show_help(identifier[5:])
        elif identifier.startswith("mode:"):
            self.page_simulation.config_panel.set_mode(identifier[5:])

    def _show_help(self, topic):
        aliases = {
            "J — acoplamento": "Hamiltoniano",
            "h — campo": "Hamiltoniano",
            "Estado inicial": "Qubits",
            "Tempo total (ℏ=1)": "Evolução",
            "Passos Trotter": "Evolução",
            "Ordem Suzuki": "Evolução",
            "Despolarização 1q": "Ruído",
            "Despolarização 2q": "Ruído",
            "Modelo de ruído": "Ruído",
        }
        topic = aliases.get(topic, topic)
        if self.width() < 1250:
            self.help_dock.setFloating(True)
        self.help_dock.show()
        self.help_browser.scrollToAnchor(topic)
        self.help_browser.find(topic)

    def _show_page(self, key):
        if key=="documentation":
            self._refresh_documentation()
        if key not in self.pages:
            return
        self._current_page = key
        self.stack.setCurrentWidget(self.pages[key])
        self.sidebar.set_active(key)
        group=next((title for _,title,_,items in Sidebar.GROUPS if key in items),"Aplicativo")
        self.topbar.set_context(dict(Sidebar.ITEMS).get(key,PAGE_META[key][0]),group+" · Entrela")
        self._update_tutorial()

    def _restore_workspace(self):
        panel = self.page_simulation.config_panel
        try:
            raw = self.settings.value("workspace/draft", "")
            if raw:
                panel.load_config(config_from_dict(json.loads(raw)))
        except (ValueError, TypeError):
            self.statusBar().showMessage(
                "Rascunho anterior inválido; configuração padrão carregada."
            )
        mode = self.settings.value("workspace/mode", "guided")
        panel.set_mode(mode if mode in ("guided", "advanced") else "guided")
        self._draft_baseline = panel.get_config()
        self._loading_draft = False

    def _apply_draft(self, config, title="Rascunho"):
        if config.circuit is not None:
            self.statusBar().showMessage(
                "Circuito livre selecionado: use a página Circuitos para criar uma cópia editável."
            )
            return
        self._loading_draft = True
        try:
            self.page_simulation.config_panel.load_config(config)
        finally:
            self._loading_draft = False
        self._draft_baseline = config
        self._draft_dirty = False
        self.page_simulation.set_title(
            title, "Cópia editável · resultados anteriores permanecem preservados."
        )
        self.settings.setValue("workspace/draft", json.dumps(asdict(config)))

    def _draft_changed(self):
        if not self._loading_draft:
            try:
                config = self.page_simulation.config_panel.get_config()
                self._draft_dirty = config != self._draft_baseline
                self.settings.setValue("workspace/draft", json.dumps(asdict(config)))
            except ValueError:
                self._draft_dirty = True
        self._update_tutorial()

    def _can_replace(self, config=None):
        if self._current_worker is not None:
            self.statusBar().showMessage("Aguarde ou cancele a execução atual.")
            return False
        if not self._confirm_unsaved():
            return False
        current = None
        try:
            current = self.page_simulation.config_panel.get_config()
        except ValueError:
            pass
        if self._draft_dirty and current != config:
            return (
                QMessageBox.question(
                    self,
                    "Substituir configuração?",
                    "O rascunho foi editado. Deseja substituí-lo? Os resultados salvos serão preservados.",
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.No,
                )
                == QMessageBox.Yes
            )
        return True

    def _new_experiment(self):
        cfg = ExperimentConfig(
            SystemConfig(),
            SimulationProtocol(),
            NoiseConfig(enabled=False),
            self.page_settings.spin_shots.value(),
            42,
        )
        if not self._can_replace(cfg):
            return
        if self.tutorial.active:
            self.tutorial.pause()
        self._pending_example_id = None
        self._apply_draft(cfg, "Novo experimento")
        self.page_simulation.config_panel.set_section("system")
        self._show_page("simulation")

    def _load_example(self, identifier):
        example = get_example(identifier)
        cfg = example.create_config()
        if not self._can_replace(cfg):
            return
        if self.tutorial.active:
            self.tutorial.pause()
        self._pending_example_id = identifier
        self._apply_draft(cfg, example.title + " · cópia")
        self.page_simulation.config_panel.set_section("system")
        self._show_page("simulation")

    def _set_default_shots(self, value):
        self.settings.setValue("shots", value)

    def _begin_tutorial(self):
        try:
            step = int(self.settings.value("tutorial/bell/step", 0))
        except (ValueError, TypeError):
            step = 0
        completed = self.settings.value("tutorial/bell/completed", False, type=bool)
        if completed:
            step = 0
        step = max(0, min(step, 6))
        experiment = None
        identifier = self.settings.value("tutorial/bell/run_id", "")
        if self.repository is not None and identifier and not completed:
            try:
                candidate = self.repository.load(identifier)
                if (
                    BellTutorial.matches(candidate.config)
                    and not candidate.result.error
                ):
                    experiment = candidate
            except (OSError, ValueError, KeyError, TypeError):
                pass
        if step >= 5 and experiment is None:
            step = 4
        cfg = (
            experiment.config
            if step >= 4 and experiment
            else ExperimentConfig(
                SystemConfig(
                    2 if step >= 1 else 1,
                    J=0,
                    h=0,
                    initial_state="bell" if step >= 2 else "zero",
                ),
                SimulationProtocol(save_snapshots=step >= 4),
                NoiseConfig(enabled=step < 3),
                shots=4096,
                seed=42,
            )
        )
        if not self._can_replace(cfg):
            return
        self._pending_example_id = "bell"
        self._apply_draft(cfg, "Tutorial · Seu primeiro Bell")
        self.page_simulation.config_panel.set_mode("guided")
        self.help_dock.hide()
        self.tutorial_dock.show()
        self.settings.setValue("tutorial/bell/completed", False)
        self.tutorial.start(step, experiment)
        self._show_page("simulation")
        self._persist_tutorial()

    def _tutorial_section(self, key):
        self.page_simulation.config_panel.set_section(key)
        if self.tutorial.step < 5:
            self._show_page("simulation")

    def _update_tutorial(self):
        if not hasattr(self, "tutorial"):
            return
        try:
            config = self.page_simulation.config_panel.get_config()
        except ValueError:
            config = None
        self.tutorial.update_context(config, self._current_page)

    def _persist_tutorial(self):
        if not self.tutorial.started:
            return
        self.settings.setValue("tutorial/bell/step", self.tutorial.step)
        self.settings.setValue("tutorial/bell/run_id", self.tutorial.run_id or "")

    def _tutorial_completed(self):
        self.settings.setValue("tutorial/bell/completed", True)
        self.statusBar().showMessage(
            "Tutorial concluído: configuração, execução, análise e reabertura verificadas."
        )

    def _tutorial_visibility(self, visible):
        if not visible and self.tutorial.active:
            self.tutorial.pause()

    def _run_simulation(self, *_):
        if self._current_worker is not None or not self._confirm_unsaved():
            return
        try:
            config = self.page_simulation.config_panel.get_config()
        except ValueError as exc:
            self.page_simulation.status.set_error(str(exc))
            return
        self._start_worker(SimulationWorker(config, self), self._on_experiment)

    def _start_worker(self, worker, callback):
        self._current_worker = worker
        self._running_config = worker.config
        worker.completed.connect(callback)
        worker.error.connect(self._on_error)
        worker.cancelled.connect(self._on_cancelled)
        worker.progress.connect(self.page_simulation.status._progress.setValue)
        worker.progress.connect(self.page_analysis.progress.setValue)
        worker.progress.connect(self.page_documentation.progress.setValue)
        worker.finished.connect(self._on_thread_finished)
        self.page_simulation.set_running(True)
        self.page_mitigation.set_running(True)
        self.page_analysis.set_running(True)
        self.page_circuit.set_running(True)
        self.page_bloch.metrics.set_busy(True)
        self.page_comparison.set_running(True)
        self.page_documentation.set_running(True)
        worker.start()

    def _run_mitigation(self, qubit, method, shots):
        if self._current_worker is not None or self._current_experiment is None:
            return
        if self._current_experiment.result.error or not self._confirm_unsaved():
            return
        self._zne_source = self._current_experiment
        seed = self._zne_source.result.metadata.get(
            "effective_seed", self._zne_source.config.seed
        )
        worker = MitigationWorker(
            replace(self._zne_source.config, seed=seed), qubit, method, shots, self
        )
        self._start_worker(worker, self._on_mitigation)

    def _on_experiment(self, experiment):
        if self._current_worker and self._current_worker.isInterruptionRequested():
            self._on_cancelled()
            return
        if self._pending_example_id:
            experiment.result.metadata["example_id"] = self._pending_example_id
        if self._pending_parent_id:
            experiment.result.metadata["reproduced_from_id"]=self._pending_parent_id
            self._pending_parent_id=None
        self._current_experiment = experiment
        self._unsaved_result = True
        self._draft_baseline = experiment.config
        self._draft_dirty = False
        self.tutorial.record_run(experiment)
        self._display_experiment(experiment)
        self._autosave_current()
        self._show_page(
            "bloch" if experiment.config.protocol.save_snapshots else "results"
        )

    def _on_mitigation(self, analysis):
        if self._current_worker and self._current_worker.isInterruptionRequested():
            self._on_cancelled()
            return
        source = self._zne_source
        analysis = {**analysis, "source_experiment_id": source.id}
        metadata = deepcopy(source.result.metadata)
        metadata.setdefault("reproduction", {}).update(
            mitigation_method="zne",
            mitigation_parameters={key: analysis[key] for key in ("method", "scale_factors", "qubit", "shots", "seed")},
        )
        self._current_experiment = Experiment(
            source.config,
            replace(source.result, mitigation=analysis, metadata=metadata),
            duration_s=analysis["duration_s"],
            tags=list(dict.fromkeys(source.tags + ["ZNE"])),
        )
        self._unsaved_result = True
        self._display_experiment(self._current_experiment)
        self._autosave_current()
        self._show_page("mitigation")

    def _display_experiment(self, experiment):
        self.page_results.show_experiment(experiment)
        self.page_bloch.load_statevectors(
            experiment.result.states,
            experiment.result.times,
            experiment.result.ideal_statevectors,
            time_unit=experiment.result.metadata.get("time_unit", "adimensional (ℏ=1)"),
        )
        self.page_circuit.show_experiment(experiment)
        self.page_analysis.load_experiment(experiment)
        self._refresh_library()
        self.page_mitigation.load_experiment(experiment)
        if self._current_worker:
            self.page_mitigation.set_running(True)
        self.page_analysis.set_running(self._current_worker is not None)
        self._restore_camera_preferences()
        self._refresh_saved_analyses()

    def _save_current(self):
        if self._current_experiment is None or self._storage_worker is not None:
            return False
        try:
            if self.repository is None:
                self.repository = ExperimentRepository()
            self.repository.save(self._current_experiment)
        except (OSError, ValueError, TypeError) as exc:
            self.page_simulation.status.set_error(
                "Resultado disponível, mas não foi salvo: " + str(exc)
            )
            self.statusBar().showMessage("Use Salvar para tentar novamente.")
            return False
        self._unsaved_result = False
        self._refresh_history()
        self.statusBar().showMessage(
            "Experimento " + self._current_experiment.id + " salvo."
        )
        return True

    def _confirm_unsaved(self):
        if not self._unsaved_result:
            return True
        choice = QMessageBox.warning(
            self,
            "Resultado não salvo",
            "Há um resultado não salvo. O que deseja fazer?",
            QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel,
            QMessageBox.Cancel,
        )
        if choice == QMessageBox.Save:
            return self._save_current()
        if choice == QMessageBox.Discard:
            self._unsaved_result = False
            return True
        return False

    def _refresh_history(self):
        records = []
        if self.repository is not None:
            try:
                records = self.repository.list_summaries()
                if self.repository.load_errors:
                    self.statusBar().showMessage(
                        f"{len(self.repository.load_errors)} arquivo(s) ilegíveis foram preservados."
                    )
            except OSError as exc:
                self.statusBar().showMessage(str(exc))
        self._history = records
        self.page_history.load(records)
        self.page_comparison.load(records)
        self.page_dashboard.load_recent(records[:5])
        latest = next((e for e in records if not e.result.error), None)
        self.page_dashboard.update_stats(
            len(records),
            system_label(latest.config) if latest else None,
            latest.result.fidelity if latest else None,
            latest.result.purity if latest else None,
        )

    def _open_experiment(self, identifier):
        if self._current_worker is not None or self._storage_worker is not None:
            self.statusBar().showMessage("Aguarde ou cancele a tarefa atual antes de abrir outra execução.")
            return
        if self.repository is None:
            return
        try:
            experiment = self.repository.load(identifier)
            if not self._can_replace(experiment.config):
                return
            self._apply_draft(experiment.config, "Execução " + experiment.id)
            self._current_experiment = experiment
            self._unsaved_result = False
            self._display_experiment(experiment)
            self._pending_example_id = experiment.result.metadata.get("example_id")
        except (OSError, ValueError, TypeError, KeyError) as exc:
            self.statusBar().showMessage("Não foi possível abrir: " + str(exc))
            return
        self._show_page("results")
        self.tutorial.record_open(identifier)

    def _cancel_simulation(self):
        if self._current_worker:
            self._current_worker.requestInterruption()
            self.page_simulation.btn_cancel.setEnabled(False)
            self.statusBar().showMessage(
                "Cancelando; aguardando a operação atual do simulador."
            )

    def _on_cancelled(self):
        self.page_analysis.message.setText("Tarefa cancelada; resultados anteriores preservados.")
        if isinstance(self._current_worker,DocumentationWorker):
            self.page_documentation.message.setText("Exportação cancelada; arquivo de destino anterior e dados de origem preservados.")
        elif isinstance(self._current_worker,ComparisonWorker):
            self.page_comparison.message.setText("Carregamento cancelado; registros de origem preservados.")
        self.page_simulation.status.set_idle(
            "Execução cancelada; resultados anteriores preservados"
        )

    def _on_error(self, message):
        if isinstance(self._current_worker,(ComparisonWorker,DocumentationWorker)):
            self.page_documentation.message.setText(message)
            self.page_comparison.message.setText(message)
            self.statusBar().showMessage(message)
            self.page_simulation.status.set_error(message)
            return
        if isinstance(self._current_worker, ReportWorker):
            self.statusBar().showMessage(message)
            self.page_simulation.status.set_error(message)
            return
        if isinstance(self._current_worker, AnalysisWorker):
            self.page_analysis.message.setText(message)
            self.page_bloch.metrics.summary.setText(message)
            self.page_simulation.status.set_error(message)
            return
        self.page_simulation.status.set_error(message)
        self.page_mitigation.set_error(message)
        if self.repository is not None and self._running_config is not None:
            try:
                self.repository.save(
                    Experiment(self._running_config, ExperimentResult(error=message))
                )
                self._refresh_history()
            except (OSError, ValueError, TypeError):
                self.statusBar().showMessage("Não foi possível salvar o diagnóstico.")

    def _on_thread_finished(self):
        worker = self.sender()
        if worker is not self._current_worker:
            return
        self._finish_current_job(worker)

    def _finish_current_job(self, worker):
        if self._storage_worker is not None or worker is not self._current_worker:
            return
        self._current_worker = None
        self._running_config = None
        self.page_simulation.set_running(False)
        self.page_mitigation.set_running(False)
        self.page_analysis.set_running(False)
        self.page_circuit.set_running(False)
        self.page_bloch.metrics.set_busy(False)
        self.page_comparison.set_running(False)
        self.page_documentation.set_running(False)
        self._pending_parent_id=None
        if worker:
            worker.deleteLater()
        if self._close_pending:
            QTimer.singleShot(0, self.close)

    def _import_experiment(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Importar experimento", "", "JSON (*.json)"
        )
        if not path:
            return
        try:
            source = import_experiment_json(path)
            if not self._can_replace(source.config):
                return
            if self.tutorial.active:
                self.tutorial.pause()
            result = replace(
                source.result,
                metadata={**source.result.metadata, "imported_from_id": source.id},
            )
            self._current_experiment = replace(
                source,
                id=uuid4().hex[:12],
                created_at=datetime.now(timezone.utc),
                result=result,
            )
            self._unsaved_result = True
            self._apply_draft(source.config, "Experimento importado")
            self._pending_example_id = None
            self._display_experiment(self._current_experiment)
            self._save_current()
            self._show_page("results")
        except (OSError, ValueError, TypeError, KeyError) as exc:
            self.statusBar().showMessage("Não foi possível importar: " + str(exc))

    def _export_counts(self):
        if (
            self._current_experiment is None
            or not self._current_experiment.result.counts
        ):
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Exportar contagens", "contagens.csv", "CSV (*.csv)"
        )
        if path:
            try:
                annotation = self._current_annotation()
                export_experiment_csv(self._current_experiment, path, annotation=annotation)
                self.statusBar().showMessage("CSV exportado com configuração e proveniência")
            except (OSError, ValueError) as exc:
                self.statusBar().showMessage(str(exc))

    def _export_experiment(self):
        if self._current_experiment is None or self._current_worker is not None:
            return
        path, kind = QFileDialog.getSaveFileName(
            self,
            "Exportar experimento",
            "experimento",
            "JSON (*.json);;Pacote ZIP (*.zip)",
        )
        if path:
            try:
                if not Path(path).suffix:
                    path += ".zip" if "ZIP" in kind else ".json"
                if Path(path).suffix.lower() == ".zip":
                    self.page_documentation.use_comparison.setChecked(False)
                    self._show_page("documentation")
                    self._start_documentation_export([self._current_experiment],path,"zip")
                    return
                else:
                    export_experiment_json(self._current_experiment, path)
                self.statusBar().showMessage("Experimento completo exportado")
            except (OSError, ValueError) as exc:
                self.statusBar().showMessage(str(exc))

    def _export_figures(self):
        if self._current_experiment is None:
            return
        directory = QFileDialog.getExistingDirectory(self, "Exportar figuras PNG")
        if not directory:
            return
        prefix = Path(directory) / ("entrela-" + self._current_experiment.id)
        figures = [
            (
                self.page_results.results_tab.canvas_hist.fig,
                str(prefix) + "-distribuicao.png",
            ),
            (
                self.page_results.results_tab.canvas_evol.fig,
                str(prefix) + "-evolucao.png",
            ),
        ]
        if self._current_experiment.result.states:
            figures.append((self.page_bloch.canvas.fig, str(prefix) + "-bloch.png"))
        if any(Path(p).exists() for _, p in figures):
            if (
                QMessageBox.question(
                    self,
                    "Substituir figuras?",
                    "Já existem figuras desta execução. Substituir?",
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.No,
                )
                != QMessageBox.Yes
            ):
                return
        try:
            for figure, path in figures:
                export_figure(figure, path)
            self.statusBar().showMessage("Figuras exportadas")
        except OSError as exc:
            self.statusBar().showMessage(str(exc))

    def closeEvent(self, event):
        if self._current_worker is not None or self._storage_worker is not None:
            self._close_pending = True
            self._cancel_simulation()
            event.ignore()
            return
        if not self._confirm_unsaved():
            event.ignore()
            return
        self._close_pending = False
        self._persist_tutorial()
        self.page_bloch.timer.stop()
        self._persist_camera()
        self.settings.sync()
        event.accept()

    def _autosave_current(self):
        if self.repository is None:
            self.page_simulation.status.set_error(
                "Armazenamento indisponível; resultado permanece disponível."
            )
            return
        self._storage_worker = StorageWorker(
            self.repository, self._current_experiment, self
        )
        self._storage_worker.completed.connect(self._on_saved)
        self._storage_worker.error.connect(self._on_save_error)
        self._storage_worker.finished.connect(self._on_storage_finished)
        self.statusBar().showMessage("Salvando resultado em segundo plano…")
        self._storage_worker.start()

    def _on_saved(self, identifier):
        if self._current_experiment and self._current_experiment.id == identifier:
            self._unsaved_result = False
        self._refresh_history()
        self.page_simulation.status.set_success(
            "Execução concluída e salva no histórico"
        )
        self.statusBar().showMessage("Experimento " + identifier + " salvo.")

    def _on_save_error(self, message):
        self.page_simulation.status.set_error(
            "Resultado disponível, mas não foi salvo: " + message
        )
        self.statusBar().showMessage("Use Salvar para tentar novamente.")

    def _on_storage_finished(self):
        worker = self._storage_worker
        self._storage_worker = None
        if worker:
            worker.deleteLater()
        if self._current_worker is not None and not self._current_worker.isRunning():
            self._finish_current_job(self._current_worker)
        elif self._close_pending:
            QTimer.singleShot(0, self.close)

    def _run_analysis(self, kind, options):
        if self._current_worker is not None or self._current_experiment is None:
            return
        source = self._current_experiment
        config = replace(
            source.config,
            seed=source.result.metadata.get("effective_seed", source.config.seed),
        )
        panel=self.page_analysis.protocol
        replay=self.page_analysis.replay_context
        self.page_analysis.replay_context=None
        self._analysis_protocol=deepcopy(panel.context() if replay is None else replay)
        if replay is None and panel.loaded and (panel.loaded["source_id"]!=source.id or panel.loaded["kind"]!=kind or panel.loaded["options"]!=options):
            self._analysis_protocol["derived_from_protocol_id"]=panel.loaded["protocol_id"]
            self._analysis_protocol["protocol_id"]=None
        self._analysis_protocol["execution_options"]=deepcopy(options)
        self._start_worker(
            AnalysisWorker(config, kind, source, options, self), self._on_analysis
        )
        self.page_analysis.message.setText(
            "Calculando em segundo plano; cancele pela página Simulação."
        )

    def _on_analysis(self, data):
        # Bind all artifacts to the source captured by the worker, never to a
        # subsequently selected record. Inputs and effective seeds remain explicit.
        worker = self._current_worker
        if worker is not None and worker.isInterruptionRequested():
            self._on_cancelled()
            return
        source = worker.source if isinstance(worker, AnalysisWorker) else self._current_experiment
        data.setdefault("source_id", source.id)
        data.setdefault("analysis_id", uuid4().hex[:12])
        data.setdefault("created_at", datetime.now(timezone.utc).isoformat())
        data.setdefault("config", asdict(source.config))
        data.setdefault("source_metadata", source.result.metadata)
        data.setdefault("protocol",deepcopy(getattr(self,"_analysis_protocol",{})))
        self.page_analysis.show_analysis(data)
        if data.get("kind") == "temporal":
            self.page_bloch.metrics.set_rows(data["rows"])
        if self.repository is not None:
            folder = (
                self.repository.base_dir / ".analyses" / source.id
            )
            path = folder / (data["analysis_id"] + ".json")
            try:
                from data.analyses import save_analysis
                save_analysis(data, path)
            except (OSError, ValueError, TypeError) as exc:
                self.statusBar().showMessage(
                    "Análise disponível; falha ao guardar: " + str(exc)
                )
        self._refresh_saved_analyses()
        self.page_simulation.status.set_success(
            "Análise concluída; execução original preservada"
        )

    def _rerun_current(self):
        if self._current_experiment is None or self._current_worker is not None:
            return
        source = self._current_experiment
        if source.result.mitigation:
            m = source.result.mitigation
            zne_seed = m.get("seed", source.result.metadata.get("effective_seed", source.config.seed))
            if zne_seed is None:
                self.statusBar().showMessage("Análise ZNE sem semente registrada; configure uma nova análise.")
                return
            if not self._confirm_unsaved():
                return
            self._zne_source = source
            self._start_worker(
                MitigationWorker(replace(source.config, seed=zne_seed), m["qubit"], m["method"], m["shots"], self, scale_factors=m["scale_factors"]),
                self._on_mitigation,
            )
            self.statusBar().showMessage("Reproduzindo ZNE; métricas da execução de origem preservadas.")
            return
        seed = source.result.metadata.get("effective_seed", source.config.seed)
        if seed is None:
            self.statusBar().showMessage(
                "Registro sem semente efetiva; escolha uma no formulário para criar uma nova execução."
            )
            return
        if not self._confirm_unsaved():
            return
        self._pending_example_id = source.result.metadata.get("example_id")
        self._pending_parent_id=source.id
        config = replace(source.config, seed=seed)
        self._apply_draft(config, "Reprodução de " + source.id)
        self._start_worker(SimulationWorker(config, self), self._on_experiment)

    def _export_report(self):
        if self._current_experiment is None or self._current_worker is not None:
            return
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Exportar relatório acadêmico",
            "relatorio.html",
            "HTML (*.html);;PDF (*.pdf)",
        )
        if not path:
            return
        try:
            annotation = self._current_annotation()
            self._report_path = path
            self._start_worker(
                ReportWorker(self._current_experiment, self.page_analysis.data, annotation, self),
                self._on_report_prepared,
            )
            self.statusBar().showMessage("Preparando gráficos e relatório em segundo plano…")
        except (OSError, ValueError) as exc:
            self.statusBar().showMessage(str(exc))

    def _on_report_prepared(self, html):
        if self._current_worker and self._current_worker.isInterruptionRequested():
            self._on_cancelled()
            return
        try:
            # Qt printing requires the GUI thread; numerical work is already done.
            export_rendered_report(html, self._report_path)
            self.statusBar().showMessage("Relatório exportado: " + self._report_path)
            self.page_simulation.status.set_success("Relatório concluído")
        except (OSError, ValueError, RuntimeError) as exc:
            self.statusBar().showMessage("Não foi possível exportar: " + str(exc))

    def _workspace_library(self):
        if self.repository is None:
            raise ValueError("Armazenamento indisponível.")
        return WorkspaceLibrary(self.repository.base_dir / ".workspace")

    def _current_annotation(self):
        # Exports remain a recovery path even if workspace storage is unavailable.
        if self.repository is None or self._current_experiment is None:
            return None
        try:
            return self._workspace_library().read()["annotations"].get(self._current_experiment.id)
        except (OSError, ValueError, TypeError, KeyError):
            return None

    def _refresh_library(self):
        try:
            data = self._workspace_library().read()
            identifier = (
                self._current_experiment.id if self._current_experiment else None
            )
            self.page_library.load(data, identifier)
            self.page_history.annotations = data["annotations"]
            self.page_history._filter()
            self._refresh_protocols()
            self.page_comparison.annotations = data["annotations"]
            self.page_comparison.load(list(self.page_comparison.records.values()))
            if hasattr(self.page_dashboard, "set_annotations"):
                self.page_dashboard.set_annotations(data["annotations"])
            if identifier:
                title = data["annotations"].get(identifier, {}).get("title", "")
                self.page_results.set_title(title or "Resultados", "Dados da execução selecionada · ID " + identifier)
        except (OSError, ValueError, TypeError, KeyError) as exc:
            self.page_library.message.setText(str(exc))

    def _save_template(self, name):
        try:
            self._workspace_library().save_template(
                name, self.page_simulation.config_panel.get_config()
            )
            self._refresh_library()
            self.page_library.message.setText("Modelo salvo.")
        except (OSError, ValueError) as exc:
            self.page_library.message.setText(str(exc))

    def _load_template(self, name):
        try:
            config = self._workspace_library().template(name)
            if not self._can_replace(config):
                return
            self._pending_example_id = None
            self._apply_draft(config, name)
            self._show_page("simulation")
        except (OSError, ValueError, KeyError) as exc:
            self.page_library.message.setText(str(exc))

    def _delete_template(self, name):
        if not name:
            return
        try:
            self._workspace_library().delete_template(name)
            self._refresh_library()
        except (OSError, ValueError) as exc:
            self.page_library.message.setText(str(exc))

    def _annotate_current(self, project, notes, tags):
        if self._current_experiment is None:
            self.page_library.message.setText(
                "Abra uma execução para salvar suas anotações."
            )
            return
        try:
            self._workspace_library().annotate(
                self._current_experiment.id, project, notes, tags,
                title=self.page_library.run_title.text(),
            )
            self._refresh_library()
            self.page_library.message.setText(
                "Projeto e anotações salvos; dados científicos preservados."
            )
        except (OSError, ValueError) as exc:
            self.page_library.message.setText(str(exc))

    def _restore_preferences(self):
        page = self.page_settings
        widgets = [
            page.theme,
            page.font_size,
            page.presentation,
            page.compact,
            self.page_bloch.speed_combo,
            self.page_bloch.loop,
            self.page_bloch.trails,
        ]
        blockers = [QSignalBlocker(w) for w in widgets]
        theme = self.settings.value("appearance/theme", "dark")
        page.theme.setCurrentIndex(max(0, page.theme.findData(theme)))
        try:
            font_size=int(self.settings.value("appearance/font",15))
            if not self.settings.value('appearance/readability_v1',False,type=bool):
                if font_size==13:
                    font_size=15
                self.settings.setValue('appearance/readability_v1',True)
            page.font_size.setValue(font_size)
        except (ValueError, TypeError):
            page.font_size.setValue(15)
        page.presentation.setChecked(
            self.settings.value("appearance/presentation", False, type=bool)
        )
        page.compact.setChecked(
            self.settings.value("appearance/compact", False, type=bool)
        )
        speed = self.settings.value("bloch/speed", "1x")
        self.page_bloch.speed_combo.setCurrentText(
            speed if speed in ("0.5x", "1x", "2x", "4x") else "1x"
        )
        self.page_bloch.loop.setChecked(
            self.settings.value("bloch/loop", False, type=bool)
        )
        self.page_bloch.trails.setChecked(
            self.settings.value("bloch/trails", True, type=bool)
        )
        blocker = QSignalBlocker(self.page_bloch)
        del blockers
        self.page_bloch._update_speed(self.page_bloch.speed_combo.currentText())
        del blocker
        self._apply_preferences()

    def _persist_bloch_preferences(self):
        if not hasattr(self, "page_bloch"):
            return
        page = self.page_bloch
        self.settings.setValue("bloch/speed", page.speed_combo.currentText())
        self.settings.setValue("bloch/loop", page.loop.isChecked())
        self.settings.setValue("bloch/trails", page.trails.isChecked())
        if page.precomputed_bloch:
            self.settings.setValue("bloch/focus", page.focus_combo.currentData())

    def _restore_camera_preferences(self):
        canvas = self.page_bloch.canvas
        if not canvas._sphere_centers:
            return
        try:
            focus = int(self.settings.value("bloch/focus", -1))
            canvas.set_focus(focus)
            canvas.restore_camera(
                zoom=float(self.settings.value("bloch/zoom", 1.0)),
                elev=float(self.settings.value("bloch/elev", 22.0)),
                azim=float(self.settings.value("bloch/azim", -60.0)),
                pan=json.loads(self.settings.value("bloch/pan", "[0,0,0]")),
                projection=self.settings.value("bloch/projection", "persp"),
            )
        except (ValueError, TypeError, OverflowError):
            canvas.reset_camera()
        self.page_bloch._refresh_ui()

    def _persist_camera(self):
        canvas = self.page_bloch.canvas
        if not canvas._sphere_centers:
            return
        for key, value in canvas.camera_state().items():
            self.settings.setValue(
                "bloch/" + key, json.dumps(value) if key == "pan" else value
            )

    def _apply_preferences(self):
        if not hasattr(self, "page_settings"):
            return
        p = self.page_settings
        self.settings.setValue("appearance/theme", p.theme.currentData())
        self.settings.setValue("appearance/font", p.font_size.value())
        self.settings.setValue("appearance/presentation", p.presentation.isChecked())
        self.settings.setValue("appearance/compact", p.compact.isChecked())
        apply_appearance(
            self,
            p.theme.currentData(),
            max(17, p.font_size.value())
            if p.presentation.isChecked()
            else p.font_size.value(),
        )
        self._adaptive_sidebar()

    def _reset_preferences(self):
        for prefix in ("appearance", "bloch"):
            self.settings.remove(prefix)
        self._restore_preferences()
        self.page_bloch.focus_combo.setCurrentIndex(0)
        self.page_bloch.canvas.reset_camera()

    def _toggle_presentation(self):
        self.page_settings.presentation.setChecked(
            not self.page_settings.presentation.isChecked()
        )
        if self.page_settings.presentation.isChecked():
            self.help_dock.hide()
            self.tutorial_dock.hide()
            self.showFullScreen()
        else:
            self.showNormal()

    def _adaptive_sidebar(self):
        if not hasattr(self, "page_settings"):
            return
        self.sidebar.set_compact(
            (self.width() < 1150 and not getattr(self,'_sidebar_explicitly_expanded',False))
            or self.page_settings.compact.isChecked()
            or self.page_settings.presentation.isChecked()
        )

    def _toggle_sidebar(self,compact):
        self._sidebar_explicitly_expanded=not compact
        self.page_settings.compact.setChecked(compact)
        self._adaptive_sidebar()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._adaptive_sidebar()

    def _refresh_saved_analyses(self):
        paths = []
        if self.repository is not None and self._current_experiment is not None:
            folder = (
                self.repository.base_dir / ".analyses" / self._current_experiment.id
            )
            for path in sorted(
                folder.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True
            ):
                try:
                    data = json.loads(path.read_text(encoding="utf-8"))
                    label = {
                        "temporal": "Métricas temporais",
                        "convergence": "Convergência Trotter",
                        "sweep": "Varredura",
                        "trotter_noise": "Trotter × ruído",
                        "mitigation_benchmark": "Benchmark de mitigação",
                        "heatmap":"Mapa de calor",
                        "zne_stability":"Estabilidade ZNE",
                        "equal_budget":"Orçamento equivalente",
                    }.get(data["kind"], "Análise")
                    paths.append((label + " · " + path.stem, path))
                except (OSError, ValueError, KeyError, TypeError):
                    pass
        self.page_analysis.set_saved(paths)

    def _show_circuit_snapshot(self, index):
        self.page_bloch.slider.setValue(index)
        self._show_page("bloch")

    def _run_editor_circuit(self, config):
        if self._current_worker is not None or not self._confirm_unsaved():
            return
        try:
            config.validate()
        except ValueError as exc:
            self.page_circuit.editor.message.setText(str(exc))
            return
        if self.tutorial.active:
            self.tutorial.pause()
        self._pending_example_id = None
        self._start_worker(SimulationWorker(config, self), self._on_experiment)

    def _protocol_repository(self):
        if self.repository is None:
            raise ValueError("Armazenamento indisponível para protocolos.")
        return ProtocolRepository(self.repository.base_dir/".protocols")

    def _refresh_protocols(self):
        records=self._protocol_repository().list_all() if self.repository is not None else []
        self.page_analysis.protocol.set_saved(records)

    def _save_protocol(self):
        if self._current_experiment is None or self._current_worker is not None:
            return
        try:
            kind,options=self.page_analysis.analysis_options()
            data=self._protocol_repository().save(self._current_experiment,kind,options,self.page_analysis.protocol.context()["fields"])
            self.page_analysis.protocol.set_protocol(data)
            self._refresh_protocols()
            self.page_analysis.message.setText("Nova revisão de protocolo salva: "+data["protocol_id"])
        except (OSError,ValueError,TypeError) as exc:
            self.page_analysis.message.setText(str(exc))

    def _load_protocol(self,identifier):
        if not identifier or self._current_worker is not None:
            return
        try:
            data=self._protocol_repository().load(identifier)
            if self._current_experiment is None or self._current_experiment.id!=data["source_id"]:
                self._open_experiment(data["source_id"])
            source=self._current_experiment
            if source is None or source.id!=data["source_id"]:
                return
            actual=asdict(source.config)
            actual["seed"]=source.result.metadata.get("effective_seed",actual["seed"])
            if actual!=data["config"]:
                raise ValueError("A configuração da fonte mudou; protocolo preservado. Crie uma nova revisão.")
            self.page_analysis.apply_options(data["kind"],data["options"])
            self.page_analysis.protocol.set_protocol(data)
            self.page_analysis.message.setText("Protocolo carregado. Calcular análise cria outra evidência sem modificar o plano salvo.")
            self._show_page("analysis")
        except (OSError,ValueError,KeyError,TypeError) as exc:
            self.page_analysis.message.setText("Não foi possível carregar o protocolo: "+str(exc))

    def _prepare_comparison(self,a,b):
        if self._current_worker is not None or self.repository is None:
            return
        try:
            from core.comparison import incompatibility
            records=self.page_comparison.records
            error=incompatibility(records[a],records[b])
            if error:
                raise ValueError(error)
            self._start_worker(ComparisonWorker(self.repository,(a,b),records[a].config,self),self._on_comparison)
            self.page_comparison.message.setText("Carregando estados e calculando curvas em segundo plano…")
        except (KeyError,ValueError) as exc:
            self.page_comparison.message.setText(str(exc))

    def _on_comparison(self,data):
        if self._current_worker and self._current_worker.isInterruptionRequested():
            return
        self.page_comparison.set_full_data(data)
        self.page_comparison.message.setText("A e B carregadas. Curvas usam seus snapshots reais; câmeras podem ser sincronizadas. ZNE preserva o estado da fonte.")
        self.page_simulation.status.set_success("Comparação preparada; execuções de origem preservadas")

    def _documentation_sources(self):
        if self.page_documentation.use_comparison.isChecked():
            data=self.page_comparison.full_data
            if data is None:
                return []
            return data["experiments"]
        return [self._current_experiment] if self._current_experiment is not None else []

    def _document_comparison(self):
        self.page_documentation.use_comparison.setChecked(True)
        self._show_page("documentation")

    def _refresh_documentation(self):
        sources=self._documentation_sources()
        analyses=[]
        protocols=[]
        try:
            if self.repository is not None:
                from data.analyses import load_analysis
                for source in sources:
                    for path in sorted((self.repository.base_dir/".analyses"/source.id).glob("*.json")):
                        analyses.append((load_analysis(path,source.id),path))
                ids={e.id for e in sources}
                protocols=[p for p in self._protocol_repository().list_all() if p["source_id"] in ids]
            self.page_documentation.set_lineage(sources,analyses,protocols)
        except (OSError,ValueError,TypeError,KeyError) as exc:
            self.page_documentation.message.setText("Não foi possível ler todas as evidências: "+str(exc))

    def _open_evidence(self,source_id,path):
        if self._current_worker is not None:
            return
        try:
            from data.analyses import load_analysis
            data=load_analysis(path,source_id)
            if self._current_experiment is None or self._current_experiment.id!=source_id:
                self._open_experiment(source_id)
            if self._current_experiment is not None and self._current_experiment.id==source_id:
                self.page_analysis.show_analysis(data)
                self._show_page("analysis")
        except (OSError,ValueError,TypeError,KeyError) as exc:
            self.page_documentation.message.setText(str(exc))

    def _export_documentation(self,kind):
        if self._current_worker is not None:
            return
        sources=self._documentation_sources()
        if not sources:
            self.page_documentation.message.setText("Abra uma execução ou carregue os estados de uma comparação antes de exportar.")
            return
        extension={"zip":"ZIP (*.zip)","pdf":"PDF (*.pdf)","gif":"GIF (*.gif)"}[kind]
        path,_=QFileDialog.getSaveFileName(self,"Exportar documentação","entrela-documentacao",extension)
        if not path:
            return
        if not Path(path).suffix:
            path+="."+kind
        self._start_documentation_export(sources,path,kind)

    def _start_documentation_export(self,sources,path,kind):
        try:
            annotations={}
            protocols=[]
            if self.repository is not None:
                try:
                    annotations=self._workspace_library().read()["annotations"]
                    ids={e.id for e in sources}
                    protocols=[p for p in self._protocol_repository().list_all() if p["source_id"] in ids]
                except (OSError,ValueError,KeyError):
                    pass
            page=self.page_documentation
            worker=DocumentationWorker(sources,path,kind,self.repository,annotations,protocols,
                page.include_analyses.isChecked(),page.include_gif.isChecked(),page.max_frames.value(),page.frame_ms.value(),self,
                live_analyses=(deepcopy(self.page_analysis.data),) if self.page_analysis.data else ())
            self._start_worker(worker,self._on_documented)
            page.message.setText("Preparando documentação em segundo plano; arquivos de origem preservados.")
            self.statusBar().showMessage("Preparando documentação em segundo plano…")
        except (OSError,ValueError,TypeError) as exc:
            self.page_documentation.message.setText(str(exc))

    def _on_documented(self,path):
        self.page_documentation.message.setText("Documentação exportada: "+path)
        self.page_simulation.status.set_success("Exportação concluída")
        self.statusBar().showMessage("Documentação exportada: "+path)

    def _export_bloch_view(self):
        if self._current_experiment is None or not self.page_bloch.original_svs:
            self.statusBar().showMessage("A vista atual requer snapshots; ative-os e execute uma simulação.")
            return
        path,filter=QFileDialog.getSaveFileName(self,"Exportar vista atual de Bloch","bloch", "PNG (*.png);;SVG (*.svg);;PDF (*.pdf)")
        if not path:
            return
        if not Path(path).suffix:
            path+=".svg" if "SVG" in filter else ".pdf" if "PDF" in filter else ".png"
        try:
            export_figure(self.page_bloch.canvas.fig,path,dpi=180)
            from core.export import _atomic_text
            _atomic_text(Path(path).with_suffix(".metadata.json"),json.dumps(dict(source_id=self._current_experiment.id,
                snapshot=self.page_bloch.slider.value(),camera=self.page_bloch.canvas.camera_state(),
                focus=self.page_bloch.canvas.focus,ideal_visible=self.page_bloch.overlay.isChecked(),
                trails_visible=self.page_bloch.trails.isChecked(),config=asdict(self._current_experiment.config),
                effective_seed=self._current_experiment.result.metadata.get("effective_seed"),
                versions=self._current_experiment.result.metadata.get("versions"),
                note="Vista atual, câmera e snapshot reais; preserve o JSON do experimento."),ensure_ascii=False,indent=2))
            self.statusBar().showMessage("Vista de Bloch e metadados exportados")
        except (OSError,ValueError) as exc:
            self.statusBar().showMessage(str(exc))
