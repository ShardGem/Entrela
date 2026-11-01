"""Round-trip IEEE-754 parameters, including tiny imported values."""

from PySide6.QtWidgets import QDoubleSpinBox
from PySide6.QtGui import QValidator
from math import isfinite


class ScientificSpinBox(QDoubleSpinBox):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setDecimals(323)
        self.setKeyboardTracking(False)

    def textFromValue(self, value):
        return repr(float(value))

    def valueFromText(self, text):
        text = text.removesuffix(self.suffix()).strip().replace(",", ".")
        try:
            return float(text)
        except ValueError:
            return self.value()

    def validate(self, text, pos):
        value = text.removesuffix(self.suffix()).strip().replace(",", ".")
        try:
            number = float(value)
            state = (
                QValidator.Acceptable
                if isfinite(number) and self.minimum() <= number <= self.maximum()
                else QValidator.Intermediate
            )
        except ValueError:
            state = QValidator.Intermediate
        return state, text, pos
