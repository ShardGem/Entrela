"""Verificação do executável instalado, sem depender do checkout ou de pytest."""
from pathlib import Path
import json
import sys
import traceback


def check_bundle(report_path):
    report_path = Path(report_path).resolve()
    report_path.parent.mkdir(parents=True, exist_ok=True)
    receipt = {'success': False, 'frozen': bool(getattr(sys, 'frozen', False)), 'checks': []}
    window = None
    try:
        from dataclasses import replace
        from tempfile import TemporaryDirectory
        from PySide6.QtCore import QSettings
        from PySide6.QtWidgets import QApplication
        from gui.branding import application_icon, configure_application_identity
        from gui.main_window import MainWindow
        from core import __version__
        from core.examples import create_example_config
        from core.simulation import run_experiment
        from core.export import export_experiment_json, import_experiment_json
        from core.report import export_report
        from data.repository import ExperimentRepository
        from data.workspace_backup import create_workspace_backup, prepare_workspace_restore
        app = QApplication.instance() or QApplication([])
        configure_application_identity(app)
        if receipt['frozen']:
            import gui
            assert Path(gui.__file__).is_relative_to(Path(sys._MEIPASS)), 'O pacote carregou código externo'
        receipt.update(version=__version__, qt_platform=app.platformName())
        assert not application_icon().pixmap(64, 64).isNull(), 'Ícone ausente'
        receipt['checks'].append('Ícones e plataforma Qt')
        with TemporaryDirectory(prefix='entrela-verificacao-') as directory:
            base = Path(directory)
            repo = ExperimentRepository(base / 'runs')
            settings = QSettings(str(base / 'prefs.ini'), QSettings.IniFormat)
            window = MainWindow(repo, settings)
            window.resize(1280, 900)
            window.show()
            app.processEvents()
            window.onboarding.show_welcome()
            assert window.onboarding.dialog.isVisible()
            window.onboarding.dialog.actions['guide'].click()
            assert window.is_page_active('docs')
            receipt['checks'].append('Janela, fontes e introdução opcional')
            config = replace(create_example_config('bell'), shots=128, seed=42)
            ideal = run_experiment(config)
            assert not ideal.result.error and ideal.result.final_state.is_valid()
            assert sum(ideal.result.counts.values()) == 128
            assert set(ideal.result.counts) <= {'00', '11'}
            assert abs(ideal.result.purity - 1) < 1e-10
            repo.save(ideal)
            window._current_experiment = ideal
            window._display_experiment(ideal)
            receipt['checks'].append('Bell ideal, Aer e metadados das dependências')
            noisy = run_experiment(replace(config, noise=replace(config.noise, enabled=True)))
            assert not noisy.result.error and noisy.result.final_state.is_valid()
            repo.save(noisy)
            receipt['checks'].append('Simulação ruidosa por matriz densidade')
            from core.circuits import build_circuit
            from core.mitigation import run_zne
            from core.noise import build_noise_model
            circuit, _ = build_circuit(2, 'Ising', 0, 0, False, 1, 2, False,
                                       initial_state='bell', measure=False)
            mitigated = run_zne(circuit, build_noise_model(noisy.config.noise), shots=64, seed=42)
            assert mitigated['scale_factors'] == [1, 3, 5]
            receipt['checks'].append('ZNE com folding 1, 3 e 5')
            window._show_page('results')
            app.processEvents()
            image_path = report_path.with_suffix('.png')
            assert window.grab().save(str(image_path))
            window.page_history.load([ideal, noisy])
            window.page_history.set_detail(ideal, files=[])
            window.page_history.circuit.select_operation(0)
            assert 'Hadamard' in window.page_history.circuit.details.text()
            exported = export_experiment_json(ideal, base / 'bell.json')
            assert import_experiment_json(exported).config == ideal.config
            pdf = base / 'relatorio.pdf'
            export_report(ideal, pdf, raster_dpi=150)
            assert pdf.read_bytes().startswith(b'%PDF-')
            receipt['checks'].append('Histórico gráfico, JSON e relatório PDF')
            # O backup exige ausência de gravações concorrentes, como no fluxo
            # da interface. Encerrar a edição também grava e pausa os rascunhos.
            window._unsaved_result = False
            window.close()
            app.processEvents()
            # Registra diferenças de stat/fstat do sistema operacional apenas
            # no recibo técnico; não altera a validação dos arquivos do backup.
            from data.workspace_backup import _signature
            signature_differences = []
            for file_path in sorted(repo.base_dir.rglob('*')):
                if not file_path.is_file() or file_path.name == '.entrela.lock':
                    continue
                import os
                path_signature = _signature(file_path.lstat())
                with file_path.open('rb') as source:
                    handle_signature = _signature(os.fstat(source.fileno()))
                if path_signature != handle_signature:
                    signature_differences.append(dict(file=file_path.relative_to(repo.base_dir).as_posix(),
                                                     path=path_signature, handle=handle_signature))
            if signature_differences:
                receipt['stat_differences'] = signature_differences
            create_workspace_backup(repo.base_dir, base / 'backup.zip', {'onboarding/welcome_seen': True})
            restored = prepare_workspace_restore(base / 'backup.zip', base / 'restored')
            restored.commit()
            assert ExperimentRepository(base / 'restored').load(ideal.id).result.counts == ideal.result.counts
            window = MainWindow(repo, settings)
            assert window.settings.value('onboarding/welcome_seen', False, type=bool)
            assert len(repo.list_all()) == 2
            receipt['checks'].append('Backup, persistência e reabertura')
            window.close()
            window = None
            app.processEvents()
        receipt['success'] = True
    except Exception:
        receipt['error'] = traceback.format_exc()
    finally:
        if window is not None:
            window._unsaved_result = False
            window.close()
        report_path.write_text(json.dumps(receipt, ensure_ascii=False, indent=2), encoding='utf-8')
    return 0 if receipt['success'] else 1
