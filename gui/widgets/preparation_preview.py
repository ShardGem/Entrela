"""Vector schematic of the configured ideal preparation; never simulated data."""
from PySide6.QtCore import Qt, QRectF, QPointF, QSize, QEvent
from PySide6.QtGui import QPainter, QPen, QColor
from PySide6.QtWidgets import QWidget
from gui.theme import PALETTE


class PreparationPreview(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.qubits = 2
        self.initial = "zero"
        self.setAccessibleName("Diagrama da preparação ideal, sem ruído")
        self.setToolTip("Prévia estrutural. Não executa o circuito nem prevê os resultados da simulação ruidosa.")
        self._fit_metrics()

    def sizeHint(self):
        return QSize(300, self.minimumHeight())

    def set_preparation(self, qubits, initial):
        self.qubits,self.initial = qubits,initial
        self._fit_metrics()
        self.update()

    def refresh_theme(self):
        self._fit_metrics()
        self.update()

    def changeEvent(self, event):
        super().changeEvent(event)
        if event.type() in (QEvent.FontChange, QEvent.StyleChange) and hasattr(self, "qubits"):
            self._fit_metrics()

    def _fit_metrics(self):
        metrics = self.fontMetrics()
        self._gate_size = max(24, metrics.height()+6)
        self._row_height = self._gate_size+12
        self._label_width = metrics.horizontalAdvance("q3  |0⟩")+4
        extra = metrics.height()+12 if self.qubits > 4 else 0
        self.setMinimumHeight(max(128, min(4, self.qubits)*self._row_height+24+extra))
        self.updateGeometry()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setFont(self.font())
        p = PALETTE
        rect = QRectF(self.rect()).adjusted(1,1,-1,-1)
        painter.setBrush(QColor(p.bg_elevated))
        painter.setPen(QPen(QColor(p.border),1))
        painter.drawRoundedRect(rect,8,8)
        if self.initial == "bell" and self.qubits != 2:
            painter.setPen(QColor(p.warning))
            painter.drawText(rect.adjusted(12,8,-12,-8),Qt.AlignCenter|Qt.TextWordWrap,"Bell requer dois qubits.\nAjuste o sistema para visualizar a preparação.")
            return
        rows = min(4,self.qubits)
        scale = min(1.8, max(1., self.width()/480), max(1., self.height()/(rows*70+40)))
        row_height = self._row_height * scale
        gate_size = self._gate_size * scale
        extra = self.fontMetrics().height()+12 if self.qubits > rows else 0
        top = (self.height()-extra-(rows-1)*row_height)/2
        start,end = self._label_width+30,self.width()-24
        gate_x = start+(end-start)*.33
        control_x = start+(end-start)*.68
        for q in range(rows):
            y = top+q*row_height
            painter.setPen(QColor(p.text_muted))
            painter.drawText(QRectF(12,y-row_height/2,self._label_width,row_height),Qt.AlignVCenter|Qt.AlignLeft,f"q{q}  |0⟩")
            painter.setPen(QPen(QColor(p.border_strong),1.2))
            painter.drawLine(QPointF(start,y),QPointF(end,y))
            if self.initial == "plus" or (self.initial == "bell" and q == 0):
                painter.setPen(QPen(QColor(p.primary),1.2))
                painter.setBrush(QColor(p.primary_faint))
                gate = QRectF(gate_x-gate_size/2,y-gate_size/2,gate_size,gate_size)
                painter.drawRoundedRect(gate,4,4)
                painter.setPen(QColor(p.primary))
                painter.drawText(gate,Qt.AlignCenter,"H")
        if self.initial == "bell":
            painter.setPen(QPen(QColor(p.primary),1.4))
            painter.drawLine(QPointF(control_x,top),QPointF(control_x,top+row_height))
            painter.setBrush(QColor(p.primary))
            painter.drawEllipse(QPointF(control_x,top),3,3)
            painter.setBrush(QColor(p.bg_elevated))
            painter.drawEllipse(QPointF(control_x,top+row_height),8,8)
            painter.drawLine(QPointF(control_x-6,top+row_height),QPointF(control_x+6,top+row_height))
            painter.drawLine(QPointF(control_x,top+row_height-6),QPointF(control_x,top+row_height+6))
        if self.qubits > rows:
            painter.setPen(QColor(p.text_dim))
            painter.drawText(QRectF(8,self.height()-extra,self.width()-16,extra),Qt.AlignCenter,f"+ {self.qubits-rows} qubits · mesma preparação")
