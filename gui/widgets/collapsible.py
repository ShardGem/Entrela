"""Progressive disclosure that preserves contents, focus and motion preferences."""
from PySide6.QtCore import Qt, Signal, QPropertyAnimation, QEasingCurve
from PySide6.QtWidgets import QApplication, QFrame, QToolButton, QWidget, QVBoxLayout, QLabel


class CollapsibleSection(QFrame):
    expanded_changed = Signal(bool)

    def __init__(self, title, *, expanded=False, parent=None):
        super().__init__(parent)
        self.setObjectName("SectionCard")
        self._expanded = expanded
        self._collapsible = True
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 14)
        layout.setSpacing(8)
        self.header = QToolButton()
        self.header.setObjectName("SectionToggle")
        self.header.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        self.header.setText(title)
        self.header.setCheckable(True)
        self.header.setChecked(expanded)
        self.header.setAccessibleName(title)
        self.header.clicked.connect(self._toggle)
        layout.addWidget(self.header)
        self.summary = QLabel()
        self.summary.setObjectName("SectionSubtitle")
        self.summary.setWordWrap(True)
        layout.addWidget(self.summary)
        self.content = QWidget()
        self.content.setObjectName("SectionContent")
        self.content_layout = QVBoxLayout(self.content)
        self.content_layout.setContentsMargins(0, 4, 0, 0)
        self.content_layout.setSpacing(12)
        layout.addWidget(self.content)
        self.animation = QPropertyAnimation(self.content, b"maximumHeight", self)
        self.animation.setDuration(160)
        self.animation.setEasingCurve(QEasingCurve.InOutCubic)
        self.animation.finished.connect(self._finish)
        self._finish()

    @property
    def is_expanded(self):
        return self._expanded

    def _toggle(self):
        if self._collapsible:
            self.set_expanded(not self._expanded)

    def set_collapsible(self, value):
        self._collapsible = value
        self.header.setCheckable(value)
        self.header.setChecked(self._expanded)
        self.header.setProperty("collapsible", value)
        self.header.setArrowType((Qt.DownArrow if self._expanded else Qt.RightArrow) if value else Qt.NoArrow)

    def set_summary(self, text):
        self.summary.setText(text)
        self.summary.setVisible(bool(text))

    def set_expanded(self, expanded, *, animate=True):
        expanded = bool(expanded)
        if expanded == self._expanded:
            return
        current = self.content.height() if self.content.isVisible() else 0
        self.animation.stop()
        self._expanded = expanded
        self.header.setChecked(expanded)
        self.header.setArrowType((Qt.DownArrow if expanded else Qt.RightArrow) if self._collapsible else Qt.NoArrow)
        app = QApplication.instance()
        motion = self.isVisible() and not (app and app.property("entrelaReduceMotion"))
        if animate and motion:
            self.content.show()
            self.content.setMaximumHeight(current)
            target = self.content_layout.heightForWidth(self.content.width())
            target = max(target, self.content.sizeHint().height())
            self.animation.setStartValue(current)
            self.animation.setEndValue(target if expanded else 0)
            self.animation.start()
        else:
            self._finish()
        self.expanded_changed.emit(expanded)

    def _finish(self):
        self.content.setVisible(self._expanded)
        self.content.setMaximumHeight(16777215 if self._expanded else 0)
        self.header.setChecked(self._expanded)
        self.header.setArrowType((Qt.DownArrow if self._expanded else Qt.RightArrow) if self._collapsible else Qt.NoArrow)

    def refresh_theme(self):
        app = QApplication.instance()
        if app and app.property("entrelaReduceMotion"):
            self.animation.stop()
            self._finish()
