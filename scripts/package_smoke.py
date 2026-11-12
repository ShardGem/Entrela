"""Import and open an extracted wheel outside the repository, in isolated Python."""

import os
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
from zipfile import ZipFile

CHECK = r"""
import sys
from pathlib import Path
sys.path.insert(0,sys.argv[1])
import gui,core
assert Path(gui.__file__).is_relative_to(sys.argv[1])
assert Path(core.__file__).is_relative_to(sys.argv[1])
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QSettings
from PySide6.QtGui import QPixmap
from gui.splash import SplashScreen
from gui.branding import application_icon, configure_application_identity
from gui.main_window import MainWindow
from data.repository import ExperimentRepository
from core.examples import create_example_config
from core.simulation import run_experiment
from dataclasses import replace
app=QApplication([])
configure_application_identity(app)
assert not application_icon().pixmap(16,16).isNull()
assert not application_icon().pixmap(256,256).isNull()
assert (Path(gui.__file__).parent/'assets/icons/entrela.ico').is_file()
splash=SplashScreen()
assert not splash.logo.pixmap.isNull()
assert not splash.text.pixmap().isNull()
window=MainWindow(ExperimentRepository('data'),QSettings('prefs.ini',QSettings.IniFormat))
window.show();app.processEvents()
for theme in ('dark','light','navy'):
    choice=window.page_settings.theme.findData(theme)
    assert choice>=0
    window.page_settings.theme.setCurrentIndex(choice)
    app.processEvents()
    assert window.property('entrelaTheme')==theme
for key in window.page_workspace.KEYS:
    window._show_page(key)
    assert window.stack.currentWidget() is window.page_workspace
    assert window.page_workspace.tabs.currentWidget() is window.pages[key]
    assert window.is_page_active(key)
exp=run_experiment(replace(create_example_config('bell'),shots=64))
window.repository.save(exp)
assert window.repository.load(exp.id).result.counts==exp.result.counts
assert exp.result.metadata['entrela_version']==core.__version__
window._current_experiment=exp
window._display_experiment(exp)
window._show_page('results')
window.page_results.tabs.setCurrentWidget(window.page_results.state_inspector)
app.processEvents()
assert abs(window.page_results.state_inspector.quantities['purity']-1)<1e-10
window.page_history.load([exp])
window.page_history.set_detail(exp,files=[])
window.page_history.circuit.select_operation(0)
assert not window.page_history.circuit.canvas.editable
assert 'Hadamard' in window.page_history.circuit.details.text()
from core.circuit_document import CircuitDocument,CircuitGate
from core.types import ExperimentConfig,SystemConfig,SimulationProtocol,NoiseConfig
custom=run_experiment(ExperimentConfig(SystemConfig(2,J=0,h=0),SimulationProtocol(2,2,True),NoiseConfig(False),64,42,CircuitDocument(2,(CircuitGate('h',(0,)),CircuitGate('cx',(0,1))),.3)))
window.repository.save(custom)
assert window.repository.load(custom.id).config.circuit==custom.config.circuit
window.page_circuit.show_experiment(custom)
window.page_circuit._copy_to_editor()
assert window.page_circuit.editor.document==custom.config.circuit
window.page_circuit.editor.circuit_name.setText('Recovered packaged circuit')
window.close();app.processEvents()
from data.workspace_backup import create_workspace_backup,prepare_workspace_restore
create_workspace_backup('data','backup.zip',{'appearance/theme':'dark'})
prepared=prepare_workspace_restore('backup.zip','restored-data')
assert prepared.preview.experiments==2
assert prepared.commit()=={'appearance/theme':'dark'}
assert ExperimentRepository('restored-data').load(exp.id).result.counts==exp.result.counts
reopened=MainWindow(window.repository,window.settings)
assert reopened.page_settings.theme.currentData()=='navy'
assert reopened.page_circuit.editor.document==custom.config.circuit
assert reopened.page_circuit.editor.circuit_name.text()=='Recovered packaged circuit'
reopened.close();splash.close();app.processEvents()
print('PASS: isolated wheel, assets, Qt workspace, scientific engine, graphical history, state inspector, backup and persistence')
"""


def main():
    wheel = Path(sys.argv[1]).resolve()
    with TemporaryDirectory(prefix="entrela-wheel-") as temp:
        target = Path(temp) / "installed"
        with ZipFile(wheel) as archive:
            archive.extractall(target)
            entry = next(
                name for name in archive.namelist() if name.endswith("entry_points.txt")
            )
            assert "entrela = gui.application:main" in archive.read(entry).decode()
        env = {**os.environ, "QT_QPA_PLATFORM": "offscreen"}
        subprocess.run(
            [sys.executable, "-I", "-c", CHECK, str(target)],
            cwd=temp,
            env=env,
            check=True,
        )


if __name__ == "__main__":
    main()
