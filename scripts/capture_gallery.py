"""Gera a galeria completa com capturas Qt nativas e cenários executados.

Use --scale 2 para renderizar 3840 × 2160 a partir da janela de 1920 × 1080.
Os dados, configurações e preferências usados são temporários.
"""
from __future__ import annotations

import argparse
from dataclasses import asdict, replace
from datetime import datetime, timezone
from hashlib import sha256
from importlib.metadata import version
import json
import os
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
from time import monotonic, sleep

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

CATEGORIES = {
    '01-inicio': 'Início e identidade',
    '02-aprendizado': 'Exemplos, conceitos e ajuda',
    '03-laboratorio': 'Configuração e circuitos',
    '04-resultados': 'Resultados e estados quânticos',
    '05-pesquisa': 'Estudos, mitigação e comparações',
    '06-acervo': 'Histórico, caderno e documentação',
    '07-preferencias': 'Aparência e preferências',
}
STUDY_SLUGS = {
    'temporal': 'evolucao-temporal', 'convergence': 'convergencia-trotter',
    'sweep': 'varredura-parametros', 'trotter_noise': 'trotter-e-ruido',
    'mitigation_benchmark': 'benchmark-mitigacao', 'heatmap': 'mapa-calor',
    'zne_stability': 'estabilidade-zne', 'equal_budget': 'orcamento-shots',
}


class Gallery:
    def __init__(self, app, window, args):
        self.app, self.window, self.args = app, window, args
        self.images = []
        self.errors = []
        self.args.output.mkdir(parents=True, exist_ok=True)

    def settle(self):
        for _ in range(10):
            self.app.processEvents()

    def idle(self):
        deadline = monotonic() + 120
        while self.window._current_worker is not None or self.window._storage_worker is not None:
            self.app.processEvents()
            if monotonic() > deadline:
                raise RuntimeError('Tempo excedido ao aguardar uma tarefa da galeria.')
            sleep(.01)
        self.settle()
        if self.errors:
            raise RuntimeError('\n'.join(self.errors))

    def show(self, page):
        self.idle()
        self.window._show_page(page)
        self.window.pages[page]._scroll.verticalScrollBar().setValue(0)
        self.settle()

    def capture(self, name, title, page, widget=None):
        from PySide6.QtWidgets import QToolTip
        from PySide6.QtGui import QImageWriter, QCursor
        from gui.widgets.figure_canvas import StableFigureCanvas
        target = widget or self.window
        self.idle()
        QToolTip.hideText()
        QCursor.setPos(0, 0)
        if self.app.focusWidget():
            self.app.focusWidget().clearFocus()
        self.settle()
        if self.window.drafts.timer.isActive():
            self.window.drafts.flush()
            self.settle()
        canvases = [c for c in target.findChildren(StableFigureCanvas) if c.isVisible()]
        for canvas in canvases:
            canvas.draw()
        self.settle()
        path = self.args.output / name
        if path.exists() and not self.args.overwrite:
            raise FileExistsError(f'Captura existente: {path}. Use --overwrite para regenerar.')
        path.parent.mkdir(parents=True, exist_ok=True)
        pixmap = target.grab()
        ratio = target.devicePixelRatioF()
        if widget is None and (target.width(), target.height()) != (self.args.width, self.args.height):
            raise RuntimeError('A janela não manteve as dimensões solicitadas.')
        if abs(ratio - self.args.scale) > .01:
            raise RuntimeError(f'Escala Qt inesperada: {ratio}, esperada {self.args.scale}.')
        if any(abs(c.device_pixel_ratio - ratio) > .01 for c in canvases):
            raise RuntimeError('O gráfico não acompanhou a resolução nativa da captura.')
        writer = QImageWriter(str(path), b'png')
        writer.setText('Description', f'Entrela · {title} · captura nativa Qt')
        if not writer.write(pixmap.toImage()):
            raise RuntimeError(writer.errorString())
        experiment = self.window._current_experiment
        self.images.append(dict(file=name, title=title, page=page,
                                pixels=[pixmap.width(), pixmap.height()],
                                logical_size=[target.width(), target.height()],
                                device_pixel_ratio=ratio, plot_count=len(canvases),
                                selected_result_id=experiment.id if experiment else None,
                                analysis_id=(self.window.page_analysis.data or {}).get('analysis_id')
                                if page == 'analysis' and self.window.page_analysis.tabs.currentWidget() is self.window.page_analysis.results_tab else None,
                                camera=self.window.page_bloch.canvas.camera_state() if page == 'bloch' else None,
                                snapshot_index=self.window.page_bloch.current_frame if page == 'bloch' else None,
                                sha256=sha256(path.read_bytes()).hexdigest()))
        print(f'CAPTURA: {name} · {pixmap.width()} × {pixmap.height()}', flush=True)

    def finish(self, experiments):
        from core import __version__
        missing = set(self.window.pages) - {item['page'] for item in self.images}
        if missing:
            raise RuntimeError('Páginas sem captura: ' + ', '.join(sorted(missing)))
        scenarios = [dict(id=e.id, config=asdict(e.config),
                          counts=e.result.counts, fidelity=e.result.fidelity,
                          purity=e.result.purity, energy=e.result.energy,
                          metadata=e.result.metadata, mitigation=e.result.mitigation) for e in experiments]
        (self.args.output / 'cenarios.json').write_text(json.dumps(scenarios, ensure_ascii=False, indent=2, allow_nan=False), encoding='utf-8')
        studies = [json.loads(path.read_text(encoding='utf-8'))
                   for path in sorted((self.window.repository.base_dir / '.analyses').rglob('*.json'))]
        (self.args.output / 'estudos.json').write_text(json.dumps(studies, ensure_ascii=False, indent=2, allow_nan=False), encoding='utf-8')
        manifest = dict(schema_version=1, entrela_version=__version__,
                        captured_at_utc=datetime.now(timezone.utc).isoformat(),
                        platform=sys.platform, qt_platform=os.environ.get('QT_QPA_PLATFORM'),
                        versions={name: version(name) for name in ('PySide6', 'qiskit', 'qiskit-aer', 'matplotlib', 'numpy')},
                        purpose='Documentação da interface com simulações computacionais realmente executadas. Não constitui evidência experimental do TCC.',
                        scenarios_file='cenarios.json', scenarios_sha256=sha256((self.args.output / 'cenarios.json').read_bytes()).hexdigest(),
                        studies_file='estudos.json', studies_sha256=sha256((self.args.output / 'estudos.json').read_bytes()).hexdigest(),
                        source_relation='selected_result_id identifica a execução selecionada; formulários de configuração são rascunhos independentes.',
                        expected_pages=sorted(self.window.pages), captures=self.images)
        (self.args.output / 'manifesto.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2, allow_nan=False), encoding='utf-8')
        lines = [f'# Galeria do Entrela {__version__}', '',
                 f'{len(self.images)} capturas PNG sem perdas, renderizadas diretamente no Qt. '
                 f'Janela principal: {self.args.width} × {self.args.height} pixels lógicos, escala {self.args.scale:g}×, fonte {self.args.font_size} px.', '',
                 'Os cenários foram executados em armazenamento temporário, com sementes registradas. '
                 'São demonstrações do aplicativo; não substituem os experimentos do TCC. '
                 'A splash e as janelas de configurações/exportação conservam seus tamanhos próprios, também na escala declarada.', '',
                 'Clique nos nomes para abrir os arquivos originais. '
                 '[Manifesto e hashes](manifesto.json) · [Configurações e resultados dos cenários](cenarios.json) · [Estudos calculados](estudos.json).', '']
        for folder, label in CATEGORIES.items():
            lines += ['## ' + label, '', '| Captura | Resolução |', '|---|---|']
            for item in self.images:
                if item['file'].startswith(folder + '/'):
                    lines.append(f"| [{item['title']}]({item['file']}) | {item['pixels'][0]} × {item['pixels'][1]} |")
            lines.append('')
        lines += ['## Como regenerar', '', 'A partir da raiz do projeto:', '', '```bash',
                  f'python scripts/capture_gallery.py --output docs/screenshots/{__version__} --scale 2',
                  '```', '', 'Use `--overwrite` somente para atualizar os arquivos gerados. '
                  'Nenhum experimento ou preferência pessoal é lido. '
                  'A validação destas imagens utiliza Qt offscreen no Linux; a revisão nativa no Windows permanece pendente.', '']
        (self.args.output / 'README.md').write_text('\n'.join(lines), encoding='utf-8')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT / 'work/galeria')
    parser.add_argument('--scale', type=int, choices=(1, 2), default=2)
    parser.add_argument('--width', type=int, default=1920)
    parser.add_argument('--height', type=int, default=1080)
    parser.add_argument('--font-size', type=int, choices=range(13, 19), default=15)
    parser.add_argument('--overwrite', action='store_true')
    args = parser.parse_args()
    if args.width < 1024 or args.height < 768:
        parser.error('Use uma janela de pelo menos 1024 × 768 pixels lógicos.')
    os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
    os.environ['QT_SCALE_FACTOR'] = str(args.scale)
    from PySide6.QtCore import Qt, QSettings, QTimer, QCoreApplication, QEvent
    from PySide6.QtWidgets import QApplication, QMessageBox, QAbstractButton
    from core.types import ExperimentConfig, SystemConfig, SimulationProtocol, NoiseConfig
    from core.circuit_document import CircuitDocument, CircuitGate
    from core.simulation import run_experiment
    from data.repository import ExperimentRepository
    from data.workspace import WorkspaceLibrary
    from gui.main_window import MainWindow
    from gui.splash import SplashScreen
    from gui.widgets.analysis_guidance import STUDIES

    app = QApplication([])
    with TemporaryDirectory(prefix='entrela-galeria-') as folder:
        repository = ExperimentRepository(Path(folder) / 'runs')
        library = WorkspaceLibrary(repository.base_dir / '.workspace')
        config = ExperimentConfig(SystemConfig(4, 'Ising', .7, .6, False, 'zero'),
                                  SimulationProtocol(1.2, 8, True, 2),
                                  NoiseConfig(True, p1=.002, p2=.012), 4096, 42)
        noisy = run_experiment(config)
        ideal = run_experiment(replace(config, noise=replace(config.noise, enabled=False)))
        circuit = CircuitDocument(3, (CircuitGate('h', (0,)), CircuitGate('cx', (0, 1)),
                                      CircuitGate('cx', (1, 2)), CircuitGate('rz', (2,), (.4,))))
        custom = run_experiment(ExperimentConfig(SystemConfig(3, J=0, h=0),
                                                SimulationProtocol(4, 4, True),
                                                NoiseConfig(False), 4096, 42, circuit))
        names = {ideal.id: 'Ising · 4 qubits · referência ideal', noisy.id: 'Ising · 4 qubits · ruído despolarizador',
                 custom.id: 'GHZ · 3 qubits · rotação RZ de 0,4 rad'}
        experiments = [ideal, noisy, custom]
        for experiment in experiments:
            repository.save(experiment)
            library.annotate(experiment.id, 'Galeria do Entrela',
                             'Comparação entre configurações com parâmetros e semente registrados.',
                             ['documentação', 'simulação'], title=names[experiment.id],
                             description='Evolução e preparação de estados quânticos para explorar os recursos do Entrela.',
                             objective='Comparar uma execução ideal à execução com ruído, preservando sistema, protocolo e semente.',
                             hypothesis='O ruído pode reduzir a fidelidade ao circuito ideal e a pureza do estado.',
                             methodology='Semente 42; 4096 shots; parâmetros físicos registrados na configuração.')
        library.save_template('Ising · protocolo de comparação', config)
        settings = QSettings(str(Path(folder) / 'prefs.ini'), QSettings.IniFormat)
        window = MainWindow(repository, settings)
        window.page_settings.apply_values({'font_size': args.font_size, 'reduce_motion': True})
        window._apply_preferences()
        window.resize(args.width, args.height)
        window.show()
        gallery = Gallery(app, window, args)
        def record_error(kind, value, traceback):
            gallery.errors.append(str(value))
            sys.__excepthook__(kind, value, traceback)
        sys.excepthook = record_error
        guard = QTimer(window)
        def reject_error_dialogs():
            for widget in app.topLevelWidgets():
                if isinstance(widget, QMessageBox) and widget.isVisible():
                    gallery.errors.append(widget.text())
                    widget.reject()
        guard.timeout.connect(reject_error_dialogs)
        guard.start(100)
        gallery.idle()
        def select(experiment):
            gallery.idle()
            window._current_experiment = experiment
            window._display_experiment(experiment)
            window._unsaved_result = False
            gallery.idle()
        select(noisy)
        window.page_simulation.experiment_name.setText(names[noisy.id])
        window._apply_draft(config, names[noisy.id])
        gallery.show('dashboard')
        gallery.capture('01-inicio/01-visao-geral.png', 'Visão geral do laboratório', 'dashboard')
        splash = SplashScreen()
        splash.show()
        gallery.capture('01-inicio/02-splash.png', 'Tela de abertura original', 'splash', splash)
        splash.close()
        splash.deleteLater()
        gallery.show('examples')
        window.page_examples.select_example('bell')
        gallery.capture('02-aprendizado/01-exemplos.png', 'Galeria de exemplos · Bell', 'examples')
        gallery.show('docs')
        for key, title in [('qubit', 'Qubit'), ('emaranhamento', 'Emaranhamento'), ('grover', 'Grover'), ('manual', 'Manual da plataforma')]:
            matches = [i for i in range(window.page_docs.concept_list.count())
                       if window.page_docs.concept_list.item(i).data(Qt.UserRole) == key]
            if not matches:
                raise RuntimeError(f'Conceito não encontrado: {key}')
            window.page_docs.concept_list.setCurrentRow(matches[0])
            gallery.capture(f'02-aprendizado/conceito-{key}.png', title, 'docs')
        gallery.show('simulation')
        panel = window.page_simulation.config_panel
        panel.set_mode('guided')
        for number, key in enumerate(panel.sections, 1):
            panel.set_section(key)
            slug = {'system': 'sistema', 'hamiltonian': 'hamiltoniano', 'evolution': 'evolucao', 'noise': 'ruido', 'execution': 'execucao'}[key]
            gallery.capture(f'03-laboratorio/0{number}-configurar-{slug}.png', 'Configuração guiada · ' + panel.sections[key].header.text(), 'simulation')
        panel.set_mode('advanced')
        panel.set_section('noise')
        gallery.capture('03-laboratorio/06-configuracao-avancada.png', 'Parâmetros no modo avançado', 'simulation')
        panel.set_mode('guided')
        select(custom)
        gallery.show('circuit')
        window.page_circuit.select_operation(0)
        gallery.capture('03-laboratorio/07-circuito-inspecao.png', 'Circuito executado · inspeção das portas', 'circuit')
        window.page_circuit._copy_to_editor()
        window.page_circuit.editor.circuit_name.setText('GHZ · circuito demonstrativo')
        window.page_circuit.editor._save_revision()
        window.page_circuit.editor._select(0)
        gallery.capture('03-laboratorio/08-editor.png', 'Editor e biblioteca de portas', 'circuit')
        library_toggle = next(button for button in window.page_circuit.editor.findChildren(QAbstractButton) if button.text() == 'Biblioteca')
        library_toggle.click()
        gallery.capture('03-laboratorio/09-editor-biblioteca.png', 'Biblioteca e revisões do circuito', 'circuit')
        library_toggle.click()
        window.page_circuit.editor.operation_views.setCurrentIndex(1)
        gallery.capture('03-laboratorio/10-editor-operacoes.png', 'Lista de operações acessível por teclado', 'circuit')
        window.page_circuit.editor.operation_views.setCurrentIndex(0)
        window.page_circuit.editor.advanced_section.set_expanded(True, animate=False)
        gallery.capture('03-laboratorio/11-editor-avancado.png', 'Fase global e parâmetros avançados do circuito', 'circuit')
        window.page_circuit.editor.advanced_section.set_expanded(False, animate=False)
        select(noisy)
        gallery.show('results')
        results = window.page_results
        for widget, key, title in [(results.results_tab, 'graficos', 'Distribuição observada e evolução'),
                                    (results.interpretation, 'interpretacao', 'Interpretação dos resultados'),
                                    (results.table, 'dados', 'Contagens, frequências e probabilidades'),
                                    (results.metadata, 'reprodutibilidade', 'Metadados de reprodutibilidade'),
                                    (results.state_inspector, 'estado-global', 'Matriz densidade do estado global')]:
            results.tabs.setCurrentWidget(widget)
            gallery.capture(f'04-resultados/resultados-{key}.png', title, 'results')
        gallery.show('bloch')
        bloch = window.page_bloch
        bloch.slider.setValue(5)
        bloch.canvas.set_view(22, -90)
        gallery.settle()
        bloch.canvas.fit_scene()
        gallery.capture('04-resultados/bloch-quatro-qubits.png', 'Evolução de quatro qubits em uma linha', 'bloch')
        bloch.camera_toggle.setChecked(False)
        bloch._camera_chosen()
        gallery.settle()
        bloch.canvas.fit_scene()
        gallery.capture('04-resultados/bloch-cena.png', 'Cena com controles de câmera recolhidos', 'bloch')
        bloch.visual_tabs.setCurrentIndex(1)
        gallery.capture('04-resultados/probabilidades.png', 'Probabilidades no snapshot selecionado', 'bloch')
        bloch.visual_tabs.setCurrentIndex(2)
        gallery.capture('04-resultados/bloch-estado-global.png', 'Estado global no instante selecionado', 'bloch')
        bloch.visual_tabs.setCurrentIndex(0)
        bloch.camera_toggle.setChecked(True)
        bloch.inspector_selector.setCurrentIndex(1)
        bloch.details_section.set_expanded(True, animate=False)
        gallery.settle()
        bloch._scroll.ensureWidgetVisible(bloch.timeline_detail)
        gallery.capture('04-resultados/bloch-detalhes.png', 'Transformação da etapa e estados locais', 'bloch')
        bloch.inspector_selector.setCurrentIndex(2)
        gallery.capture('04-resultados/bloch-estados-locais.png', 'Estados locais dos qubits', 'bloch')
        bloch.details_section.set_expanded(False, animate=False)
        gallery.show('analysis')
        for key, (title, _) in STUDIES.items():
            window.page_analysis.kind.setCurrentIndex(window.page_analysis.kind.findData(key))
            window.page_analysis.tabs.setCurrentWidget(window.page_analysis.configuration_tab)
            gallery.capture(f'05-pesquisa/configurar-{STUDY_SLUGS[key]}.png', title + ' · configuração', 'analysis')
        for kind, options in [('temporal', {}), ('sweep', {'parameter': 'p2', 'values': [0, .005, .01, .02, .04], 'seeds': [42]}),
                              ('heatmap', {'x_parameter': 'trotter_steps', 'x_values': [2, 4, 8], 'y_parameter': 'p2', 'y_values': [0, .01, .03]}),
                              ('mitigation_benchmark', {'qubit': 0, 'shots': 2048, 'seed': 42})]:
            window._run_analysis(kind, options)
            gallery.idle()
            if window.page_analysis.data is None or window.page_analysis.data['kind'] != kind:
                raise RuntimeError(f'Estudo não foi concluído: {kind}')
            gallery.capture(f'05-pesquisa/resultado-{STUDY_SLUGS[kind]}.png', STUDIES[kind][0] + ' · resultado calculado', 'analysis')
            if kind == 'temporal':
                gallery.show('bloch')
                bloch.camera_toggle.setChecked(True)
                bloch.inspector_selector.setCurrentIndex(3)
                bloch.details_section.set_expanded(True, animate=False)
                gallery.settle()
                bloch._scroll.ensureWidgetVisible(bloch.metrics)
                gallery.capture('04-resultados/bloch-metricas.png', 'Métricas temporais ligadas ao snapshot', 'bloch')
                bloch.details_section.set_expanded(False, animate=False)
                gallery.show('analysis')
        analysis = window.page_analysis
        analysis.tabs.setCurrentWidget(analysis.planning_tab)
        analysis.protocol.setChecked(True)
        for key, field in analysis.protocol.fields.items():
            field.setText({'title': 'Comparação de mitigação em Ising', 'question': 'Como as estimativas de Z0 mudam com a técnica de mitigação?',
                           'hypothesis': 'A extrapolação pode reduzir parte do erro, sem garantia de melhoria.',
                           'controls': 'Mesmo circuito, ruído, shots por fator e semente.', 'evidence_ref': 'Galeria do Entrela · exemplo de planejamento'}[key])
        gallery.capture('05-pesquisa/planejamento.png', 'Planejamento e protocolo científico', 'analysis')
        window._run_mitigation(0, 'linear', 4096)
        gallery.idle()
        mitigated = window._current_experiment
        if not mitigated.result.mitigation:
            raise RuntimeError('ZNE não foi concluída.')
        experiments.append(mitigated)
        library.annotate(mitigated.id, 'Galeria do Entrela', 'Extrapolação de Z0; métricas de estado preservadas da fonte.', ['documentação', 'ZNE'], title='Ising · extrapolação ZNE de Z0')
        window._refresh_history()
        gallery.show('mitigation')
        gallery.capture('05-pesquisa/mitigacao-zne.png', 'ZNE · medições, ajuste e limites', 'mitigation')
        gallery.show('comparison')
        comparison = window.page_comparison
        comparison.set_runs(ideal.id, noisy.id)
        window._prepare_comparison(ideal.id, noisy.id)
        gallery.idle()
        for i, key in enumerate(['distribuicoes', 'curvas', 'bloch', 'configuracoes']):
            comparison.tabs.setCurrentIndex(i)
            gallery.capture(f'05-pesquisa/comparacao-{key}.png', comparison.tabs.tabText(i), 'comparison')
        comparison.set_runs(noisy.id, mitigated.id)
        comparison.tabs.setCurrentIndex(5)
        gallery.capture('05-pesquisa/comparacao-metricas.png', 'Métricas numéricas da comparação', 'comparison')
        comparison.tabs.setCurrentIndex(4)
        gallery.capture('05-pesquisa/comparacao-observaveis-zne.png', 'Comparação dos observáveis ZNE', 'comparison')
        select(noisy)
        gallery.show('history')
        window.page_history.set_detail(noisy, files=[])
        gallery.capture('06-acervo/historico-resumo.png', 'Histórico e resumo da execução', 'history')
        select(custom)
        window.page_history.set_detail(custom, files=[])
        window.page_history.detail_tabs.setCurrentWidget(window.page_history.circuit)
        window.page_history.circuit.select_operation(0)
        gallery.capture('06-acervo/historico-circuito.png', 'Circuito gráfico no histórico', 'history')
        select(noisy)
        gallery.show('library')
        window.page_library.sections['planning'].set_expanded(True, animate=False)
        gallery.capture('06-acervo/caderno.png', 'Caderno e plano científico', 'library')
        window.page_library.show_configurations()
        gallery.capture('06-acervo/configuracoes-salvas.png', 'Biblioteca de configurações reutilizáveis', 'library', window.configuration_dialog)
        window.configuration_dialog.close()
        gallery.show('documentation')
        gallery.capture('06-acervo/evidencias.png', 'Evidências do estudo', 'documentation')
        window.page_documentation.open_export('pdf')
        gallery.capture('06-acervo/documentacao.png', 'Preparar relatório científico', 'documentation', window.page_documentation.export_dialog)
        window.page_documentation.export_dialog.close()
        for kind, title in [('zip', 'Pacote científico completo'), ('gif', 'Animação com snapshots reais')]:
            window.page_documentation.open_export(kind)
            gallery.capture(f'06-acervo/exportacao-{kind}.png', title, 'documentation', window.page_documentation.export_dialog)
            window.page_documentation.export_dialog.close()
        gallery.show('settings')
        for index, (slug, title) in enumerate([('aparencia', 'Aparência e tipografia'), ('acessibilidade', 'Acessibilidade e notificações'), ('exportacao', 'Preferências de exportação'), ('backup-exportacao', 'Dados e backup')]):
            window.page_settings.category.setCurrentIndex(index)
            gallery.capture(f'07-preferencias/{slug}.png', title, 'settings')
        for theme, label in [('light', 'claro'), ('navy', 'azul-escuro')]:
            window.page_settings.theme.setCurrentIndex(window.page_settings.theme.findData(theme))
            gallery.show('results')
            results.tabs.setCurrentWidget(results.results_tab)
            gallery.capture(f'07-preferencias/tema-{label}.png', 'Resultados · tema ' + label, 'results')
        window.page_settings.theme.setCurrentIndex(window.page_settings.theme.findData('dark'))
        gallery.show('simulation')
        window._begin_tutorial()
        gallery.capture('02-aprendizado/tutorial.png', 'Tutorial de Bell com etapas verificáveis', 'simulation')
        window.tutorial_dock.hide()
        window.help_dock.show()
        gallery.capture('02-aprendizado/ajuda-contextual.png', 'Ajuda contextual durante a configuração', 'simulation')
        window.help_dock.hide()
        gallery.finish(experiments)
        guard.stop()
        window._unsaved_result = False
        window.close()
        window.deleteLater()
        QCoreApplication.sendPostedEvents(None, QEvent.DeferredDelete)
        app.processEvents()
    print(f'PASS: {len(gallery.images)} capturas; todas as 14 páginas documentadas; dados temporários.', flush=True)


if __name__ == '__main__':
    main()
