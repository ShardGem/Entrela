"""Interactive circuit diagrams built on Qt Graphics View (PySide6)."""

import math
from fractions import Fraction
from PySide6.QtCore import Qt, QRectF, QSize, Signal
from PySide6.QtGui import QColor, QPen, QBrush, QPainter, QFont
from PySide6.QtWidgets import QGraphicsView, QGraphicsScene, QGraphicsItem, QSizePolicy
from gui.theme import PALETTE
from core.circuit_document import GATE_HELP

LEFT, TOP, WIRE, COLUMN = 110, 80, 68, 100


def angle_label(value):
    fraction = Fraction(float(value) / math.pi).limit_denominator(16)
    if abs(float(fraction) * math.pi - value) < 1e-8 and fraction:
        numerator, denominator = fraction.numerator, fraction.denominator
        sign = "−" if numerator < 0 else ""
        return (
            sign
            + ("" if abs(numerator) == 1 else str(abs(numerator)))
            + "π"
            + ("" if denominator == 1 else "/" + str(denominator))
        )
    return f"{value:.4g}"


class GateItem(QGraphicsItem):
    def __init__(self, operation, index, column, view):
        super().__init__()
        self.operation = operation
        self.index = index
        self.column = column
        self.view = view
        self.setPos(LEFT + column * COLUMN, 0)
        self.setData(0, index)
        self.setFlag(QGraphicsItem.ItemIsSelectable)
        self.setFlag(QGraphicsItem.ItemIsFocusable)
        self.setFlag(QGraphicsItem.ItemIsMovable, view.editable)
        self.setAcceptHoverEvents(True)
        self.hover = False
        qs = operation["qubits"]
        self.low = TOP + min(qs) * WIRE
        self.high = TOP + max(qs) * WIRE
        self.setToolTip(
            f"Operação {index + 1}: {operation['name'].upper()}\n"
            + GATE_HELP.get(operation['name'], "Operação sintetizada do circuito; consulte os parâmetros na inspeção.")
            + f"\nQubits: {', '.join('q'+str(q) for q in qs)}\nParâmetros (rad): {operation.get('parameters', [])}\n"
            + (
                "Arraste horizontalmente para reordenar."
                if view.editable
                else "Clique para inspecionar."
            )
        )

    def boundingRect(self):
        return QRectF(-43, self.low - 29, 86, self.high - self.low + 61)

    def hoverEnterEvent(self, event):
        self.hover = True
        self.update()
        super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event):
        self.hover = False
        self.update()
        super().hoverLeaveEvent(event)

    def paint(self, painter, option, widget=None):
        painter.setRenderHint(QPainter.Antialiasing)
        op = self.operation
        name = op["name"]
        qs = op["qubits"]
        color = PALETTE.q2 if op.get("stage") == "preparation" else PALETTE.primary
        if name == "measure":
            color = PALETTE.success
        pen = QPen(QColor(color), 2.5 if self.isSelected() else 1.4)
        painter.setPen(pen)
        painter.setBrush(
            QColor(
                PALETTE.surface_active
                if self.isSelected() or self.hover
                else PALETTE.surface
            )
        )
        ys = [TOP + q * WIRE for q in qs]
        if len(ys) > 1:
            painter.drawLine(0, int(min(ys)), 0, int(max(ys)))
        if name in ("cx", "cy", "cz", "ch", "ccx"):
            for y in ys[:-1]:
                painter.setBrush(QColor(color))
                painter.drawEllipse(QRectF(-5, y - 5, 10, 10))
            y = ys[-1]
            painter.setBrush(QColor(PALETTE.surface))
            if name in ("cx", "ccx"):
                painter.drawEllipse(QRectF(-15, y - 15, 30, 30))
                painter.drawLine(-10, y, 10, y)
                painter.drawLine(0, y - 10, 0, y + 10)
            else:
                painter.drawRoundedRect(QRectF(-22, y - 20, 44, 40), 6, 6)
                painter.drawText(
                    QRectF(-22, y - 20, 44, 40), Qt.AlignCenter, name[-1].upper()
                )
        elif name == "swap":
            for y in ys:
                painter.drawLine(-10, y - 10, 10, y + 10)
                painter.drawLine(-10, y + 10, 10, y - 10)
        else:
            for y in ys:
                painter.setBrush(
                    QColor(
                        PALETTE.surface_active if self.isSelected() else PALETTE.surface
                    )
                )
                painter.drawRoundedRect(QRectF(-36, y - 23, 72, 46), 7, 7)
                painter.setFont(QFont("Segoe UI", 10, QFont.DemiBold))
                painter.drawText(
                    QRectF(-34, y - 22, 68, 26),
                    Qt.AlignCenter,
                    "M" if name == "measure" else name.upper(),
                )
                if self.view.show_parameters and op.get("parameters"):
                    painter.setFont(QFont("Segoe UI", 8))
                    painter.setPen(QColor(PALETTE.text_muted))
                    text = ", ".join(angle_label(v) for v in op["parameters"])
                    text = painter.fontMetrics().elidedText(text, Qt.ElideRight, 64)
                    painter.drawText(QRectF(-34, y + 4, 68, 18), Qt.AlignCenter, text)
                    painter.setPen(pen)
        if self.isSelected() or self.hasFocus():
            painter.setPen(QPen(QColor(PALETTE.text), 1, Qt.DashLine))
            painter.setBrush(Qt.NoBrush)
            painter.drawRoundedRect(self.boundingRect(), 8, 8)

    def mousePressEvent(self, event):
        self._press_x = self.pos().x()
        self.setFocus(Qt.MouseFocusReason)
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        x = self.pos().x()
        self.setPos(self._press_x, 0)
        super().mouseReleaseEvent(event)
        if self.view.editable and abs(x - self._press_x) > COLUMN * 0.3:
            target = self.view.offset + round((x - LEFT) / COLUMN)
            target = max(0, min(self.view.total_operations - 1, target))
            if target != self.index:
                self.view.move_requested.emit(self.index, target)


class CircuitCanvas(QGraphicsView):
    operation_selected = Signal(int)
    operations_selected = Signal(list)
    move_requested = Signal(int, int)
    zoom_changed = Signal(int)

    def __init__(self, parent=None, editable=False):
        super().__init__(parent)
        self.editable = editable
        self.show_parameters = True
        self.offset = 0
        self.total_operations = 0
        self.scene_model = QGraphicsScene(self)
        self.setScene(self.scene_model)
        self.setRenderHints(QPainter.Antialiasing | QPainter.TextAntialiasing)
        self.setDragMode(QGraphicsView.ScrollHandDrag)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setMinimumSize(260, 240)
        self.scene_model.selectionChanged.connect(self._selection)
        self.setToolTip(
            "Clique ou use as setas: inspecionar · roda: zoom · arraste o fundo: navegar"
            + (" · arraste uma porta: reordenar" if self.editable else " · consulta sem edição")
        )
        self.description = "Circuito Entrela"
        self.operations = []
        self.num_qubits = 2
        self._keyboard_index = None
        self._selection_anchor = None
        self.setAccessibleName("Desenho do circuito quântico")
        self.setAccessibleDescription("Use as setas para selecionar portas em ordem de execução. Shift e setas ampliam a seleção.")
        self.refresh_theme()

    def sizeHint(self):
        return QSize(800, 380)

    def minimumSizeHint(self):
        return QSize(260, 240)

    def refresh_theme(self):
        self.setBackgroundBrush(QBrush(QColor(PALETTE.bg)))
        self.scene_model.setBackgroundBrush(QBrush(QColor(PALETTE.bg)))
        selection = self.scene_model.selectedItems()
        indexes = [item.data(0) for item in selection]
        if self.operations:
            self.set_operations(
                self.operations, self.num_qubits, self.offset, self.total_operations
            )
            self.select_operations(indexes)

    def _selection(self):
        items = self.scene_model.selectedItems()
        focus = self.scene_model.focusItem()
        self._keyboard_index = (focus.index if isinstance(focus, GateItem) and focus.isSelected()
                                else max((item.index for item in items), default=None))
        self._selection_anchor = self._keyboard_index
        self.operations_selected.emit(sorted(item.data(0) for item in items))
        if items:
            self.operation_selected.emit(items[0].data(0))

    def set_operations(self, operations, num_qubits, offset=0, total=None):
        self.operations = list(operations)
        self.num_qubits = num_qubits
        self.offset = offset
        self.total_operations = total if total is not None else len(operations)
        self.scene_model.blockSignals(True)
        self.scene_model.clear()
        width = max(800, LEFT + len(operations) * COLUMN + 70)
        height = TOP + num_qubits * WIRE + 85
        self.setSceneRect(0, 0, width, height)
        for q in range(num_qubits):
            y = TOP + q * WIRE
            self.scene_model.addLine(
                LEFT - 60, y, width - 30, y, QPen(QColor(PALETTE.border_strong), 1.2)
            )
            label = self.scene_model.addText(
                f"q{q}", QFont("Segoe UI", 11, QFont.DemiBold)
            )
            label.setDefaultTextColor(QColor(getattr(PALETTE, f"q{q + 1}")))
            label.setPos(16, y - 15)
        bus = TOP + num_qubits * WIRE + 22
        for delta in (0, 4):
            self.scene_model.addLine(
                LEFT - 60,
                bus + delta,
                width - 30,
                bus + delta,
                QPen(QColor(PALETTE.text_dim), 1),
            )
        label = self.scene_model.addText(f"c[{num_qubits}]", QFont("Segoe UI", 10))
        label.setDefaultTextColor(QColor(PALETTE.text_muted))
        label.setPos(10, bus - 12)
        previous = None
        for column, op in enumerate(operations):
            stage = (op.get("stage"), op.get("step"))
            if stage != previous:
                title = {
                    "preparation": "Preparação",
                    "evolution": "Passo",
                    "measurement": "Medição",
                }.get(stage[0], "Portas")
                if stage[0] == "evolution":
                    title += f" {stage[1]}"
                text = self.scene_model.addText(title, QFont("Segoe UI", 8))
                text.setDefaultTextColor(QColor(PALETTE.text_dim))
                text.setPos(LEFT + column * COLUMN - 35, 18)
            previous = stage
            self.scene_model.addItem(GateItem(op, offset + column, column, self))
            if op["name"] == "measure":
                x = LEFT + column * COLUMN
                y = TOP + op["qubits"][0] * WIRE + 25
                self.scene_model.addLine(
                    x, y, x, bus, QPen(QColor(PALETTE.success), 1.2, Qt.DashLine)
                )
                text = self.scene_model.addText(
                    str(op["qubits"][0]), QFont("Segoe UI", 8)
                )
                text.setDefaultTextColor(QColor(PALETTE.success))
                text.setPos(x + 3, bus - 20)
        self.scene_model.blockSignals(False)

    def select_operation(self, index):
        self.select_operations([index])

    def select_operations(self, indexes):
        indexes = set(indexes)
        self._keyboard_index = max(indexes, default=None)
        self._selection_anchor = self._keyboard_index
        self.scene_model.blockSignals(True)
        for item in self.scene_model.items():
            if isinstance(item, GateItem):
                chosen = item.index in indexes
                item.setSelected(chosen)
                if chosen:
                    self.ensureVisible(item)
        self.scene_model.blockSignals(False)

    def keyPressEvent(self, event):
        previous = (Qt.Key_Left, Qt.Key_Up)
        following = (Qt.Key_Right, Qt.Key_Down)
        navigation = (*previous, *following, Qt.Key_Home, Qt.Key_End)
        if (event.key() not in navigation or not self.operations
                or event.modifiers() & (Qt.ControlModifier | Qt.AltModifier | Qt.MetaModifier)):
            super().keyPressEvent(event)
            return
        first, last = self.offset, self.offset + len(self.operations) - 1
        current = self._keyboard_index
        if event.key() == Qt.Key_Home:
            target = first
        elif event.key() == Qt.Key_End:
            target = last
        elif current is None:
            target = last if event.key() in previous else first
        else:
            target = max(first, min(last, current + (-1 if event.key() in previous else 1)))
        anchor = self._selection_anchor
        extending = bool(event.modifiers() & Qt.ShiftModifier)
        indexes = list(range(min(anchor, target), max(anchor, target) + 1)) if extending and anchor is not None else [target]
        self.select_operations(indexes)
        self._keyboard_index = target
        self._selection_anchor = anchor if extending and anchor is not None else target
        item = next((item for item in self.scene_model.items()
                     if isinstance(item, GateItem) and item.index == target), None)
        if item:
            item.setFocus(Qt.OtherFocusReason)
            self.ensureVisible(item)
        self.operations_selected.emit(indexes)
        self.operation_selected.emit(target)
        event.accept()

    def set_zoom(self, percent):
        factor = max(0.35, min(2.5, percent / 100))
        self.resetTransform()
        self.scale(factor, factor)
        self.zoom_changed.emit(round(factor * 100))

    def fit_circuit(self):
        ratio = min(
            self.viewport().width() / self.sceneRect().width(),
            self.viewport().height() / self.sceneRect().height(),
        )
        self.set_zoom(round(max(0.35, min(1.5, ratio * 0.95)) * 100))
        self.centerOn(self.sceneRect().center())

    def wheelEvent(self, event):
        steps = (
            event.angleDelta().y() / 120
            if event.angleDelta().y()
            else event.pixelDelta().y() / 120
        )
        self.set_zoom(
            round(self.transform().m11() * 100 * math.exp(max(-4, min(4, steps)) * 0.1))
        )
        event.accept()

    def export_svg(self, path):
        from PySide6.QtSvg import QSvgGenerator

        generator = QSvgGenerator()
        generator.setFileName(str(path))
        generator.setTitle("Entrela · Circuito quântico")
        generator.setDescription(self.description)
        generator.setSize(self.sceneRect().size().toSize())
        generator.setViewBox(self.sceneRect())
        painter = QPainter(generator)
        try:
            self.scene_model.render(painter)
        finally:
            painter.end()
