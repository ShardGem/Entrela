import numpy as np
from PySide6.QtWidgets import QWidget,QHBoxLayout
from gui.widgets.plot_canvas import MplCanvas
from gui.theme import PALETTE
class ResultsTab(QWidget):
    def __init__(self,parent=None):
        super().__init__(parent)
        layout=QHBoxLayout(self)
        self.canvas_hist=MplCanvas(self)
        self.canvas_evol=MplCanvas(self)
        layout.addWidget(self.canvas_hist)
        layout.addWidget(self.canvas_evol)
    def exibir_histograma(self,counts,titulo="Distribuição observada"):
        ax=self.canvas_hist.reset_axes()
        if counts:
            keys=sorted(counts)
            ax.bar(keys,[counts[k] for k in keys],color=PALETTE.primary)
            ax.tick_params(axis="x",labelrotation=90 if len(keys)>8 else 0)
        else:ax.text(.5,.5,"Sem contagens",color=PALETTE.text,ha="center",transform=ax.transAxes)
        ax.set_title(titulo)
        ax.set_ylabel("Contagens")
        ax.set_xlabel("Estado (q0 à direita)")
        self.canvas_hist.draw()
    def exibir_evolucao_temporal(self,states,times=None):
        ax=self.canvas_evol.reset_axes()
        if states:
            probabilities=np.asarray([s.probabilities() for s in states])
            indices=np.argsort(probabilities[-1])[-min(4,probabilities.shape[1]):]
            time=times if times is not None and len(times)==len(states) else np.arange(len(states))
            for index in sorted(indices):
                ax.plot(time,probabilities[:,index],".-",label=f"|{index:0{int(np.log2(states[0].dim))}b}⟩")
            ax.legend(facecolor=PALETTE.surface,edgecolor=PALETTE.border,labelcolor=PALETTE.text)
            ax.set_ylim(-.03,1.03)
        else:ax.text(.5,.5,"Ative snapshots para registrar a evolução",color=PALETTE.text,
                     ha="center",transform=ax.transAxes)
        ax.set_title("Evolução — até 4 estados mais prováveis")
        ax.set_xlabel("Tempo (adimensional, ℏ=1)")
        ax.set_ylabel("Probabilidade")
        self.canvas_evol.draw()
