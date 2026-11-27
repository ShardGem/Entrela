"""Rolagem não altera campos sem foco e continua chegando à página."""
import pytest
from PySide6.QtCore import Qt, QPoint, QPointF
from PySide6.QtGui import QWheelEvent
from PySide6.QtWidgets import QWidget, QVBoxLayout, QScrollArea, QLineEdit, QSpinBox, QComboBox, QApplication
from gui.widgets.scientific_input import ScientificSpinBox
from gui.widgets.scroll_guard import install_parameter_scroll_guard


def wheel(widget, delta):
    pos = widget.rect().center()
    event = QWheelEvent(QPointF(pos), QPointF(widget.mapToGlobal(pos)), QPoint(), QPoint(0,delta),
                        Qt.NoButton, Qt.NoModifier, Qt.ScrollUpdate, False)
    QApplication.sendEvent(widget, event)


@pytest.fixture
def controls(qt_app):
    window = QWidget()
    root = QVBoxLayout(window)
    other = QLineEdit()
    root.addWidget(other)
    scroll = QScrollArea();scroll.setWidgetResizable(True);root.addWidget(scroll)
    body = QWidget();layout = QVBoxLayout(body)
    fields = {}
    for key in ('J','qubits','shots','modelo'):
        field = QComboBox() if key == 'modelo' else ScientificSpinBox() if key == 'J' else QSpinBox()
        if key == 'modelo':
            field.addItems(['Ising','Heisenberg','XXZ']);field.setCurrentIndex(1)
        else:
            field.setRange(-100,1_000_000);field.setValue(4)
        fields[key] = field;layout.addWidget(field)
    filler = QWidget();filler.setMinimumHeight(900);layout.addWidget(filler)
    scroll.setWidget(body)
    install_parameter_scroll_guard(window)
    window.resize(400,300);window.show();window.activateWindow();other.setFocus()
    qt_app.processEvents()
    yield window,other,scroll,body,layout,fields
    window.close();window.deleteLater();qt_app.processEvents()


@pytest.mark.parametrize('name',['J','qubits','shots','modelo'])
def test_unfocused_wheel_preserves_parameter_and_scrolls_page(controls,qt_app,name):
    _,other,scroll,_,_,fields = controls
    field = fields[name];other.setFocus();qt_app.processEvents()
    value = field.currentIndex() if isinstance(field,QComboBox) else field.value()
    assert not field.hasFocus()
    wheel(field,-120)
    assert (field.currentIndex() if isinstance(field,QComboBox) else field.value()) == value
    assert scroll.verticalScrollBar().value() > 0


@pytest.mark.parametrize('name',['J','qubits','shots','modelo'])
def test_focused_wheel_keeps_native_field_behavior(controls,qt_app,name):
    _,_,scroll,_,_,fields = controls
    field = fields[name];field.setFocus();qt_app.processEvents()
    assert field.hasFocus()
    value = field.currentIndex() if isinstance(field,QComboBox) else field.value()
    wheel(field,120)
    assert (field.currentIndex() if isinstance(field,QComboBox) else field.value()) != value


def test_guard_covers_new_fields_after_installation(controls,qt_app):
    _,other,scroll,_,layout,_ = controls
    field = ScientificSpinBox();field.setValue(.1);layout.insertWidget(0,field)
    other.setFocus();qt_app.processEvents()
    wheel(field,-120)
    assert field.value() == .1
    assert scroll.verticalScrollBar().value() > 0


def test_scroll_continues_in_outer_page_at_an_inner_panel_boundary(controls,qt_app):
    _,other,outer,_,layout,_ = controls
    inner = QScrollArea();inner.setWidgetResizable(True);inner.setFixedHeight(100)
    body = QWidget();inside = QVBoxLayout(body)
    field = ScientificSpinBox();field.setValue(.1);inside.addWidget(field)
    filler = QWidget();filler.setMinimumHeight(500);inside.addWidget(filler)
    inner.setWidget(body);layout.insertWidget(0,inner)
    other.setFocus();qt_app.processEvents()
    inner.verticalScrollBar().setValue(inner.verticalScrollBar().maximum())
    assert inner.verticalScrollBar().value()>0
    wheel(field,-120)
    assert field.value()==.1
    assert inner.verticalScrollBar().value()==inner.verticalScrollBar().maximum()
    assert outer.verticalScrollBar().value()>0
