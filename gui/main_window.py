"""Application controller: real executions, learning flows and durable records."""
from dataclasses import asdict,replace
from datetime import datetime,timezone
from pathlib import Path
from uuid import uuid4
import json
from PySide6.QtCore import QSettings,Qt,QTimer
from PySide6.QtGui import QShortcut,QKeySequence
from PySide6.QtWidgets import (QMainWindow,QWidget,QHBoxLayout,QVBoxLayout,QStackedWidget,QStatusBar,
    QDockWidget,QTextBrowser,QFileDialog,QMessageBox)
from gui.theme import build_qss
from gui.manual import WELCOME_HTML
from gui.widgets.sidebar import Sidebar
from gui.widgets.topbar import Topbar
from gui.widgets.tutorial import BellTutorial,STEPS
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
from gui.workers.simulation_worker import SimulationWorker
from gui.workers.mitigation_worker import MitigationWorker
from core.types import (Experiment,ExperimentResult,ExperimentConfig,SystemConfig,SimulationProtocol,
                        NoiseConfig,config_from_dict)
from core.examples import EXAMPLES,get_example,create_example_config
from core.export import (export_counts_csv,export_experiment_json,import_experiment_json,
                         export_run_bundle,export_figure)
from data.repository import ExperimentRepository

PAGE_META={
    "dashboard":("Início","Seu laboratório quântico"),"examples":("Exemplos","Aprenda a partir de experimentos reais"),
    "simulation":("Experimento","Configure e execute"),"circuit":("Circuito","Preparação, evolução e medição"),
    "results":("Resultados","Dados da execução selecionada"),"bloch":("Evolução 3D","Estados efetivamente simulados"),
    "mitigation":("Mitigação","Extrapolação de observáveis"),"comparison":("Comparações","Experimentos compatíveis"),
    "history":("Histórico","Resultados preservados"),"docs":("Aprender","Conceitos e ajuda"),
    "settings":("Configurações","Preferências")}
class MainWindow(QMainWindow):
    def __init__(self,repository=None,settings=None):
        super().__init__()
        self.setWindowTitle("Entrela · Laboratório quântico")
        self.resize(1440,900)
        self.setMinimumSize(1020,720)
        self.settings=settings if settings is not None else QSettings("Entrela","TCC")
        self.repository=repository
        self._storage_error=""
        if self.repository is None:
            try:self.repository=ExperimentRepository()
            except OSError as exc:self._storage_error=str(exc)
        self._current_worker=None
        self._current_experiment=None
        self._running_config=None
        self._unsaved_result=False
        self._close_pending=False
        self._loading_draft=True
        self._draft_dirty=False
        self._draft_baseline=None
        self._pending_example_id=None
        self._current_page="dashboard"
        self._history=[]
        self.setStyleSheet(build_qss())
        self._build_ui()
        self._build_help()
        self._build_tutorial()
        self._wire_signals()
        self._build_commands()
        try:shots=int(self.settings.value("shots",8192))
        except (ValueError,TypeError):shots=8192
        self.page_settings.spin_shots.setValue(shots)
        self.page_simulation.config_panel.spin_shots.setValue(shots)
        self._restore_workspace()
        self._refresh_history()
        self._show_page("dashboard")
        if self._storage_error:self.statusBar().showMessage("Armazenamento indisponível: "+self._storage_error)

    def _build_ui(self):
        root=QWidget()
        root.setObjectName("RootWidget")
        self.setCentralWidget(root)
        layout=QHBoxLayout(root)
        layout.setContentsMargins(0,0,0,0)
        layout.setSpacing(0)
        self.sidebar=Sidebar()
        layout.addWidget(self.sidebar)
        right=QWidget()
        body=QVBoxLayout(right)
        body.setContentsMargins(0,0,0,0)
        body.setSpacing(0)
        self.topbar=Topbar()
        body.addWidget(self.topbar)
        self.stack=QStackedWidget()
        body.addWidget(self.stack,1)
        layout.addWidget(right,1)
        self.page_dashboard=DashboardPage()
        self.page_examples=ExamplesPage()
        self.page_simulation=SimulationPage()
        self.page_circuit=CircuitPage()
        self.page_results=ResultsPage()
        self.page_bloch=BlochPage()
        self.page_mitigation=MitigationPage()
        self.page_comparison=ComparisonPage()
        self.page_history=HistoryPage()
        self.page_docs=DocsPage(WELCOME_HTML)
        self.page_settings=SettingsPage()
        self.pages=dict(dashboard=self.page_dashboard,examples=self.page_examples,simulation=self.page_simulation,
            circuit=self.page_circuit,results=self.page_results,bloch=self.page_bloch,mitigation=self.page_mitigation,
            comparison=self.page_comparison,history=self.page_history,docs=self.page_docs,settings=self.page_settings)
        for page in self.pages.values():self.stack.addWidget(page)
        self.setStatusBar(QStatusBar())

    def _build_help(self):
        self.help_dock=QDockWidget("Ajuda contextual",self)
        self.help_dock.setObjectName("ScientificHelp")
        self.help_browser=QTextBrowser()
        self.help_browser.setHtml(WELCOME_HTML)
        self.help_dock.setWidget(self.help_browser)
        self.addDockWidget(Qt.RightDockWidgetArea,self.help_dock)
        self.help_dock.hide()

    def _build_tutorial(self):
        self.tutorial=BellTutorial()
        self.tutorial_dock=QDockWidget("Aprender fazendo · Bell",self)
        self.tutorial_dock.setObjectName("BellTutorial")
        self.tutorial_dock.setWidget(self.tutorial)
        self.addDockWidget(Qt.RightDockWidgetArea,self.tutorial_dock)
        self.tutorial_dock.hide()
        self.tutorial.section_requested.connect(self._tutorial_section)
        self.tutorial.progress_changed.connect(self._persist_tutorial)
        self.tutorial.paused.connect(self.tutorial_dock.hide)
        self.tutorial.completed.connect(self._tutorial_completed)
        self.tutorial_dock.visibilityChanged.connect(self._tutorial_visibility)

    def _wire_signals(self):
        self.sidebar.navigate.connect(self._show_page)
        self.topbar.help_requested.connect(lambda:self._show_help("Início"))
        self.topbar.commands_requested.connect(self._open_commands)
        p=self.page_simulation
        p.run_requested.connect(self._run_simulation)
        p.cancel_requested.connect(self._cancel_simulation)
        p.config_panel.ajuda_acionada.connect(self._show_help)
        p.config_panel.parametros_alterados.connect(self._draft_changed)
        p.config_panel.mode_changed.connect(lambda mode:self.settings.setValue("workspace/mode",mode))
        self.page_dashboard.new_simulation.connect(self._new_experiment)
        self.page_dashboard.open_history.connect(lambda:self._show_page("history"))
        self.page_dashboard.examples_requested.connect(lambda:self._show_page("examples"))
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

    def _build_commands(self):
        self.command_palette=CommandPalette(self)
        self.command_palette.command_requested.connect(self._command)
        self.shortcuts=[]
        for key,callback in [("Ctrl+K",self._open_commands),("Ctrl+N",self._new_experiment),
                             ("Ctrl+O",self._import_experiment),("Ctrl+Return",self._run_simulation),
                             ("F1",lambda:self._show_help("Início"))]:
            shortcut=QShortcut(QKeySequence(key),self)
            shortcut.activated.connect(callback)
            self.shortcuts.append(shortcut)

    def _open_commands(self):
        commands=[("new","Criar experimento","novo"),("import","Importar experimento JSON","abrir arquivo"),
                  ("tutorial","Aprender: tutorial de Bell","primeiro experimento"),
                  ("mode:guided","Usar modo Guiado","ajuda etapas"),("mode:advanced","Usar modo Avançado","parâmetros")]
        commands += [("page:"+key,"Abrir "+title,"navegar") for key,(title,_) in PAGE_META.items()]
        commands += [("example:"+e.id,"Exemplo: "+e.title,e.description) for e in EXAMPLES]
        commands += [("run:"+e.id,"Abrir execução "+e.id,e.config.system.hamiltonian) for e in self._history[:20]]
        commands += [("help:"+word,"Conceito: "+word,word) for word in
                     ("Fidelidade","Pureza","Hamiltoniano","T₁","T₂","Shots","Semente","Mitigação","Evolução")]
        self.command_palette.open_commands(commands)

    def _command(self,identifier):
        if identifier=="new":self._new_experiment()
        elif identifier=="import":self._import_experiment()
        elif identifier=="tutorial":self._begin_tutorial()
        elif identifier.startswith("page:"):self._show_page(identifier[5:])
        elif identifier.startswith("example:"):self._load_example(identifier[8:])
        elif identifier.startswith("run:"):self._open_experiment(identifier[4:])
        elif identifier.startswith("help:"):self._show_help(identifier[5:])
        elif identifier.startswith("mode:"):self.page_simulation.config_panel.set_mode(identifier[5:])

    def _show_help(self,topic):
        self.help_dock.show()
        self.help_browser.scrollToAnchor(topic)
        self.help_browser.find(topic)

    def _show_page(self,key):
        if key not in self.pages:return
        self._current_page=key
        self.stack.setCurrentWidget(self.pages[key])
        self.sidebar.set_active(key)
        self.topbar.set_context(*PAGE_META[key])
        self._update_tutorial()

    def _restore_workspace(self):
        panel=self.page_simulation.config_panel
        try:
            raw=self.settings.value("workspace/draft","")
            if raw:panel.load_config(config_from_dict(json.loads(raw)))
        except (ValueError,TypeError):
            self.statusBar().showMessage("Rascunho anterior inválido; configuração padrão carregada.")
        mode=self.settings.value("workspace/mode","guided")
        panel.set_mode(mode if mode in ("guided","advanced") else "guided")
        self._draft_baseline=panel.get_config()
        self._loading_draft=False

    def _apply_draft(self,config,title="Rascunho"):
        self._loading_draft=True
        try:self.page_simulation.config_panel.load_config(config)
        finally:self._loading_draft=False
        self._draft_baseline=config
        self._draft_dirty=False
        self.page_simulation.set_title(title,"Cópia editável · resultados anteriores permanecem preservados.")
        self.settings.setValue("workspace/draft",json.dumps(asdict(config)))

    def _draft_changed(self):
        if not self._loading_draft:
            try:
                config=self.page_simulation.config_panel.get_config()
                self._draft_dirty=config!=self._draft_baseline
                self.settings.setValue("workspace/draft",json.dumps(asdict(config)))
            except ValueError:self._draft_dirty=True
        self._update_tutorial()

    def _can_replace(self,config=None):
        if self._current_worker is not None:
            self.statusBar().showMessage("Aguarde ou cancele a execução atual.")
            return False
        if not self._confirm_unsaved():return False
        current=None
        try:current=self.page_simulation.config_panel.get_config()
        except ValueError:pass
        if self._draft_dirty and current!=config:
            return QMessageBox.question(self,"Substituir configuração?",
                "O rascunho foi editado. Deseja substituí-lo? Os resultados salvos serão preservados.",
                QMessageBox.Yes|QMessageBox.No,QMessageBox.No)==QMessageBox.Yes
        return True

    def _new_experiment(self):
        cfg=ExperimentConfig(SystemConfig(),SimulationProtocol(),NoiseConfig(enabled=False),
                             self.page_settings.spin_shots.value(),42)
        if not self._can_replace(cfg):return
        if self.tutorial.active:self.tutorial.pause()
        self._pending_example_id=None
        self._apply_draft(cfg,"Novo experimento")
        self.page_simulation.config_panel.set_section("system")
        self._show_page("simulation")

    def _load_example(self,identifier):
        example=get_example(identifier)
        cfg=example.create_config()
        if not self._can_replace(cfg):return
        if self.tutorial.active:self.tutorial.pause()
        self._pending_example_id=identifier
        self._apply_draft(cfg,example.title+" · cópia")
        self.page_simulation.config_panel.set_section("system")
        self._show_page("simulation")

    def _set_default_shots(self,value):
        self.settings.setValue("shots",value)
        if self._current_worker is None:self.page_simulation.config_panel.spin_shots.setValue(value)

    def _begin_tutorial(self):
        try:step=int(self.settings.value("tutorial/bell/step",0))
        except (ValueError,TypeError):step=0
        completed=self.settings.value("tutorial/bell/completed",False,type=bool)
        if completed:step=0
        step=max(0,min(step,6))
        experiment=None
        identifier=self.settings.value("tutorial/bell/run_id","")
        if self.repository is not None and identifier and not completed:
            try:
                candidate=self.repository.load(identifier)
                if BellTutorial.matches(candidate.config) and not candidate.result.error:experiment=candidate
            except (OSError,ValueError,KeyError,TypeError):pass
        if step>=5 and experiment is None:step=4
        cfg=experiment.config if step>=4 and experiment else ExperimentConfig(
            SystemConfig(2 if step>=1 else 1,J=0,h=0,initial_state="bell" if step>=2 else "zero"),
            SimulationProtocol(save_snapshots=step>=4),NoiseConfig(enabled=step<3),shots=4096,seed=42)
        if not self._can_replace(cfg):return
        self._pending_example_id="bell"
        self._apply_draft(cfg,"Tutorial · Seu primeiro Bell")
        self.page_simulation.config_panel.set_mode("guided")
        self.help_dock.hide()
        self.tutorial_dock.show()
        self.settings.setValue("tutorial/bell/completed",False)
        self.tutorial.start(step,experiment)
        self._show_page("simulation")
        self._persist_tutorial()

    def _tutorial_section(self,key):
        self.page_simulation.config_panel.set_section(key)
        if self.tutorial.step<5:self._show_page("simulation")

    def _update_tutorial(self):
        if not hasattr(self,"tutorial"):return
        try:config=self.page_simulation.config_panel.get_config()
        except ValueError:config=None
        self.tutorial.update_context(config,self._current_page)

    def _persist_tutorial(self):
        if not self.tutorial.started:return
        self.settings.setValue("tutorial/bell/step",self.tutorial.step)
        self.settings.setValue("tutorial/bell/run_id",self.tutorial.run_id or "")

    def _tutorial_completed(self):
        self.settings.setValue("tutorial/bell/completed",True)
        self.statusBar().showMessage("Tutorial concluído: configuração, execução, análise e reabertura verificadas.")

    def _tutorial_visibility(self,visible):
        if not visible and self.tutorial.active:self.tutorial.pause()

    def _run_simulation(self,*_):
        if self._current_worker is not None or not self._confirm_unsaved():return
        try:config=self.page_simulation.config_panel.get_config()
        except ValueError as exc:
            self.page_simulation.status.set_error(str(exc))
            return
        self._start_worker(SimulationWorker(config,self),self._on_experiment)

    def _start_worker(self,worker,callback):
        self._current_worker=worker
        self._running_config=worker.config
        worker.completed.connect(callback)
        worker.error.connect(self._on_error)
        worker.cancelled.connect(self._on_cancelled)
        worker.progress.connect(self.page_simulation.status._progress.setValue)
        worker.finished.connect(self._on_thread_finished)
        self.page_simulation.set_running(True)
        self.page_mitigation.set_running(True)
        worker.start()

    def _run_mitigation(self,qubit,method,shots):
        if self._current_worker is not None or self._current_experiment is None:return
        if self._current_experiment.result.error or not self._confirm_unsaved():return
        self._zne_source=self._current_experiment
        seed=self._zne_source.result.metadata.get("effective_seed",self._zne_source.config.seed)
        worker=MitigationWorker(replace(self._zne_source.config,seed=seed),qubit,method,shots,self)
        self._start_worker(worker,self._on_mitigation)

    def _on_experiment(self,experiment):
        if self._current_worker and self._current_worker.isInterruptionRequested():
            self._on_cancelled()
            return
        if self._pending_example_id:experiment.result.metadata["example_id"]=self._pending_example_id
        self._current_experiment=experiment
        self._unsaved_result=True
        self._draft_baseline=experiment.config
        self._draft_dirty=False
        self.tutorial.record_run(experiment)
        self._display_experiment(experiment)
        if self._save_current():self.page_simulation.status.set_success("Execução concluída e salva no histórico")
        self._show_page("bloch" if experiment.config.protocol.save_snapshots else "results")

    def _on_mitigation(self,analysis):
        if self._current_worker and self._current_worker.isInterruptionRequested():
            self._on_cancelled()
            return
        source=self._zne_source
        analysis={**analysis,"source_experiment_id":source.id}
        self._current_experiment=Experiment(source.config,replace(source.result,mitigation=analysis),
            duration_s=analysis["duration_s"],tags=list(dict.fromkeys(source.tags+["ZNE"])))
        self._unsaved_result=True
        self._display_experiment(self._current_experiment)
        if self._save_current():self.page_simulation.status.set_success("Análise ZNE concluída e salva")
        self._show_page("mitigation")

    def _display_experiment(self,experiment):
        self.page_results.show_experiment(experiment)
        self.page_bloch.load_statevectors(experiment.result.states,experiment.result.times)
        self.page_circuit.show_circuit(experiment.result.circuit_text)
        self.page_mitigation.load_experiment(experiment)
        if self._current_worker:self.page_mitigation.set_running(True)

    def _save_current(self):
        if self._current_experiment is None:return False
        try:
            if self.repository is None:self.repository=ExperimentRepository()
            self.repository.save(self._current_experiment)
        except (OSError,ValueError,TypeError) as exc:
            self.page_simulation.status.set_error("Resultado disponível, mas não foi salvo: "+str(exc))
            self.statusBar().showMessage("Use Salvar para tentar novamente.")
            return False
        self._unsaved_result=False
        self._refresh_history()
        self.statusBar().showMessage("Experimento "+self._current_experiment.id+" salvo.")
        return True

    def _confirm_unsaved(self):
        if not self._unsaved_result:return True
        choice=QMessageBox.warning(self,"Resultado não salvo","Há um resultado não salvo. O que deseja fazer?",
                                  QMessageBox.Save|QMessageBox.Discard|QMessageBox.Cancel,QMessageBox.Cancel)
        if choice==QMessageBox.Save:return self._save_current()
        if choice==QMessageBox.Discard:
            self._unsaved_result=False
            return True
        return False

    def _refresh_history(self):
        records=[]
        if self.repository is not None:
            try:
                records=self.repository.list_all()
                if self.repository.load_errors:self.statusBar().showMessage(
                    f"{len(self.repository.load_errors)} arquivo(s) ilegíveis foram preservados.")
            except OSError as exc:self.statusBar().showMessage(str(exc))
        self._history=records
        self.page_history.load(records)
        self.page_comparison.load(records)
        self.page_dashboard.load_recent(records[:5])
        latest=next((e for e in records if not e.result.error),None)
        self.page_dashboard.update_stats(len(records),latest.config.system.hamiltonian if latest else None,
            latest.result.fidelity if latest else None,latest.result.purity if latest else None)

    def _open_experiment(self,identifier):
        if self.repository is None:return
        try:
            experiment=self.repository.load(identifier)
            if not self._can_replace(experiment.config):return
            self._apply_draft(experiment.config,"Execução "+experiment.id)
            self._current_experiment=experiment
            self._unsaved_result=False
            self._display_experiment(experiment)
            self._pending_example_id=experiment.result.metadata.get("example_id")
        except (OSError,ValueError,TypeError,KeyError) as exc:
            self.statusBar().showMessage("Não foi possível abrir: "+str(exc))
            return
        self._show_page("results")
        self.tutorial.record_open(identifier)

    def _cancel_simulation(self):
        if self._current_worker:
            self._current_worker.requestInterruption()
            self.page_simulation.btn_cancel.setEnabled(False)
            self.statusBar().showMessage("Cancelando; aguardando a operação atual do simulador.")

    def _on_cancelled(self):
        self.page_simulation.status.set_idle("Execução cancelada; resultados anteriores preservados")

    def _on_error(self,message):
        self.page_simulation.status.set_error(message)
        self.page_mitigation.set_error(message)
        if self.repository is not None and self._running_config is not None:
            try:self.repository.save(Experiment(self._running_config,ExperimentResult(error=message)));self._refresh_history()
            except (OSError,ValueError,TypeError):self.statusBar().showMessage("Não foi possível salvar o diagnóstico.")

    def _on_thread_finished(self):
        worker=self._current_worker
        self._current_worker=None
        self._running_config=None
        self.page_simulation.set_running(False)
        self.page_mitigation.set_running(False)
        if worker:worker.deleteLater()
        if self._close_pending:QTimer.singleShot(0,self.close)

    def _import_experiment(self):
        path,_=QFileDialog.getOpenFileName(self,"Importar experimento","","JSON (*.json)")
        if not path:return
        try:
            source=import_experiment_json(path)
            if not self._can_replace(source.config):return
            if self.tutorial.active:self.tutorial.pause()
            result=replace(source.result,metadata={**source.result.metadata,"imported_from_id":source.id})
            self._current_experiment=replace(source,id=uuid4().hex[:12],created_at=datetime.now(timezone.utc),result=result)
            self._unsaved_result=True
            self._apply_draft(source.config,"Experimento importado")
            self._pending_example_id=None
            self._display_experiment(self._current_experiment)
            self._save_current()
            self._show_page("results")
        except (OSError,ValueError,TypeError,KeyError) as exc:self.statusBar().showMessage("Não foi possível importar: "+str(exc))

    def _export_counts(self):
        if self._current_experiment is None or not self._current_experiment.result.counts:return
        path,_=QFileDialog.getSaveFileName(self,"Exportar contagens","contagens.csv","CSV (*.csv)")
        if path:
            try:export_counts_csv(self._current_experiment.result.counts,path);self.statusBar().showMessage("CSV exportado")
            except OSError as exc:self.statusBar().showMessage(str(exc))

    def _export_experiment(self):
        if self._current_experiment is None:return
        path,kind=QFileDialog.getSaveFileName(self,"Exportar experimento","experimento.json","JSON (*.json);;Pacote ZIP (*.zip)")
        if path:
            try:
                if "ZIP" in kind and not Path(path).suffix:path+=".zip"
                if Path(path).suffix.lower()==".zip":export_run_bundle(self._current_experiment,path)
                else:export_experiment_json(self._current_experiment,path)
                self.statusBar().showMessage("Experimento completo exportado")
            except (OSError,ValueError) as exc:self.statusBar().showMessage(str(exc))

    def _export_figures(self):
        if self._current_experiment is None:return
        directory=QFileDialog.getExistingDirectory(self,"Exportar figuras PNG")
        if not directory:return
        prefix=Path(directory)/("entrela-"+self._current_experiment.id)
        figures=[(self.page_results.results_tab.canvas_hist.fig,str(prefix)+"-distribuicao.png"),
                 (self.page_results.results_tab.canvas_evol.fig,str(prefix)+"-evolucao.png")]
        if self._current_experiment.result.states:figures.append((self.page_bloch.canvas.fig,str(prefix)+"-bloch.png"))
        if any(Path(p).exists() for _,p in figures):
            if QMessageBox.question(self,"Substituir figuras?","Já existem figuras desta execução. Substituir?",
                                    QMessageBox.Yes|QMessageBox.No,QMessageBox.No)!=QMessageBox.Yes:return
        try:
            for figure,path in figures:export_figure(figure,path)
            self.statusBar().showMessage("Figuras exportadas")
        except OSError as exc:self.statusBar().showMessage(str(exc))

    def closeEvent(self,event):
        if self._current_worker is not None and self._current_worker.isRunning():
            self._close_pending=True
            self._cancel_simulation()
            event.ignore()
            return
        if not self._confirm_unsaved():event.ignore();return
        self._close_pending=False
        self._persist_tutorial()
        self.page_bloch.timer.stop()
        self.settings.sync()
        event.accept()
