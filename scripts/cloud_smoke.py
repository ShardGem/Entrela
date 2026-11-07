"""Exercise the real desktop workflow in a temporary repository."""
import os,sys,argparse
from pathlib import Path
from tempfile import TemporaryDirectory
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
os.environ.setdefault("QT_QPA_PLATFORM","offscreen")
os.environ.setdefault("MPLCONFIGDIR","/workspace/.cache/entrela/matplotlib")
os.environ.setdefault("XDG_CACHE_HOME","/workspace/.cache/entrela")
os.environ.setdefault("XDG_CONFIG_HOME","/workspace/.config/entrela")
for name in ("MPLCONFIGDIR","XDG_CACHE_HOME","XDG_CONFIG_HOME"):Path(os.environ[name]).mkdir(parents=True,exist_ok=True)
from PySide6.QtCore import QSettings,QEventLoop,QTimer
from PySide6.QtWidgets import QApplication
from gui.main_window import MainWindow
from data.repository import ExperimentRepository
from core.export import export_experiment_json,import_experiment_json
from tests.qt_helpers import execute,wait_until

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--screenshots",type=Path)
    args=parser.parse_args()
    app=QApplication([])
    def capture(window,name):
        if args.screenshots:
            args.screenshots.mkdir(parents=True,exist_ok=True)
            app.processEvents()
            assert window.grab().save(str(args.screenshots/(name+".png")))
    with TemporaryDirectory(prefix="entrela-smoke-") as directory:
        repo=ExperimentRepository(Path(directory)/"runs")
        settings=QSettings(str(Path(directory)/"prefs.ini"),QSettings.IniFormat)
        window=MainWindow(repo,settings)
        window.show()
        app.processEvents()
        capture(window,"inicio")
        for key,page in window.pages.items():
            window._show_page(key)
            assert window.is_page_active(key)
        print("PASS: navigation across",len(window.pages),"pages")
        window._show_page("examples")
        window.page_examples.select_example("bell")
        capture(window,"exemplos")
        p=window.page_simulation.config_panel
        window._show_page("simulation")
        p.set_mode("guided")
        capture(window,"guiado")
        p.set_mode("advanced")
        capture(window,"avancado")
        p.spin_shots.setValue(128)
        for noisy,snapshots in [(False,False),(True,False),(False,True),(True,True)]:
            p.check_ruido.setChecked(noisy)
            p.check_snaps.setChecked(snapshots)
            exp=execute(window)
            assert sum(exp.result.counts.values())==128
            assert len(exp.result.states)==(5 if snapshots else 0)
            assert all(state.is_valid() for state in exp.result.states)
            loaded=repo.load(exp.id)
            assert loaded.config==exp.config
            print("PASS: run and persisted states, noise=",noisy,"snapshots=",snapshots)
        for key in ("results","bloch"):
            window._show_page(key)
            capture(window,key)
        window.page_mitigation.shots.setValue(256)
        window.page_mitigation.btn_run.click()
        wait_until(lambda:window._current_worker is None)
        assert window._current_experiment.result.mitigation["scale_factors"]==[1,3,5]
        window._show_page("mitigation")
        capture(window,"mitigation")
        assert len(repo.list_all())==5
        print("PASS: ZNE analysis as independent record")
        window._begin_tutorial()
        t=window.tutorial
        p.spin_qubits.setValue(2)
        t.advance()
        p.combo_initial.setCurrentIndex(p.combo_initial.findData("bell"))
        t.advance()
        p.check_ruido.setChecked(False)
        t.advance()
        p.check_snaps.setChecked(True)
        t.advance()
        assert t.step==4
        exp=execute(window)
        t.advance()
        window._show_page("results")
        t.advance()
        window._show_page("history")
        window._open_experiment(exp.id)
        t.advance()
        assert settings.value("tutorial/bell/completed",False,type=bool)
        path=export_experiment_json(exp,Path(directory)/"export.json")
        assert import_experiment_json(path).config==exp.config
        identifier=exp.id
        window.close()
        reopened=MainWindow(repo,settings)
        reopened._open_experiment(identifier)
        assert reopened._current_experiment.id==identifier
        assert len(reopened._current_experiment.result.states)==5
        reopened.close()
        print("PASS: action-gated tutorial, JSON export/import and reopen after restart")
if __name__=="__main__":main()
