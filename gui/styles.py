DARK_STYLE = """
QMainWindow {
    background-color: #1e1e2e;
    color: #cdd6f4;
}
QTabWidget::pane {
    border: 1px solid #45475a;
    background: #1e1e2e;
}
QTabBar::tab {
    background: #313244;
    color: #cdd6f4;
    padding: 8px 16px;
    margin-right: 2px;
    border-top-left-radius: 4px;
    border-top-right-radius: 4px;
}
QTabBar::tab:selected {
    background: #45475a;
    font-weight: bold;
}
QGroupBox {
    border: 1px solid #45475a;
    border-radius: 6px;
    margin-top: 10px;
    padding-top: 16px;
    color: #cdd6f4;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 5px;
}
QPushButton {
    background-color: #89b4fa;
    color: #1e1e2e;
    border: none;
    border-radius: 6px;
    padding: 8px 16px;
    font-weight: bold;
}
QPushButton:hover {
    background-color: #74c7ec;
}
QPushButton:pressed {
    background-color: #89dceb;
}
QDoubleSpinBox, QSpinBox, QComboBox {
    background: #313244;
    color: #cdd6f4;
    border: 1px solid #45475a;
    border-radius: 4px;
    padding: 4px;
}
QLabel {
    color: #cdd6f4;
}
QProgressBar {
    background: #313244;
    border: 1px solid #45475a;
    border-radius: 4px;
    text-align: center;
    color: #cdd6f4;
}
QProgressBar::chunk {
    background: #89b4fa;
    border-radius: 3px;
}
"""

QUANTUM_DARK = """
QMainWindow {
    background-color: #0d1117;
    color: #c9d1d9;
    font-family: "Segoe UI", "Roboto", sans-serif;
}
QTabWidget::pane {
    border: 1px solid #30363d;
    background: #0d1117;
}
QTabBar::tab {
    background: #161b22;
    color: #8b949e;
    padding: 8px 20px;
    margin-right: 2px;
    border-top-left-radius: 4px;
    border-top-right-radius: 4px;
}
QTabBar::tab:selected {
    background: #21262d;
    color: #f0f6fc;
    font-weight: bold;
}
QGroupBox {
    border: 1px solid #30363d;
    border-radius: 6px;
    margin-top: 10px;
    padding-top: 16px;
    color: #c9d1d9;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 5px;
}
QPushButton {
    background-color: #238636;
    color: white;
    border: 1px solid #2ea043;
    border-radius: 6px;
    padding: 8px 16px;
    font-weight: bold;
}
QPushButton:hover {
    background-color: #2ea043;
}
QPushButton:pressed {
    background-color: #3fb950;
}
QPushButton:disabled {
    background-color: #484f58;
    border-color: #484f58;
    color: #8b949e;
}
QDoubleSpinBox, QSpinBox, QComboBox {
    background: #0d1117;
    color: #c9d1d9;
    border: 1px solid #30363d;
    border-radius: 4px;
    padding: 4px;
}
QLabel {
    color: #c9d1d9;
}
QProgressBar {
    background: #161b22;
    border: 1px solid #30363d;
    border-radius: 4px;
    text-align: center;
    color: #c9d1d9;
}
QProgressBar::chunk {
    background: #238636;
    border-radius: 3px;
}
QSlider::groove:horizontal {
    height: 6px;
    background: #30363d;
    border-radius: 3px;
}
QSlider::handle:horizontal {
    background: #238636;
    width: 14px;
    margin: -4px 0;
    border-radius: 7px;
}
QStatusBar {
    background: #161b22;
    color: #8b949e;
}
QToolTip {
    background: #21262d;
    color: #c9d1d9;
    border: 1px solid #30363d;
}
"""

QUANTUM_LAB = """
QMainWindow {
    background-color: #0a0e14;
    color: #bfc7d5;
    font-family: "Consolas", "Monaco", "Courier New", monospace;
}
QTabWidget::pane {
    border: 1px solid #1a1f2b;
    background: #0a0e14;
}
QTabBar::tab {
    background: #12171f;
    color: #6c7a8f;
    padding: 6px 16px;
    margin-right: 2px;
    border-top-left-radius: 3px;
    border-top-right-radius: 3px;
    font-size: 12px;
}
QTabBar::tab:selected {
    background: #1a1f2b;
    color: #e6e9ef;
    font-weight: bold;
}
QGroupBox {
    border: 1px solid #1a1f2b;
    border-radius: 4px;
    margin-top: 8px;
    padding-top: 14px;
    color: #bfc7d5;
    font-size: 12px;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 4px;
    color: #7ec8e3;
}
QPushButton {
    background-color: #1a3a4a;
    color: #7ec8e3;
    border: 1px solid #2a5a6a;
    border-radius: 3px;
    padding: 6px 14px;
    font-size: 12px;
}
QPushButton:hover {
    background-color: #2a4a5a;
    border-color: #7ec8e3;
}
QPushButton:pressed {
    background-color: #1a2a3a;
}
QPushButton:disabled {
    background-color: #151a22;
    border-color: #1a1f2b;
    color: #3a4a5a;
}
QDoubleSpinBox, QSpinBox, QComboBox {
    background: #0f1419;
    color: #bfc7d5;
    border: 1px solid #1a1f2b;
    border-radius: 3px;
    padding: 3px 6px;
    font-size: 12px;
}
QLabel {
    color: #bfc7d5;
    font-size: 12px;
}
QProgressBar {
    background: #0f1419;
    border: 1px solid #1a1f2b;
    border-radius: 3px;
    text-align: center;
    color: #bfc7d5;
    font-size: 11px;
}
QProgressBar::chunk {
    background: #7ec8e3;
    border-radius: 2px;
}
QSlider::groove:horizontal {
    height: 4px;
    background: #1a1f2b;
    border-radius: 2px;
}
QSlider::handle:horizontal {
    background: #7ec8e3;
    width: 12px;
    margin: -4px 0;
    border-radius: 6px;
}
QTextEdit, QPlainTextEdit {
    background: #0f1419;
    color: #bfc7d5;
    border: 1px solid #1a1f2b;
    border-radius: 3px;
    font-family: "Consolas", monospace;
    font-size: 11px;
}
QTableWidget {
    background: #0f1419;
    color: #bfc7d5;
    border: 1px solid #1a1f2b;
    gridline-color: #1a1f2b;
    font-size: 11px;
}
QTableWidget::item:selected {
    background: #1a3a4a;
}
QHeaderView::section {
    background: #12171f;
    color: #7ec8e3;
    border: 1px solid #1a1f2b;
    padding: 4px;
    font-size: 11px;
}
QSplitter::handle {
    background: #1a1f2b;
    width: 2px;
}
QScrollBar:vertical {
    background: #0a0e14;
    width: 8px;
}
QScrollBar::handle:vertical {
    background: #1a1f2b;
    border-radius: 4px;
    min-height: 20px;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}
"""

QUANTUM_LIGHT = """
QMainWindow { background-color: #ffffff; color: #1e1e2e; }
QTabWidget::pane { border: 1px solid #d0d7de; background: #ffffff; }
QTabBar::tab { background: #f6f8fa; color: #24292f; padding: 8px 16px; }
QTabBar::tab:selected { background: #ffffff; font-weight: bold; }
QGroupBox { border: 1px solid #d0d7de; color: #1e1e2e; }
QPushButton { background: #ddf4ff; color: #0969da; border: 1px solid #54aeff; }
QPushButton:hover { background: #b6e3ff; }
QDoubleSpinBox, QSpinBox, QComboBox { background: #ffffff; border: 1px solid #d0d7de; color: #1e1e2e; }
QLabel { color: #1e1e2e; }
"""

LIGHT_STYLE = """
QMainWindow { background-color: #f5f5f5; color: #333333; }
QTabWidget::pane { border: 1px solid #cccccc; background: #ffffff; }
QTabBar::tab { background: #e0e0e0; color: #333333; padding: 8px 16px; margin-right: 2px; border-radius: 4px; }
QTabBar::tab:selected { background: #ffffff; font-weight: bold; }
QGroupBox { border: 1px solid #cccccc; border-radius: 6px; margin-top: 10px; padding-top: 16px; color: #333333; }
QPushButton { background-color: #0078d4; color: white; border: none; border-radius: 6px; padding: 8px 16px; font-weight: bold; }
QPushButton:hover { background-color: #005a9e; }
QPushButton:pressed { background-color: #004578; }
QDoubleSpinBox, QSpinBox, QComboBox { background: white; color: #333333; border: 1px solid #cccccc; border-radius: 4px; padding: 4px; }
QLabel { color: #333333; }
QProgressBar { background: #e0e0e0; border: 1px solid #cccccc; border-radius: 4px; text-align: center; }
QProgressBar::chunk { background: #0078d4; border-radius: 3px; }
"""
