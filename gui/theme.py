"""Cores, tipografia e componentes Qt do Entrela."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Palette:
    bg: str = "#181B25"
    bg_elevated: str = "#202432"
    surface: str = "#282D3E"
    surface_hover: str = "#31384B"
    surface_active: str = "#3A435D"
    border: str = "#353D52"
    border_strong: str = "#7180A0"

    primary: str = "#B8C4FF"
    primary_hover: str = "#CAD2FF"
    primary_pressed: str = "#9EAEF2"
    primary_muted: str = "#3D486E"
    primary_faint: str = "#2D3654"
    primary_on: str = "#1B2446"
    text_on_primary: str = "#1B2446"
    action_bg: str = "#B8C4FF"
    action_hover: str = "#CAD2FF"
    action_pressed: str = "#9EAEF2"
    action_on: str = "#1B2446"

    text: str = "#F1F3FB"
    text_muted: str = "#C4CBDD"
    text_dim: str = "#ABB6CF"

    chrome: str = "#121520"
    chrome_border: str = "#30354A"
    chrome_text: str = "#F1F2FE"
    chrome_muted: str = "#A6B1CD"
    chrome_hover: str = "#22283A"
    chrome_selected: str = "#313A58"
    chrome_accent: str = "#B7C6FF"

    success: str = "#7DD4AA"
    success_bg: str = "#1B392F"
    warning: str = "#E6B579"
    warning_bg: str = "#3B2E20"
    danger: str = "#F494AC"
    danger_bg: str = "#432731"
    info: str = "#A0BBFB"
    info_bg: str = "#2A3B5A"

    q1: str = "#9BAEFF"
    q2: str = "#CEA6EA"
    q3: str = "#75D1C4"
    q4: str = "#E7BA83"
    q5: str = "#E69FB3"
    q6: str = "#86C6EF"


@dataclass(frozen=True)
class Spacing:
    xs: int = 4
    sm: int = 8
    md: int = 12
    lg: int = 16
    xl: int = 24
    xxl: int = 32
    xxxl: int = 48


@dataclass(frozen=True)
class Radius:
    sm: int = 6
    md: int = 9
    lg: int = 14
    pill: int = 999


PALETTE = Palette()
SPACING = Spacing()
RADIUS = Radius()

FONT_FAMILY = "Instrument Sans"
FONT_MONO = '"IBM Plex Mono", "Cascadia Mono", Consolas, monospace'


def build_qss(*, density="comfortable") -> str:
    from PySide6.QtGui import QFontDatabase
    from PySide6.QtWidgets import QApplication

    family = FONT_FAMILY
    app = QApplication.instance()
    if app is not None:
        if not app.property("entrelaFontsLoaded"):
            for path in sorted((Path(__file__).parent / "assets" / "fonts").glob("*.ttf")):
                QFontDatabase.addApplicationFont(str(path))
            app.setProperty("entrelaFontsLoaded", True)
        available = set(QFontDatabase.families())
        family = next((name for name in (FONT_FAMILY, "IBM Plex Sans", "Segoe UI", "Noto Sans")
                       if name in available), "sans-serif")
    p = PALETTE
    icons = (Path(__file__).resolve().parent / "assets" / "icons").as_posix()
    pad = {"compact": 5, "comfortable": 8, "spacious": 11}.get(density, 8)
    checkmark = "check-dark.svg" if p.primary_on != "#FFFFFF" else "check-light.svg"
    return f"""
* {{ font-family: "{family}"; font-size: 13px; }}
QWidget {{ color: {p.text}; background: transparent; }}
QMainWindow, QWidget#RootWidget {{ background: {p.chrome}; }}
QDialog, QDockWidget {{ background: {p.bg}; }}
QFrame#Workbench {{
    background: {p.bg}; border: 1px solid {p.chrome_border}; border-radius: 16px;
}}
QStatusBar {{ background: {p.chrome}; color: {p.chrome_muted}; font-size: 11px; }}
QStatusBar QLabel {{ color: {p.chrome_muted}; font-size: 11px; }}
QToolTip {{
    background: {p.bg_elevated}; color: {p.text}; border: 1px solid {p.border_strong};
    border-radius: 6px; padding: 6px 10px; font-size: 12px;
}}

/* Identidade e hierarquia tipográfica */
QLabel#TopbarTitle, QLabel#HeroTitle {{ font-size: 31px; font-weight: 700; }}
QLabel#TopbarBreadcrumb {{ color: {p.text_dim}; font-size: 11px; font-weight: 600; }}
QLabel#PageTitle, QLabel#ResumeTitle {{ font-size: 23px; font-weight: 600; }}
QLabel#WorkspaceSectionTitle {{ font-size: 20px; font-weight: 600; }}
QLabel#SectionTitle, QLabel#PanelTitle {{ font-size: 14px; font-weight: 600; }}
QLabel#ExecutionIdentity, QLabel#SummaryValue {{ font-weight: 600; }}
QLabel#PageSubtitle, QLabel#SectionSubtitle, QLabel#LeadText {{ color: {p.text_muted}; }}
QLabel#Eyebrow, QLabel#FieldLabel {{ color: {p.text_dim}; font-size: 11px; font-weight: 600; }}
QLabel#FieldHint {{ color: {p.text_muted}; font-size: 12px; }}
QLabel#ContextBadge {{ color: {p.primary}; background: {p.primary_faint}; padding: 4px 8px; border-radius: 5px; font-size: 11px; }}
QLabel#StateFormula, QLabel#MetricValue, QLabel#MetricCompact {{
    font-family: {FONT_MONO}; font-weight: 500;
}}
QLabel#StateFormula {{ color: {p.primary}; font-size: 13px; }}
QLabel#MetricValue {{ font-size: 23px; }}
QLabel#MetricCompact {{ font-size: 17px; }}
QLabel#MetricLabel {{ color: {p.text_muted}; font-size: 11px; font-weight: 600; }}
QLabel#MetricUnit {{ color: {p.text_dim}; font-size: 11px; }}

/* Navegação */
QFrame#Sidebar {{ background: {p.chrome}; }}
QLabel#SidebarLogo {{ color: {p.chrome_text}; font-size: 20px; font-weight: 700; }}
QLabel#SidebarMark {{ background: {p.chrome_hover}; border: 1px solid {p.chrome_border}; border-radius: 9px; }}
QPushButton#NavButton, QPushButton#NavGroup, QPushButton#SearchButton, QToolButton#SidebarToggle {{
    color: {p.chrome_muted}; background: transparent; border: 1px solid transparent; border-radius: 8px;
    text-align: left;
}}
QPushButton#NavButton {{ padding: 5px 10px; font-weight: 500; }}
QPushButton#NavButton[compact="true"] {{ padding: 5px 7px; }}
QPushButton#NavGroup {{ padding: 4px 8px; font-size: 10px; font-weight: 600; }}
QPushButton#NavGroup[activeGroup="true"] {{ color: {p.chrome_text}; }}
QPushButton#SearchButton {{ background: {p.chrome_hover}; border-color: {p.chrome_border}; padding: 6px 10px; }}
QPushButton#NavButton:hover, QPushButton#NavGroup:hover, QToolButton#SidebarToggle:hover {{
    background: {p.chrome_hover}; color: {p.chrome_text};
}}
QPushButton#NavButton:checked {{ background: {p.chrome_selected}; color: {p.chrome_text}; font-weight: 600; }}
QPushButton#SearchButton:hover {{ background: {p.chrome_selected}; color: {p.chrome_text}; }}
QPushButton#NavButton:focus, QPushButton#NavGroup:focus, QPushButton#SearchButton:focus,
QToolButton#SidebarToggle:focus {{ border-color: {p.chrome_accent}; }}

/* Superfícies, barras e seções */
QFrame#StudioPanel, QWidget#InspectorPanel, QFrame#EvidencePanel, QFrame#WorkbenchInspector,
QFrame#ProjectCard, QFrame#PlotFrame, QWidget#ParameterWorkspace {{
    background: {p.bg_elevated}; border: 1px solid {p.border}; border-radius: {RADIUS.lg}px;
}}
QFrame#ProjectResume, QFrame#PreparationPlate {{
    background: {p.primary_faint}; border: 1px solid {p.border}; border-radius: {RADIUS.lg}px;
}}
QFrame#Card {{ background: transparent; border: none; }}
QFrame#IdentityCard, QFrame#SectionCard, QFrame#RunMetric {{
    background: transparent; border: none; border-bottom: 1px solid {p.border};
}}
QFrame#SectionCard[inline="true"] {{ border: none; }}
QFrame#MetricTile {{ background: {p.bg_elevated}; border: 1px solid {p.border}; border-radius: {RADIUS.md}px; }}
QFrame#ExecutionBar, QFrame#TransportBar, QFrame#CommandBar {{
    background: transparent; border: none; border-top: 1px solid {p.border};
}}
QLabel#ValidationMessage {{ color: {p.text_muted}; font-size: 12px; }}
QLabel#ValidationMessage[state="error"] {{ color: {p.danger}; }}
QPushButton#ConfigStep {{
    background: transparent; color: {p.text_muted}; border: 1px solid transparent;
    text-align: left; padding: 7px 10px;
}}
QPushButton#ConfigStep:checked {{ background: {p.primary_faint}; color: {p.primary}; font-weight: 600; }}
QPushButton#ConfigStep[invalid="true"] {{ color: {p.danger}; background: {p.danger_bg}; }}
QToolButton#SectionToggle {{ background: transparent; border-color: transparent; padding: 4px 3px; font-weight: 600; }}
QToolButton#SectionToggle:hover {{ color: {p.primary}; background: {p.surface_hover}; }}

/* Botões e menus */
QPushButton, QToolButton {{
    background: {p.bg_elevated}; color: {p.text}; border: 1px solid {p.border}; border-radius: {RADIUS.md}px;
    padding: {max(4, pad - 1)}px 12px; font-weight: 500;
}}
QPushButton:hover, QToolButton:hover {{ background: {p.surface_hover}; }}
QPushButton:pressed, QToolButton:pressed, QToolButton:checked {{ background: {p.surface_active}; }}
QPushButton:disabled, QToolButton:disabled {{ background: {p.bg}; color: {p.text_dim}; border-color: {p.border}; }}
QPushButton:focus, QToolButton:focus, QFrame#Workbench QToolButton#SectionToggle:focus {{ border-color: {p.primary}; }}
QPushButton#PrimaryButton {{
    background: {p.action_bg}; border-color: {p.action_bg}; color: {p.action_on}; font-weight: 600;
    padding: {pad}px 16px;
}}
QPushButton#PrimaryButton:hover {{ background: {p.action_hover}; border-color: {p.action_hover}; }}
QPushButton#PrimaryButton:pressed {{ background: {p.action_pressed}; border-color: {p.action_pressed}; }}
QPushButton#PrimaryButton:focus {{ border: 2px solid {p.text}; }}
QPushButton#PrimaryButton:disabled {{ background: {p.surface}; color: {p.text_dim}; border-color: {p.border}; }}
QPushButton#GhostButton, QToolButton#QuietTool {{
    background: transparent; border-color: transparent; color: {p.primary}; padding: {max(4, pad - 1)}px 8px;
}}
QPushButton#GhostButton:hover, QToolButton#QuietTool:hover {{ background: {p.primary_faint}; }}
QPushButton#GhostButton:focus, QToolButton#QuietTool:focus, QPushButton#ConfigStep:focus {{ border-color: {p.primary}; }}
QPushButton#GhostButton:disabled, QToolButton#QuietTool:disabled {{ color: {p.text_dim}; }}
QPushButton#DangerButton {{ color: {p.danger}; background: {p.danger_bg}; }}
QPushButton#HelpButton {{
    background: transparent; color: {p.primary}; border-color: {p.border};
    border-radius: 10px; padding: 0; min-width: 20px; min-height: 20px;
}}
QPushButton[gateFamily] {{ background: {p.bg_elevated}; padding: 6px 8px; }}
QPushButton[gateFamily="phase"] {{ border-bottom: 2px solid {p.q2}; }}
QPushButton[gateFamily="controlled"] {{ border-bottom: 2px solid {p.q3}; }}
QPushButton[gateFamily="rotation"] {{ border-bottom: 2px solid {p.q1}; }}
QPushButton[gateFamily]:hover {{ background: {p.primary_faint}; }}
QMenu, QComboBox QAbstractItemView {{
    background: {p.bg_elevated}; color: {p.text}; border: 1px solid {p.border_strong};
    border-radius: 8px; padding: 5px; selection-background-color: {p.primary_faint}; selection-color: {p.text};
}}
QMenu::item {{ padding: 7px 24px 7px 12px; border-radius: 5px; }}
QMenu::item:selected {{ background: {p.primary_faint}; color: {p.primary}; }}
QMenu::item:disabled {{ color: {p.text_dim}; }}
QMenu::separator {{ height: 1px; margin: 4px 6px; background: {p.border}; }}

/* Campos e controles */
QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox, QPlainTextEdit, QTextEdit {{
    background: {p.bg_elevated}; color: {p.text}; border: 1px solid {p.border}; border-radius: {RADIUS.md}px;
    padding: {pad}px 10px; selection-background-color: {p.primary_muted}; selection-color: {p.text};
}}
QLineEdit:hover, QSpinBox:hover, QDoubleSpinBox:hover, QComboBox:hover {{ border-color: {p.border_strong}; }}
QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus,
QPlainTextEdit:focus, QTextEdit:focus {{ border-color: {p.primary}; }}
QLineEdit:disabled, QSpinBox:disabled, QDoubleSpinBox:disabled, QComboBox:disabled {{
    background: {p.surface}; color: {p.text_dim};
}}
QLineEdit#DocumentTitle {{
    background: transparent; border: 1px solid transparent; border-bottom-color: {p.border};
    font-size: 17px; font-weight: 600; padding: 5px 4px;
}}
QLineEdit#DocumentTitle:hover {{ background: {p.bg_elevated}; }}
QLineEdit#DocumentTitle:focus {{ background: {p.bg_elevated}; border-color: {p.primary}; }}
QSpinBox, QDoubleSpinBox, QSpinBox QLineEdit, QDoubleSpinBox QLineEdit {{ font-family: {FONT_MONO}; }}
QSpinBox::up-button, QDoubleSpinBox::up-button, QSpinBox::down-button, QDoubleSpinBox::down-button {{
    background: transparent; border: none; width: 18px;
}}
QSpinBox::up-arrow, QDoubleSpinBox::up-arrow {{ image: url("{icons}/chevron-up.svg"); width: 12px; height: 12px; }}
QSpinBox::down-arrow, QDoubleSpinBox::down-arrow {{ image: url("{icons}/chevron-down.svg"); width: 12px; height: 12px; }}
QComboBox::drop-down {{ border: none; width: 22px; }}
QComboBox::down-arrow {{ image: url("{icons}/chevron-down.svg"); width: 14px; height: 14px; }}
QCheckBox {{ spacing: 8px; }}
QCheckBox::indicator {{
    width: 14px; height: 14px; border: 1px solid {p.border_strong}; border-radius: 4px; background: {p.bg_elevated};
}}
QCheckBox::indicator:hover, QCheckBox::indicator:focus {{ border-color: {p.primary}; }}
QCheckBox::indicator:checked {{
    background: {p.primary}; border-color: {p.primary}; image: url("{icons}/{checkmark}");
}}
QSlider::groove:horizontal {{ background: {p.border}; height: 4px; border-radius: 2px; }}
QSlider::sub-page:horizontal {{ background: {p.primary}; border-radius: 2px; }}
QSlider::handle:horizontal {{ background: {p.primary}; width: 14px; margin: -5px 0; border-radius: 7px; }}
QSlider::groove:vertical {{ background: {p.border}; width: 4px; border-radius: 2px; margin: 6px 0; }}
QSlider::handle:vertical {{ background: {p.primary}; height: 14px; margin: 0 -5px; border-radius: 7px; }}
QSlider:focus {{ border: 1px solid {p.primary}; border-radius: 5px; }}
QProgressBar {{ background: {p.surface}; border: none; border-radius: 3px; max-height: 6px; }}
QProgressBar::chunk {{ background: {p.primary}; border-radius: 3px; }}

/* Abas, listas e tabelas */
QTabWidget::pane {{ border: none; }}
QTabBar {{ qproperty-drawBase: false; }}
QTabBar::tab {{
    background: transparent; color: {p.text_muted}; border: 1px solid transparent;
    border-radius: 8px; padding: 7px 12px; margin-right: 3px;
}}
QTabBar::tab:hover {{ background: {p.surface_hover}; }}
QTabBar::tab:selected {{ background: {p.primary_faint}; color: {p.primary}; font-weight: 600; }}
QTabBar::tab:focus {{ border-color: {p.primary}; }}
QTabBar::tab:disabled {{ color: {p.text_dim}; }}
QListView, QTreeView, QTableView {{
    background: {p.bg_elevated}; alternate-background-color: {p.bg}; gridline-color: {p.border};
    selection-background-color: {p.primary_muted}; selection-color: {p.text}; border: 1px solid {p.border}; border-radius: 9px;
}}
QListView::item {{ padding: 7px 10px; }}
QListView::item:selected, QTreeView::item:selected {{ background: {p.primary_faint}; color: {p.primary}; }}
QHeaderView::section {{
    background: {p.surface}; color: {p.text_muted}; padding: {pad}px 10px;
    border: none; border-bottom: 1px solid {p.border}; font-size: 11px; font-weight: 600;
}}
QTableView::item {{ padding: 5px 10px; border-bottom: 1px solid {p.border}; }}
QTableView::item:alternate {{ background: {p.bg}; }}
QTableView::item:selected {{ background: {p.primary_muted}; color: {p.text}; }}
QListView:focus, QTreeView:focus, QTableView:focus {{ border-color: {p.primary}; }}
QListWidget#PreferenceCategories, QListWidget#WorkspaceList {{ background: transparent; border: none; }}
QListWidget#PreferenceCategories::item {{ border-radius: 8px; padding: 9px 11px; }}
QListWidget#WorkspaceList::item {{ border-bottom: 1px solid {p.border}; }}
QListWidget#PreferenceCategories::item:selected {{ color: {p.primary}; background: {p.primary_faint}; }}
QTextBrowser {{
    background: {p.bg_elevated}; border: 1px solid {p.border}; border-radius: {RADIUS.md}px; padding: 16px 20px;
}}
QScrollArea {{ border: none; background: transparent; }}
QScrollBar:vertical {{ background: transparent; width: 8px; margin: 2px; }}
QScrollBar:horizontal {{ background: transparent; height: 8px; margin: 2px; }}
QScrollBar::handle:vertical, QScrollBar::handle:horizontal {{ background: {p.border_strong}; border-radius: 4px; }}
QScrollBar::handle:vertical {{ min-height: 24px; }}
QScrollBar::handle:horizontal {{ min-width: 24px; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ width: 0; }}
QScrollBar::add-page, QScrollBar::sub-page {{ background: transparent; }}
QSplitter::handle {{ background: transparent; }}
QSplitter::handle:hover {{ background: {p.border_strong}; border-radius: 2px; }}
"""
