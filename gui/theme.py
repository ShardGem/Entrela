"""
Design system do Entrela.
Fonte única de verdade para cores, tipografia e espaçamento.
"""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Palette:
    # Superfícies
    bg: str = "#12171e"
    bg_elevated: str = "#181f28"
    surface: str = "#202a36"
    surface_hover: str = "#293644"
    surface_active: str = "#304451"

    # Bordas
    border: str = "#2e3b4b"
    border_strong: str = "#62758a"

    # Acento
    primary: str = "#7ad7dd"
    primary_hover: str = "#a3e6e9"
    primary_pressed: str = "#59b9c3"
    primary_muted: str = "#1b3940"
    primary_faint: str = "#1b3940"
    primary_on: str = "#0a0a0b"
    text_on_primary: str = "#0a0a0b"

    # Texto
    text: str = "#e9eff6"
    text_muted: str = "#b0bfd0"
    text_dim: str = "#a2b4c7"

    # Semânticas
    success: str = "#4ade80"
    success_bg: str = "#0d2818"
    warning: str = "#f59e0b"
    warning_bg: str = "#2a1e05"
    danger: str = "#fb7185"
    danger_bg: str = "#2a0e0c"
    info: str = "#7ad7dd"
    info_bg: str = "#1b3940"

    # Paleta quântica (compat)
    q1: str = "#7ad7dd"
    q2: str = "#a78bfa"
    q3: str = "#22c55e"
    q4: str = "#f59e0b"
    q5: str = "#ef4444"
    q6: str = "#58a6ff"


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
    md: int = 8
    lg: int = 12
    pill: int = 999


PALETTE = Palette()
SPACING = Spacing()
RADIUS = Radius()

FONT_FAMILY = '"Inter", "Segoe UI", "SF Pro Text", system-ui, sans-serif'
FONT_MONO = '"JetBrains Mono", "Cascadia Code", "Consolas", monospace'


def build_qss(*, density="comfortable") -> str:
    from PySide6.QtWidgets import QApplication
    from PySide6.QtGui import QFontDatabase
    family = FONT_FAMILY
    if QApplication.instance() is not None:
        available = set(QFontDatabase.families())
        chosen = next((name for name in ("Inter", "Segoe UI", "Noto Sans", "DejaVu Sans") if name in available), None)
        if chosen:
            family = '"' + chosen + '"'
    p = PALETTE
    icons = (Path(__file__).resolve().parent / 'assets' / 'icons').as_posix()
    pad = {"compact": 5, "comfortable": 8, "spacious": 11}.get(density, 8)
    return f"""
* {{ font-family: {family}; font-size: 13px; outline: none; }}

QWidget {{ background-color: transparent; color: {p.text}; }}
QWidget#PageSurface, QDialog, QDockWidget, QStackedWidget {{ background-color: {p.bg}; }}
QLabel#HeroTitle {{ font-size: 32px; font-weight: 600; padding: 12px 0; }}
QLabel#LeadText {{ color: {p.text_muted}; font-size: 14px; padding: 6px 0; }}
QPushButton#HelpButton {{ padding: 0; min-width: 20px; min-height: 20px; }}
QPushButton:focus, QPushButton#NavButton:focus, QPushButton#PrimaryButton:focus {{ border: 2px solid {p.text}; }}
QTabWidget::pane {{ border: none; }}
QTabWidget#WorkbenchTabs::pane {{ border: none; }}
QTabBar {{ qproperty-drawBase: false; }}
QTabBar::tab {{ background: transparent; padding: 10px 16px; color: {p.text_muted}; }}
QTabBar::tab:hover {{ background: {p.surface_hover}; }}
QTabBar::tab:selected {{ color: {p.primary}; border-bottom: 2px solid {p.primary}; }}
QListWidget {{ background: {p.surface}; border: 1px solid {p.border}; padding: 8px; }}
QListWidget::item {{ padding: 10px; }}
QListWidget::item:selected {{ background: {p.primary_muted}; color: {p.primary}; }}
QSlider {{ background: transparent; }}
QSlider::groove:vertical {{ background: {p.border_strong}; width: 6px; border-radius: 3px; margin: 6px 0; }}
QSlider::handle:vertical {{ background: {p.primary}; height: 16px; margin: 0 -6px; border-radius: 5px; border: 1px solid {p.primary_hover}; }}
QSlider::add-page:vertical {{ background: {p.primary}; border-radius: 3px; }}
QToolButton {{ color: {p.text}; background: {p.surface}; border: 1px solid {p.border_strong}; border-radius: 6px; padding: 6px; }}
QToolButton:focus {{ border: 2px solid {p.primary}; }}
QSlider::groove:horizontal {{ background: {p.border_strong}; height: 4px; }}
QSlider::handle:horizontal {{ background: {p.primary}; width: 14px; margin: -5px 0; border-radius: 7px; }}

QMainWindow, QWidget#RootWidget {{
    background-color: {p.bg};
    color: {p.text};
}}

QToolTip {{
    background-color: {p.surface_active};
    color: {p.text};
    border: 1px solid {p.border_strong};
    border-radius: {RADIUS.sm}px;
    padding: 6px 10px;
    font-size: 12px;
}}

/* ============ SIDEBAR ============ */
QFrame#Sidebar {{
    background-color: {p.bg};
    border-right: 1px solid {p.border};
}}

QLabel#SidebarLogo {{
    color: {p.text};
    font-size: 20px;
    font-weight: 600;
    letter-spacing: 0.3px;
}}

QPushButton#NavGroup {{
    background: transparent; color: {p.text}; border: none; qproperty-iconSize: 24px 24px;
    padding: 6px 10px; text-align: left; font-weight: 600; font-size: 13px;
}}
QPushButton#NavGroup:hover {{ background: {p.surface}; }}
QPushButton#NavGroup[compact="true"] {{ padding: 6px; text-align: left; }}
QPushButton#NavGroup[activeGroup="true"] {{ color: {p.primary}; background: {p.primary_faint}; }}
QToolButton#SidebarToggle {{ background: transparent; border: none; border-radius: 4px; padding: 4px; color: {p.text_muted}; font-size: 12px; }}
QToolButton#SidebarToggle:hover {{ background: {p.surface_hover}; color: {p.text}; }}
QToolButton#SidebarToggle:focus {{ border: 1px solid {p.primary}; }}
QPushButton#NavButton[compact="true"] {{ padding: 7px 6px; text-align: left; }}
QPushButton#NavButton {{
    qproperty-iconSize: 22px 22px;
    background: transparent;
    color: {p.text_muted};
    border: none;
    border-radius: {RADIUS.md}px;
    padding: 8px 10px;
    text-align: left;
    font-size: 13px;
    font-weight: 500;
    min-height: 22px;
}}

QPushButton#NavButton:hover {{
    background-color: {p.surface};
    color: {p.text};
}}

QPushButton#NavButton:checked {{
    background-color: {p.primary_muted};
    color: {p.primary};
    border-left: 3px solid {p.primary};
}}

/* ============ TOPBAR ============ */
QFrame#Topbar {{
    background-color: {p.bg};
    border-bottom: 1px solid {p.border};
}}

QLabel#TopbarTitle {{
    color: {p.text};
    font-size: 18px;
    font-weight: 600;
}}

QLabel#TopbarBreadcrumb {{
    color: {p.text_dim};
    font-size: 12px;
    font-weight: 500;
    letter-spacing: 0.4px;
}}

/* ============ PAGE ============ */
QLabel#PageTitle {{
    color: {p.text};
    font-size: 22px;
    font-weight: 600;
    letter-spacing: -0.3px;
}}

QLabel#PageSubtitle {{
    color: {p.text_muted};
    font-size: 13px;
}}

/* ============ CARD ============ */
QFrame#Card {{
    background-color: {p.bg_elevated};
    border: none;
    border-radius: {RADIUS.md}px;
}}

QFrame#SectionCard {{
    background-color: {p.bg_elevated}; border: none; border-radius: {RADIUS.md}px;
}}
QFrame#IdentityCard {{
    background: transparent; border: none; border-bottom: 1px solid {p.border}; border-radius: 0;
}}
QToolButton#SectionToggle {{
    background: transparent; border: none; text-align: left; font-weight: 600; font-size: 14px;
    padding: 4px 0; min-height: 24px;
}}
QToolButton#SectionToggle:hover {{ color: {p.primary}; }}
QToolButton#SectionToggle:focus {{ border: 1px solid {p.primary}; }}
QPushButton#ConfigStep {{ background: {p.bg_elevated}; color: {p.text_muted}; border: 1px solid {p.border}; padding: 6px 10px; }}
QPushButton#ConfigStep:checked {{ color: {p.primary}; border-color: {p.primary}; background: {p.primary_faint}; }}
QPushButton#ConfigStep:hover {{ color: {p.text}; background: {p.surface_hover}; }}
QLabel#FieldHint {{ color: {p.text_muted}; font-size: 12px; }}
QLabel#SummaryValue {{ color: {p.text}; font-size: 13px; font-weight: 500; }}
QLabel#StateFormula {{ color: {p.primary}; font-size: 14px; font-weight: 500; padding: 2px 0; }}
QLabel#ValidationMessage {{ color: {p.text_muted}; font-size: 12px; }}
QLabel#ValidationMessage[state="error"] {{ color: {p.danger}; }}
QFrame#ExecutionBar {{ background: {p.bg_elevated}; border-top: 1px solid {p.border}; }}
QFrame#ExecutionStatus {{ background: transparent; border: none; }}
QFrame#ExecutionStatus QProgressBar {{ max-height: 6px; border: none; background: {p.border}; }}

QLabel#SectionTitle {{
    color: {p.text};
    font-size: 14px;
    font-weight: 600;
}}

QLabel#SectionSubtitle {{
    color: {p.text_muted};
    font-size: 12px;
}}

QLabel#MetricValue {{
    color: {p.text};
    font-size: 26px;
    font-weight: 600;
    font-family: {FONT_MONO};
    letter-spacing: -0.5px;
}}

QLabel#MetricLabel {{
    color: {p.text_dim};
    font-size: 12px;
    font-weight: 500;
    letter-spacing: 0.6px;
}}

/* ============ BUTTONS ============ */
QPushButton {{
    background-color: {p.surface};
    color: {p.text};
    border: 1px solid {p.border_strong};
    border-radius: {RADIUS.md}px;
    padding: {max(4, pad - 1)}px 14px;
    font-size: 13px;
    font-weight: 500;
    min-height: 20px;
    qproperty-iconSize: 20px 20px;
}}

QPushButton:hover {{
    background-color: {p.surface_hover};
    border-color: {p.text_dim};
}}

QPushButton:pressed {{
    background-color: {p.surface_active};
}}

QPushButton:disabled {{
    color: {p.text_dim};
    border-color: {p.border};
    background-color: {p.bg};
}}

QPushButton#PrimaryButton {{
    background-color: {p.primary};
    color: {p.primary_on};
    border: none;
    font-weight: 600;
    padding: {pad}px 16px;
}}

QPushButton#PrimaryButton:hover {{
    background-color: {p.primary_hover};
}}

QPushButton#PrimaryButton:pressed {{
    background-color: {p.primary_pressed};
}}

QPushButton#PrimaryButton:disabled {{
    background-color: {p.primary_faint};
    color: {p.text_dim};
}}

QPushButton#GhostButton {{
    background: transparent;
    border: none;
    color: {p.text_muted};
    padding: 6px 8px;
}}

QPushButton#GhostButton:hover {{
    background-color: {p.surface};
    color: {p.text};
}}

QPushButton#DangerButton {{
    background: transparent;
    color: {p.danger};
    border: 1px solid {p.danger};
}}

QPushButton#DangerButton:hover {{
    background-color: {p.danger_bg};
}}

/* ============ INPUTS ============ */
QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox, QPlainTextEdit, QTextEdit {{
    background-color: {p.bg_elevated};
    color: {p.text};
    border: 1px solid {p.border_strong};
    border-radius: {RADIUS.sm}px;
    padding: {max(4, pad - 2)}px 10px;
    font-size: 13px;
    selection-background-color: {p.primary_faint};
}}
QLineEdit:disabled, QSpinBox:disabled, QDoubleSpinBox:disabled, QComboBox:disabled {{
    background-color: {p.surface}; color: {p.text_dim}; border-color: {p.border};
}}

QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus,
QComboBox:focus, QPlainTextEdit:focus, QTextEdit:focus {{
    border-color: {p.primary};
}}

QSpinBox::up-button, QDoubleSpinBox::up-button,
QSpinBox::down-button, QDoubleSpinBox::down-button {{
    background: transparent;
    border: none;
    width: 16px;
}}

QSpinBox::up-arrow, QDoubleSpinBox::up-arrow {{
    image: url("{icons}/chevron-up.svg");
    width: 12px; height: 12px;
}}

QSpinBox::down-arrow, QDoubleSpinBox::down-arrow {{
    image: url("{icons}/chevron-down.svg");
    width: 12px; height: 12px;
}}

QComboBox::drop-down {{
    border: none;
    width: 20px;
}}

QComboBox::down-arrow {{
    image: url("{icons}/chevron-down.svg");
    width: 14px; height: 14px;
    margin-right: 8px;
}}

QComboBox QAbstractItemView {{
    background-color: {p.surface};
    color: {p.text};
    border: 1px solid {p.border_strong};
    border-radius: {RADIUS.sm}px;
    padding: 4px;
    selection-background-color: {p.surface_active};
    outline: none;
}}

QCheckBox {{ color: {p.text}; background: transparent; spacing: 8px; }}

QCheckBox::indicator {{
    width: 14px; height: 14px;
    border: 1px solid {p.border_strong};
    border-radius: 3px;
    background-color: {p.bg};
}}

QCheckBox::indicator:hover {{ border-color: {p.primary}; }}

QCheckBox::indicator:checked {{
    background-color: {p.primary};
    border-color: {p.primary};
}}

QLabel {{ color: {p.text}; background: transparent; }}

QLabel#FieldLabel {{
    color: {p.text_muted};
    font-size: 12px;
    font-weight: 500;
}}

QLabel#HelpIcon {{
    color: {p.text_dim};
    font-size: 10px;
    font-weight: 700;
    border: 1px solid {p.border_strong};
    border-radius: 8px;
    min-width: 16px; max-width: 16px;
    min-height: 16px; max-height: 16px;
    qproperty-alignment: AlignCenter;
}}

QLabel#HelpIcon:hover {{
    color: {p.primary};
    border-color: {p.primary};
}}

/* ============ SCROLLBARS ============ */
QScrollArea {{ background: transparent; border: none; }}

QScrollBar:vertical {{
    background: transparent;
    width: 8px;
    margin: 2px;
}}

QScrollBar::handle:vertical {{
    background: {p.border_strong};
    border-radius: 4px;
    min-height: 30px;
}}

QScrollBar::handle:vertical:hover {{ background: {p.text_dim}; }}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}

QScrollBar:horizontal {{
    background: transparent;
    height: 8px;
    margin: 2px;
}}

QScrollBar::handle:horizontal {{
    background: {p.border_strong};
    border-radius: 4px;
    min-width: 30px;
}}

QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ width: 0; }}

/* ============ MISC ============ */
QSplitter::handle {{ background: {p.bg}; border: none; margin: 1px; }}
QSplitter::handle:hover {{ background: {p.border_strong}; border-radius: 2px; }}
QSplitter::handle:horizontal {{ width: 5px; }}
QSplitter::handle:vertical {{ height: 5px; }}

QStatusBar {{
    background-color: {p.bg};
    color: {p.text_dim};
    border-top: 1px solid {p.border};
    font-size: 12px;
}}

QTableWidget, QTableView {{
    background-color: {p.surface};
    alternate-background-color: {p.surface_hover};
    color: {p.text};
    border: 1px solid {p.border};
    border-radius: {RADIUS.md}px;
    gridline-color: transparent;
    selection-background-color: {p.surface_active};
    selection-color: {p.text};
    outline: none;
}}

QHeaderView::section {{
    background-color: {p.surface};
    color: {p.text_dim};
    border: none;
    border-bottom: 1px solid {p.border};
    padding: {pad + 2}px 14px;
    font-size: 12px;
    font-weight: 600;
    letter-spacing: 0.4px;
}}

QTableWidget::item, QTableView::item {{
    padding: 8px 14px;
    border-bottom: 1px solid {p.border};
}}

QTableWidget::item:alternate, QTableView::item:alternate {{ background-color: {p.surface_hover}; color: {p.text}; }}
QTableWidget::item:selected, QTableView::item:selected {{ background-color: {p.surface_active}; color: {p.text}; }}
QTableWidget::item:focus, QTableView::item:focus {{ border: none; }}

QTextBrowser {{
    background-color: {p.surface};
    border: 1px solid {p.border};
    border-radius: {RADIUS.md}px;
    padding: 20px 28px;
    color: {p.text};
    selection-background-color: {p.primary_faint};
}}

QProgressBar {{
    background-color: {p.bg};
    border: 1px solid {p.border};
    border-radius: 3px;
    max-height: 6px;
}}

QProgressBar::chunk {{
    background-color: {p.primary};
    border-radius: 2px;
}}

/* Após os estilos específicos para o foco não ser ocultado por eles. */
QPushButton:focus, QPushButton#PrimaryButton:focus, QPushButton#GhostButton:focus,
QPushButton#SecondaryButton:focus, QPushButton#NavButton:focus,
QPushButton#NavGroup:focus, QPushButton#ConfigStep:focus {{ border: 2px solid {p.text}; }}
"""
