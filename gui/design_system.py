"""Superfícies e hierarquia do estúdio científico, sem estado de experimento."""
from dataclasses import dataclass
from PySide6.QtWidgets import QApplication, QFrame, QVBoxLayout, QLabel


@dataclass(frozen=True)
class LayoutTokens:
    page_margin: int = 24
    section_gap: int = 16
    control_gap: int = 8
    panel_padding: int = 16
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
    """Hierarquia de plataforma: cabeçalho, comandos, painéis e dados."""
    app = QApplication.instance()
    activity_padding = 12 if app and int(app.property('entrelaFontSize') or 15) >= 20 else 24
    return f'''
QFrame#GlobalHeader {{ background: {p.bg}; border: none; border-bottom: 1px solid {p.border}; }}
QLabel#GlobalBrand {{ color: {p.text}; font-size: 18px; font-weight: 600; }}
QLabel#GlobalProduct {{ color: {p.text_dim}; font-size: 12px; border-left: 1px solid #525252; padding-left: 16px; }}
QLabel#BackendBadge {{ color: #a6c8ff; background: #243a5e; padding: 4px 8px; font-size: 11px; }}
QPushButton#GlobalAction {{ background: transparent; color: {p.text}; border: 1px solid transparent; border-radius: 8px; padding: 8px 12px; }}
QPushButton#GlobalAction:hover {{ background: {p.surface}; }}
QPushButton#GlobalAction:focus {{ border: 2px solid {p.primary}; }}
QFrame#PageHeader {{ background: {p.bg}; border-bottom: 1px solid {p.border}; }}
QLabel#TopbarTitle {{ font-size: 25px; font-weight: 600; }}
QLabel#TopbarBreadcrumb {{ font-size: 13px; color: {p.text_dim}; }}
QWidget#PageSurface {{ background: {p.bg}; }}
QFrame#StudioPanel, QWidget#InspectorPanel, QFrame#EvidencePanel {{ background: {p.bg_elevated}; border: 1px solid {p.border}; border-radius: 8px; }}
QFrame#DocumentHeader {{ background: transparent; border: none; }}
QLineEdit#DocumentTitle {{ background: transparent; border: 1px solid transparent; border-bottom: 1px solid {p.border}; border-radius: 8px; color: {p.text}; font-size: 18px; font-weight: 500; padding: 6px 0; }}
QLineEdit#DocumentTitle:focus {{ background: {p.bg_elevated}; border: 2px solid {p.primary}; padding-left: 8px; }}
QLabel#Eyebrow {{ color: {p.text_muted}; font-size: 11px; font-weight: 500; letter-spacing: 0.5px; }}
QLabel#PanelTitle {{ color: {p.text}; font-size: 15px; font-weight: 600; }}
QLabel#ContextBadge {{ color: {p.primary}; background: {p.primary_faint}; padding: 4px 8px; border-radius: 0; font-size: 11px; }}
QLabel#MetricCompact {{ color: {p.text}; font-size: 19px; font-weight: 500; }}
QFrame#Card {{ background: transparent; border: none; border-radius: 0; }}
QFrame#MetricTile {{ background: {p.bg_elevated}; border: none; border-left: 1px solid {p.border}; border-radius: 0; }}
QFrame#SectionCard {{ background: transparent; border: none; border-bottom: 1px solid {p.border}; border-radius: 0; }}
QFrame#ExecutionBar, QFrame#TransportBar, QFrame#CommandBar {{ background: {p.bg_elevated}; border: none; border-top: 1px solid {p.border}; border-radius: 0; }}
QFrame#Sidebar {{ background: {p.bg}; border-right: 1px solid {p.border}; }}
QPushButton#NavButton {{ color: {p.text_muted}; background: transparent; border: none; border-left: 3px solid transparent; border-radius: 8px; padding: 8px 16px; font-weight: 400; }}
QPushButton#NavButton:checked {{ background: {p.surface}; border-left: 3px solid {p.primary}; color: {p.text}; font-weight: 600; }}
QPushButton#NavButton:hover {{ background: {p.bg_elevated}; color: {p.text}; }}
QPushButton#NavButton[compact="true"] {{ padding: 8px 12px; }}
QPushButton#NavGroup {{ color: {p.text_dim}; font-size: 11px; font-weight: 600; padding: 12px 12px 6px 12px; border-radius: 8px; }}
QToolButton#SidebarToggle {{ border-radius: 8px; }}
QPushButton#NavGroup[activeGroup="true"] {{ color: {p.text}; }}
QPushButton#ConfigStep {{ background: transparent; border: none; border-left: 2px solid transparent; border-radius: 8px; text-align: left; }}
QPushButton#ConfigStep:checked {{ background: {p.primary_faint}; border-left-color: {p.primary}; color: {p.primary}; }}
QPushButton, QToolButton {{ border-radius: 8px; }}
QPushButton#PrimaryButton {{ color: {p.action_on}; background: {p.action_bg}; border: 1px solid {p.action_bg}; border-radius: 10px; padding: 10px 18px; font-weight: 500; }}
QPushButton#PrimaryButton:hover {{ color: {p.action_on}; background: {p.action_hover}; border-color: {p.action_hover}; }}
QPushButton#PrimaryButton:pressed {{ color: {p.action_on}; background: {p.action_pressed}; border-color: {p.action_pressed}; }}
QPushButton#PrimaryButton:disabled {{ background: {p.surface}; color: {p.text_dim}; border-color: {p.border}; }}
QPushButton#GhostButton {{ background: transparent; color: {p.primary}; border: 1px solid transparent; border-radius: 8px; }}
QPushButton#GhostButton:hover {{ background: {p.surface}; color: {p.text}; }}
QPushButton[gateFamily] {{ background: {p.surface}; color: {p.text}; border: 1px solid {p.border}; border-left: 3px solid {p.primary}; border-radius: 10px; font-weight: 500; }}
QPushButton[gateFamily="phase"] {{ border-left-color: {p.q2}; }}
QPushButton[gateFamily="controlled"] {{ border-left-color: {p.q3}; }}
QPushButton[gateFamily="rotation"] {{ border-left-color: {p.q1}; }}
QPushButton[gateFamily]:hover {{ background: {p.surface_hover}; border-color: {p.primary}; }}
QPushButton[gateFamily]:disabled {{ background: {p.bg_elevated}; color: {p.text_dim}; border-color: {p.border}; }}
QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox {{ background: {p.surface}; color: {p.text}; border: 1px solid {p.border_strong}; border-radius: 8px; selection-background-color: {p.primary_muted}; padding: 8px 10px; }}
QLineEdit:hover, QSpinBox:hover, QDoubleSpinBox:hover, QComboBox:hover {{ background: {p.surface_hover}; }}
QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus {{ border: 2px solid {p.primary}; }}
QTabWidget::pane {{ border: none; background: transparent; }}
QTabBar::tab {{ color: {p.text_muted}; background: {p.bg_elevated}; border: none; border-top: 2px solid transparent; border-bottom: 1px solid {p.border}; border-radius: 0; padding: 9px 16px; }}
QTabBar::tab:selected {{ color: {p.text}; font-weight: 600; border-top: 2px solid transparent; border-bottom: 2px solid {p.primary}; background: transparent; }}
QTabBar#ViewTabs::tab {{ padding: 8px 12px; border-radius: 0; }}
QTabBar#ViewTabs::tab:selected {{ background: {p.surface}; color: {p.text}; }}
QTableView, QTreeView, QListView {{ background: {p.bg_elevated}; alternate-background-color: {p.bg}; border: none; border-radius: 0; gridline-color: {p.border}; selection-background-color: {p.primary_muted}; selection-color: {p.text}; }}
QHeaderView::section {{ background: {p.surface}; color: {p.text}; border: none; border-bottom: 1px solid {p.border_strong}; padding: 10px 12px; font-weight: 600; }}
QTableWidget::item, QTableView::item {{ border-bottom: 1px solid {p.border}; padding: 8px 12px; }}
QTableWidget::item:alternate, QTableView::item:alternate {{ background: {p.bg}; }}
QTableWidget::item:selected, QTableView::item:selected {{ background: {p.primary_muted}; color: {p.text}; }}
QSplitter::handle {{ background: transparent; }}
QSplitter::handle:horizontal {{ border-left: 1px solid {p.border}; }}
QSplitter::handle:vertical {{ border-top: 1px solid {p.border}; }}
QSplitter::handle:hover {{ background: {p.primary}; }}
QListWidget#PreferenceCategories {{ background: transparent; border: none; }}
QListWidget#PreferenceCategories::item {{ padding: 12px 14px; margin: 0; border-radius: 0; border-left: 2px solid transparent; }}
QListWidget#PreferenceCategories::item:selected {{ background: {p.surface}; color: {p.text}; border-left-color: {p.primary}; }}
QPushButton:focus, QToolButton:focus, QTableView:focus, QListView:focus {{ border: 2px solid {p.primary}; }}
QPushButton#PrimaryButton:focus {{ border: 2px solid {p.text}; }}

QPushButton#GlobalDestination {{ background: transparent; border: none; border-bottom: 3px solid transparent; padding: 12px 16px; color: {p.text_muted}; border-radius: 0; }}
QPushButton#GlobalDestination:checked {{ color: {p.text}; border-bottom-color: {p.primary}; font-weight: 600; }}
QPushButton#GlobalDestination:hover {{ background: {p.surface}; }}
QPushButton#GlobalDestination:focus {{ border: 2px solid {p.primary}; }}
QTabBar#ActivityTabs::tab {{ border: 1px solid {p.border_strong}; border-radius: 10px; padding: 8px {activity_padding}px; margin-right: 6px; background: {p.bg_elevated}; }}
QTabBar#ActivityTabs::tab:selected {{ background: {p.action_bg}; color: {p.action_on}; border-color: {p.action_bg}; }}
QTabBar#ObservationTabs::tab, QTabBar#ProjectTabs::tab {{ background: transparent; border-top: none; border-bottom: 2px solid transparent; }}
QTabBar#ObservationTabs::tab:selected, QTabBar#ProjectTabs::tab:selected {{ border-bottom-color: {p.primary}; color: {p.text}; }}
QFrame#ProjectCard {{ background: {p.bg_elevated}; border: 1px solid {p.border}; border-radius: 10px; }}
QLabel#ExecutionIdentity {{ color: {p.text}; font-weight: 600; }}
QPushButton#Breadcrumb {{ color: {p.primary}; background: transparent; border: 1px solid transparent; padding: 2px 4px; text-align: left; min-height: 24px; }}
QPushButton#Breadcrumb:focus {{ border: 2px solid {p.primary}; }}
QPushButton#Breadcrumb:hover {{ text-decoration: underline; }}
QPushButton#ConfigStep[invalid="true"] {{ color: {p.danger}; border-left-color: {p.danger}; }}
QWidget#PreparationSteps {{ background: {p.bg_elevated}; border-radius: 10px; }}
'''
