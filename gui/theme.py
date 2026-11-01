"""
Design system do Entrela.
Fonte única de verdade para cores, tipografia e espaçamento.
"""
from __future__ import annotations
from dataclasses import dataclass


@dataclass(frozen=True)
class Palette:
    # Superfícies
    bg: str = "#080c12"
    bg_elevated: str = "#121214"
    surface: str = "#111923"
    surface_hover: str = "#18181b"
    surface_active: str = "#1f1f23"

    # Bordas
    border: str = "#1e1e22"
    border_strong: str = "#566170"

    # Acento
    primary: str = "#58d6ff"
    primary_hover: str = "#7ee0ff"
    primary_pressed: str = "#3fb8e6"
    primary_muted: str = "#0d2933"
    primary_faint: str = "#0d2933"
    primary_on: str = "#0a0a0b"
    text_on_primary: str = "#0a0a0b"

    # Texto
    text: str = "#e8e8ea"
    text_muted: str = "#8b8b90"
    text_dim: str = "#8995a6"

    # Semânticas
    success: str = "#22c55e"
    success_bg: str = "#0d2818"
    warning: str = "#f59e0b"
    warning_bg: str = "#2a1e05"
    danger: str = "#ef4444"
    danger_bg: str = "#2a0e0c"
    info: str = "#58d6ff"
    info_bg: str = "#0d2933"

    # Paleta quântica (compat)
    q1: str = "#58d6ff"
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


def build_qss() -> str:
    p = PALETTE
    return f"""
* {{ font-family: {FONT_FAMILY}; font-size: 13px; outline: none; }}

QWidget {{ background-color: {p.bg}; color: {p.text}; }}
QLabel#HeroTitle {{ font-size: 32px; font-weight: 600; padding: 12px 0; }}
QLabel#LeadText {{ color: {p.text_muted}; font-size: 14px; padding: 6px 0; }}
QPushButton#HelpButton {{ padding: 0; min-width: 20px; min-height: 20px; }}
QPushButton:focus, QPushButton#NavButton:focus, QPushButton#PrimaryButton:focus {{ border: 2px solid {p.text}; }}
QTabWidget::pane {{ border: 1px solid {p.border}; }}
QTabBar::tab {{ background: {p.surface}; padding: 10px 16px; color: {p.text_muted}; }}
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
    font-size: 11px;
}}

/* ============ SIDEBAR ============ */
QFrame#Sidebar {{
    background-color: {p.bg};
    border-right: 1px solid {p.border};
}}

QLabel#SidebarLogo {{
    color: {p.text};
    font-size: 14px;
    font-weight: 600;
    letter-spacing: 0.3px;
}}

QPushButton#NavButton {{
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
    background-color: {p.surface_active};
    color: {p.text};
}}

/* ============ TOPBAR ============ */
QFrame#Topbar {{
    background-color: {p.bg};
    border-bottom: 1px solid {p.border};
}}

QLabel#TopbarTitle {{
    color: {p.text};
    font-size: 14px;
    font-weight: 600;
}}

QLabel#TopbarBreadcrumb {{
    color: {p.text_dim};
    font-size: 11px;
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
    background-color: {p.surface};
    border: 1px solid {p.border};
    border-radius: {RADIUS.lg}px;
}}

QLabel#SectionTitle {{
    color: {p.text};
    font-size: 14px;
    font-weight: 600;
}}

QLabel#SectionSubtitle {{
    color: {p.text_muted};
    font-size: 11px;
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
    font-size: 11px;
    font-weight: 500;
    letter-spacing: 0.6px;
}}

/* ============ BUTTONS ============ */
QPushButton {{
    background-color: {p.surface};
    color: {p.text};
    border: 1px solid {p.border_strong};
    border-radius: {RADIUS.md}px;
    padding: 7px 14px;
    font-size: 13px;
    font-weight: 500;
    min-height: 20px;
    qproperty-iconSize: 16px 16px;
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
    padding: 8px 16px;
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
    background-color: {p.bg};
    color: {p.text};
    border: 1px solid {p.border_strong};
    border-radius: {RADIUS.sm}px;
    padding: 6px 10px;
    font-size: 13px;
    selection-background-color: {p.primary_faint};
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
    image: none;
    border-left: 3px solid transparent;
    border-right: 3px solid transparent;
    border-bottom: 4px solid {p.text_dim};
    width: 0; height: 0;
}}

QSpinBox::down-arrow, QDoubleSpinBox::down-arrow {{
    image: none;
    border-left: 3px solid transparent;
    border-right: 3px solid transparent;
    border-top: 4px solid {p.text_dim};
    width: 0; height: 0;
}}

QSpinBox::up-arrow:hover, QDoubleSpinBox::up-arrow:hover {{
    border-bottom-color: {p.primary};
}}

QSpinBox::down-arrow:hover, QDoubleSpinBox::down-arrow:hover {{
    border-top-color: {p.primary};
}}

QComboBox::drop-down {{
    border: none;
    width: 20px;
}}

QComboBox::down-arrow {{
    image: none;
    border-left: 3px solid transparent;
    border-right: 3px solid transparent;
    border-top: 4px solid {p.text_dim};
    width: 0; height: 0;
    margin-right: 8px;
}}

QComboBox::down-arrow:hover {{
    border-top-color: {p.primary};
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
    font-size: 11px;
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
QSplitter::handle {{ background: {p.border}; }}
QSplitter::handle:horizontal {{ width: 1px; }}

QStatusBar {{
    background-color: {p.bg};
    color: {p.text_dim};
    border-top: 1px solid {p.border};
    font-size: 11px;
}}

QTableWidget, QTableView {{
    background-color: {p.surface};
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
    padding: 10px 14px;
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 0.4px;
}}

QTableWidget::item {{
    padding: 8px 14px;
    border-bottom: 1px solid {p.border};
}}

QTableWidget::item:selected {{ background-color: {p.surface_active}; }}
QTableWidget::item:focus {{ border: none; }}

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
"""
