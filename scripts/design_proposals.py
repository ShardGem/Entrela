"""Três estudos de composição Qt usando a mesma execução real, sem alterar o produto."""
from pathlib import Path
import os, sys, gc, json
from tempfile import TemporaryDirectory
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
os.environ.setdefault('QT_SCALE_FACTOR', '2')
from PySide6.QtCore import Qt, QCoreApplication, QEvent
from PySide6.QtWidgets import QApplication, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QFrame, QPushButton, QLineEdit, QSplitter
from core.examples import create_example_config
from core.simulation import run_experiment
from core.export import export_experiment_json
from gui.panels.config_panel import ConfigPanel
from gui.widgets.preparation_preview import PreparationPreview
from gui.widgets.plot_canvas import MplCanvas
from gui.widgets.sidebar import Sidebar
from gui.controllers.appearance import apply_appearance
from gui.branding import application_icon
from core.figures import draw_histograms


def label(text, role='caption'):
    item=QLabel(text); item.setWordWrap(True); item.setObjectName(role); return item


def panel(title, hint=None):
    frame=QFrame(); frame.setObjectName('StudyPanel')
    body=QVBoxLayout(frame); body.setContentsMargins(22,18,22,18); body.setSpacing(12)
    body.addWidget(label(title,'heading'))
    if hint: body.addWidget(label(hint))
    return frame,body


def main():
    output=Path(sys.argv[1] if len(sys.argv)>1 else ROOT/'docs/design/0.25.0')
    output.mkdir(parents=True,exist_ok=True)
    app=QApplication([])
    source=run_experiment(create_example_config('thermal-ising'))
    export_experiment_json(source,output/'cenario.json')
    for key,title,subtitle in [('a','Estúdio científico','Cena central e parâmetros em um inspetor lateral'),('b','Bancada integrada','Preparação e evidência dispostas simultaneamente'),('c','Caderno de investigação','Leitura sequencial com hierarquia editorial')]:
        window=QWidget(); window.setWindowIcon(application_icon()); window.resize(1920,1080)
        root=QHBoxLayout(window); root.setContentsMargins(0,0,0,0); root.setSpacing(0)
        sidebar=Sidebar(); sidebar.set_active('simulation'); root.addWidget(sidebar)
        main=QVBoxLayout(); main.setContentsMargins(28,22,28,20); main.setSpacing(18); root.addLayout(main,1)
        main.addWidget(label('ESTUDO VISUAL '+key.upper()+'  /  ENTRELA','eyebrow'))
        main.addWidget(label(title,'hero')); main.addWidget(label(subtitle))
        document=QLineEdit('Ising térmico · investigação de decoerência'); document.setObjectName('DocumentTitle'); main.addWidget(document)
        config=ConfigPanel(); config.load_config(source.config)
        preview=PreparationPreview(); preview.set_preparation(source.config.system.num_qubits,source.config.system.initial_state)
        scene, scene_layout=panel('Preparação do sistema','Prévia estrutural ideal · não representa uma nova execução')
        scene_layout.addWidget(preview,1)
        inspector, inspector_layout=panel('Parâmetros','Rascunho independente da execução apresentada')
        inspector_layout.addWidget(config,1)
        evidence, evidence_layout=panel('Execução selecionada','Dados calculados uma única vez e compartilhados entre as três propostas')
        metrics=QHBoxLayout()
        for name,value in [('Fidelidade',source.result.fidelity),('Pureza global',source.result.purity),('Energia ⟨H⟩',source.result.energy)]:
            column=QVBoxLayout(); column.addWidget(label(name)); column.addWidget(label('—' if value is None else f'{value:.6g}','number')); metrics.addLayout(column)
        evidence_layout.addLayout(metrics)
        canvas=MplCanvas(); draw_histograms(canvas.fig,[source.result.counts],frequency=True)
        evidence_layout.addWidget(canvas,1)
        if key=='a':
            center=QWidget(); center_layout=QVBoxLayout(center); center_layout.setContentsMargins(0,0,0,0)
            center_layout.addWidget(scene,2); center_layout.addWidget(evidence,3)
            split=QSplitter(Qt.Horizontal); split.addWidget(center); split.addWidget(inspector); split.setSizes([1050,450]); main.addWidget(split,1)
        elif key=='b':
            work=QHBoxLayout(); work.addWidget(inspector,3)
            middle=QVBoxLayout(); middle.addWidget(scene,2); middle.addWidget(label('Estado → Hamiltoniano → Evolução → Ruído → Medições','heading'))
            middle.addWidget(label('T₁ = '+str(source.config.noise.t1_us)+' µs\nA referência ideal e a matriz densidade permanecem identificadas.')); middle.addStretch(); work.addLayout(middle,3); work.addWidget(evidence,4); main.addLayout(work,1)
        else:
            main.addWidget(label('01  FORMULAR A PERGUNTA     →     02  PREPARAR     →     03  EXAMINAR A EVIDÊNCIA','heading'))
            work=QHBoxLayout(); work.addWidget(inspector,1)
            article=QVBoxLayout(); article.addWidget(label('Como a relaxação modifica o estado?','hero'))
            article.addWidget(label('Configuração atual: modelo térmico T₁/T₂. A evidência abaixo pertence à execução registrada, não às edições do formulário.'))
            figures=QHBoxLayout(); figures.addWidget(scene,1); figures.addWidget(evidence,2); article.addLayout(figures,1); work.addLayout(article,2); main.addLayout(work,1)
        footer=QHBoxLayout(); footer.addWidget(label('PROPOSTA VISUAL · controles de composição ilustrativos · dados de simulação reais'))
        footer.addStretch(); footer.addWidget(QPushButton('Executar simulação')); main.addLayout(footer)
        apply_appearance(window,'light',15)
        window.setStyleSheet(window.styleSheet()+'''
QWidget { background: #f3f6fa; }
QFrame#StudyPanel { background: #ffffff; border: 1px solid #dde5ef; border-radius: 10px; }
QFrame#StudyPanel QLabel, QFrame#StudyPanel QWidget { background: transparent; }
QLabel#eyebrow { color: #176eab; font-weight: 600; font-size: 12px; }
QLabel#hero { color: #142b43; font-size: 28px; font-weight: 600; }
QLabel#heading { color: #17324e; font-size: 16px; font-weight: 600; }
QLabel#caption { color: #4b6178; font-size: 13px; }
QLabel#number { color: #142b43; font-size: 28px; font-weight: 600; }
QLineEdit#DocumentTitle { background: transparent; border: none; font-size: 20px; font-weight: 600; padding: 0; }
''')
        window.show()
        for _ in range(12): app.processEvents()
        canvas.draw()
        assert window.grab().save(str(output/f'{key}-{title.lower().replace(" ","-")}.png'))
        window.close(); window.deleteLater(); QCoreApplication.sendPostedEvents(None,QEvent.DeferredDelete); app.processEvents(); gc.collect()
    print('PASS: três composições Qt, uma execução real, resolução nativa 2×.')

if __name__=='__main__': main()
