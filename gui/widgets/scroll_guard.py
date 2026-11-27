"""A roda rola a página; parâmetros só mudam quando o campo tem foco."""
from PySide6.QtCore import QObject, QEvent, QPointF
from PySide6.QtGui import QWheelEvent
from PySide6.QtWidgets import QApplication, QWidget, QAbstractSpinBox, QComboBox, QAbstractScrollArea


class ParameterScrollGuard(QObject):
    def __init__(self, window):
        super().__init__(window)
        self.window = window

    def eventFilter(self, watched, event):
        if event.type() != QEvent.Wheel or not isinstance(watched, QWidget):
            return False
        control = watched
        # A área de texto de um spinbox também pode receber a roda diretamente.
        if not isinstance(control, (QAbstractSpinBox, QComboBox)):
            control = watched.parentWidget()
        if not isinstance(control, (QAbstractSpinBox, QComboBox)):
            return False
        if not self.window.isAncestorOf(control):
            return False
        focus = QApplication.focusWidget()
        if control.hasFocus() or (focus is not None and control.isAncestorOf(focus)):
            return False
        if isinstance(control, QComboBox) and control.view().isVisible():
            return False
        parent = control.parentWidget()
        while parent is not None:
            if isinstance(parent, QAbstractScrollArea):
                horizontal = bool(event.angleDelta().x() or (not event.angleDelta().y() and event.pixelDelta().x()))
                bar = parent.horizontalScrollBar() if horizontal else parent.verticalScrollBar()
                delta = ((event.pixelDelta().x() or event.angleDelta().x()) if horizontal
                         else (event.pixelDelta().y() or event.angleDelta().y()))
                can_scroll = ((delta > 0 and bar.value() > bar.minimum()) or
                              (delta < 0 and bar.value() < bar.maximum()))
                if can_scroll:
                    viewport = parent.viewport()
                    forwarded = QWheelEvent(
                        QPointF(viewport.mapFromGlobal(event.globalPosition().toPoint())),
                        event.globalPosition(), event.pixelDelta(), event.angleDelta(),
                        event.buttons(), event.modifiers(), event.phase(), event.inverted(),
                        event.source(), event.pointingDevice(),
                    )
                    QApplication.sendEvent(viewport, forwarded)
                    if forwarded.isAccepted():
                        break
            parent = parent.parentWidget()
        event.accept()
        return True


def install_parameter_scroll_guard(window):
    """Filtro da aplicação alcança também campos criados depois da aparência."""
    if not hasattr(window, '_parameter_scroll_guard'):
        guard = ParameterScrollGuard(window)
        window._parameter_scroll_guard = guard
        QApplication.instance().installEventFilter(guard)
