"""Captura os três temas reais em repositórios e preferências temporários.

Não lê dados do usuário nem altera a instalação. Exemplo:
python scripts/preview_interface.py --output work/interface --font-size 15
"""
from __future__ import annotations

import argparse
import gc
import os
from pathlib import Path
import sys
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

from PySide6.QtCore import QCoreApplication, QEvent, QSettings
from PySide6.QtWidgets import QApplication

from core.examples import create_example_config
from core.simulation import run_experiment
from data.repository import ExperimentRepository
from data.workspace import WorkspaceLibrary
from gui.main_window import MainWindow

PROFILES = {'grafite': 'dark', 'claro': 'light', 'azulado': 'navy'}
SCREENS = {'simulation': 'simulacao', 'results': 'resultados', 'bloch': 'bloch',
           'history': 'historico', 'settings': 'preferencias'}


def settle(app):
    for _ in range(8):
        app.processEvents()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT / 'work/interface')
    parser.add_argument('--font-size', type=int, choices=range(11, 25), default=15)
    parser.add_argument('--width', type=int, default=1440)
    parser.add_argument('--height', type=int, default=960)
    parser.add_argument('--all-pages', action='store_true', help='Inclui todas as ferramentas nos três temas.')
    args = parser.parse_args()
    if args.width < 800 or args.height < 600:
        parser.error('A captura requer pelo menos 800 × 600 pixels.')
    args.output.mkdir(parents=True, exist_ok=True)
    app = QApplication([])
    errors = []
    sys.excepthook = lambda *event: errors.append(str(event[1]))
    with TemporaryDirectory(prefix='entrela-interface-') as folder:
        experiment = run_experiment(create_example_config('bell'))
        for profile, theme in PROFILES.items():
            base = Path(folder) / profile
            repository = ExperimentRepository(base / 'runs')
            repository.save(experiment)
            WorkspaceLibrary(repository.base_dir / '.workspace').annotate(
                experiment.id, 'TCC · referência',
                'Simulação ideal de Bell usada somente para verificar a interface.',
                ['referência'], title='Bell · referência ideal')
            settings = QSettings(str(base / 'prefs.ini'), QSettings.IniFormat)
            window = MainWindow(repository, settings)
            window._current_experiment = experiment
            window._display_experiment(experiment)
            window._apply_draft(experiment.config, 'Bell · referência ideal')
            window.page_settings.apply_values({'theme': theme, 'font_size': args.font_size})
            window._apply_preferences()
            window.resize(args.width, args.height)
            window.show()
            screens = {key: SCREENS.get(key, key) for key in window.pages} if args.all_pages else SCREENS
            for page, suffix in screens.items():
                window.navigation.open_page(page)
                if page == 'history':
                    window.page_history.load([experiment])
                    window.page_history.set_detail(experiment, files=[])
                    window.page_history.detail_tabs.setCurrentWidget(window.page_history.circuit)
                    window.page_history.circuit.select_operation(0)
                settle(app)
                path = args.output / f'{profile}-{suffix}.png'
                if not window.grab().save(str(path)):
                    raise RuntimeError(f'Falha ao salvar {path}')
            window._unsaved_result = False
            window.close()
            window.deleteLater()
            QCoreApplication.sendPostedEvents(None, QEvent.DeferredDelete)
            app.processEvents()
            gc.collect()
    if errors:
        raise RuntimeError('\n'.join(errors))
    print(f'PASS: {len(screens) * len(PROFILES)} capturas dos temas reais, com experimento, preferências e armazenamento temporários.')


if __name__ == '__main__':
    main()
