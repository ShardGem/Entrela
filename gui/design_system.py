"""Superfícies e hierarquia do estúdio científico, sem estado de experimento."""
from dataclasses import dataclass
from PySide6.QtWidgets import QFrame, QVBoxLayout, QLabel


@dataclass(frozen=True)
class LayoutTokens:
    page_margin: int = 20
    section_gap: int = 16
    control_gap: int = 12
    panel_padding: int = 18
    inspector_width: int = 380
    handle_width: int = 3


LAYOUT = LayoutTokens()


class Surface(QFrame):
    """Uma superfície de trabalho; não cria caixas para cada campo."""
    def __init__(self, title=None, description=None, *, role='StudioPanel', parent=None):
        super().__init__(parent)
        self.setObjectName(role)
        self._body = QVBoxLayout(self)
        self._body.setContentsMargins(LAYOUT.panel_padding, LAYOUT.section_gap,
                                      LAYOUT.panel_padding, LAYOUT.section_gap)
        self._body.setSpacing(LAYOUT.control_gap)
        if title:
            heading=QLabel(title); heading.setObjectName('PanelTitle'); heading.setWordWrap(True)
            self._body.addWidget(heading)
        if description:
            hint=QLabel(description); hint.setObjectName('FieldHint'); hint.setWordWrap(True)
            self._body.addWidget(hint)

    def body(self):
        return self._body

    def add(self, widget, stretch=0):
        self._body.addWidget(widget, stretch)
        return widget


def studio_qss(p):
    return f'''
/* Sistema visual do estúdio: superfícies, campos e barras com papéis distintos. */
QWidget#PageSurface {{ background: {p.bg}; }}
QFrame#StudioPanel, QWidget#InspectorPanel {{ background: {p.bg_elevated}; border: 1px solid {p.border}; border-radius: 10px; }}
QWidget#InspectorPanel {{ border-radius: 8px; }}
QFrame#DocumentHeader {{ background: transparent; border: none; }}
QLineEdit#DocumentTitle {{ background: transparent; border: 1px solid transparent; border-radius: 6px; color: {p.text}; font-size: 20px; font-weight: 600; padding: 5px 0; }}
QLineEdit#DocumentTitle:focus {{ background: {p.bg_elevated}; border-color: {p.primary}; padding-left: 8px; }}
QLabel#Eyebrow {{ color: {p.primary}; font-size: 11px; font-weight: 600; letter-spacing: 1px; }}
QLabel#PanelTitle {{ color: {p.text}; font-size: 15px; font-weight: 600; }}
QLabel#ContextBadge {{ color: {p.primary}; background: {p.primary_faint}; padding: 4px 9px; border-radius: 5px; font-size: 11px; }}
QFrame#Card {{ background: transparent; border: none; border-radius: 0; }}
QFrame#MetricTile {{ background: transparent; border: none; border-left: 2px solid {p.border}; border-radius: 0; }}
QFrame#SectionCard {{ background: transparent; border: none; border-bottom: 1px solid {p.border}; border-radius: 0; }}
QFrame#ExecutionBar, QFrame#TransportBar {{ background: {p.bg_elevated}; border: none; border-top: 1px solid {p.border}; border-radius: 0; }}
QFrame#Sidebar {{ background: {p.bg_elevated}; border-right: 1px solid {p.border}; }}
QFrame#Topbar {{ background: {p.bg}; border-bottom: none; }}
QLabel#TopbarTitle {{ font-size: 23px; font-weight: 600; }}
QLabel#TopbarBreadcrumb {{ font-size: 11px; color: {p.text_dim}; }}
QPushButton#NavButton {{ border-left: 3px solid transparent; border-radius: 6px; }}
QPushButton#NavButton:checked {{ background: {p.primary_faint}; border-left-color: {p.primary}; color: {p.primary}; }}
QPushButton#ConfigStep {{ background: transparent; border: none; border-radius: 5px; text-align: left; }}
QPushButton#ConfigStep:checked {{ background: {p.primary_faint}; color: {p.primary}; }}
QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox {{ background: {p.surface}; border: 1px solid {p.border}; border-radius: 6px; selection-background-color: {p.primary_muted}; }}
QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus {{ border-color: {p.primary}; }}
QTabWidget::pane {{ border: none; background: transparent; }}
QTabBar::tab {{ color: {p.text_muted}; background: transparent; border: none; border-bottom: 2px solid transparent; padding: 10px 14px; }}
QTabBar::tab:selected {{ color: {p.primary}; border-bottom-color: {p.primary}; background: transparent; }}
QTabBar#ViewTabs::tab {{ padding: 7px 12px; border: none; border-radius: 5px; }}
QTabBar#ViewTabs::tab:selected {{ background: {p.primary_faint}; color: {p.primary}; }}
QTableView, QTreeView, QListView {{ background: {p.bg_elevated}; alternate-background-color: {p.bg}; border: none; border-radius: 7px; gridline-color: {p.border}; selection-background-color: {p.primary_muted}; selection-color: {p.text}; }}
QHeaderView::section {{ background: {p.bg_elevated}; color: {p.text_dim}; border: none; border-bottom: 1px solid {p.border}; padding: 10px 12px; font-weight: 500; }}
QSplitter::handle {{ background: transparent; }}
QSplitter::handle:hover {{ background: {p.border_strong}; }}
QListWidget#PreferenceCategories {{ background: transparent; border: none; }}
QListWidget#PreferenceCategories::item {{ padding: 12px 14px; margin: 2px 0; border-radius: 6px; }}
QListWidget#PreferenceCategories::item:selected {{ background: {p.primary_faint}; color: {p.primary}; }}
QPushButton:focus, QToolButton:focus, QTableView:focus, QListView:focus {{ border: 2px solid {p.text}; }}
'''
