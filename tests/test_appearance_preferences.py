from PySide6.QtCore import Qt
from PySide6.QtTest import QSignalSpy
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QTableWidget, QTableWidgetItem, QTextBrowser
from gui.pages.settings import SettingsPage
from gui.controllers.appearance import apply_appearance, resolve_theme
from gui.theme import PALETTE
from gui.splash import SplashScreen
from gui.branding import application_icon


def test_settings_restore_is_atomic_and_validates_stale_values(qt_app):
    settings = SettingsPage()
    changed = QSignalSpy(settings.appearance_changed)
    settings.apply_values({'theme': 'auto', 'accent': 'violet', 'font_size': '18', 'density': 'spacious', 'reduce_motion': 'true', 'export_dpi': 450})
    values = settings.collect_values()
    assert values['theme'] == 'auto' and values['accent'] == 'violet'
    assert values['font_size'] == 18 and values['export_dpi'] == 450
    assert values['reduce_motion'] is True
    assert changed.count() == 0
    settings.apply_values({'theme': 'removed-theme', 'font_size': 'invalid'})
    assert settings.collect_values()['theme'] == SettingsPage.DEFAULTS['theme']
    assert settings.font_size.value() == 15
    settings.close()


def test_live_appearance_roundtrip_has_no_accumulated_typographic_scaling(qt_app):
    window = QWidget()
    layout = QVBoxLayout(window)
    label = QLabel('Dados científicos')
    label.setStyleSheet('font-size: 13px; color: #58d6ff;')
    layout.addWidget(label)
    try:
        apply_appearance(window, 'light', 18, accent='violet', density='compact', reduce_motion=True, high_contrast=True)
        assert qt_app.property('entrelaReduceMotion') is True
        assert qt_app.property('entrelaDensity') == 'compact'
        assert PALETTE.primary == '#7340b6'
        assert 'font-size: 18px' in label.styleSheet()
        apply_appearance(window, 'dark', 15)
        assert 'font-size: 15px' in label.styleSheet()
        assert PALETTE.primary == '#7ad7dd'
        assert resolve_theme('auto') in ('dark', 'light')
    finally:
        apply_appearance(window)
        window.close()


def test_splash_budget_counts_initialization_and_stops_on_close(qt_app):
    splash = SplashScreen()
    splash.show()
    qt_app.processEvents()
    assert 0 < splash.remaining_ms() <= 3000
    # Simulate a long initialization without sleeping through startup.
    splash._elapsed = type('Elapsed', (), {'isValid': lambda self: True, 'elapsed': lambda self: 3200})()
    window = QWidget()
    splash.finish_after_minimum(window)
    qt_app.processEvents()
    assert window.isVisible()
    assert not splash.isVisible()
    assert not splash._completion_timer.isActive()
    assert not application_icon().isNull()
    assert not application_icon().pixmap(16, 16).isNull()
    window.close()


def test_compact_group_hierarchy_and_motion_preference(window, qt_app):
    from tests.qt_helpers import wait_until
    sidebar = window.sidebar
    sidebar.set_compact(True)
    assert 'Investigação' in sidebar.group_buttons['research'].text()
    assert all(not body.isHidden() for body in sidebar.group_bodies.values())
    assert 'varreduras' in sidebar.buttons['analysis'].toolTip()
    sidebar.group_buttons['research'].click()
    wait_until(lambda: sidebar.group_bodies['research'].isHidden())
    assert not sidebar.group_bodies['learning'].isHidden()
    qt_app.setProperty('entrelaReduceMotion', True)
    sidebar.group_buttons['research'].click()
    assert not sidebar.group_bodies['research'].isHidden()
    sidebar.group_buttons['learning'].click()
    assert sidebar.group_bodies['learning'].isHidden()
    assert not sidebar.group_bodies['research'].isHidden()
    sidebar.group_buttons['learning'].click()
    assert not sidebar.group_bodies['learning'].isHidden()
    qt_app.setProperty('entrelaReduceMotion', False)


def test_rendered_table_alternate_rows_keep_readable_contrast(qt_app):
    from PySide6.QtGui import QColor

    def luminance(color):
        channels = [color.redF(), color.greenF(), color.blueF()]
        linear = [v / 12.92 if v <= .04045 else ((v + .055) / 1.055) ** 2.4 for v in channels]
        return sum(v * weight for v, weight in zip(linear, (.2126, .7152, .0722)))

    window = QWidget()
    layout = QVBoxLayout(window)
    table = QTableWidget(2, 1)
    table.setAlternatingRowColors(True)
    table.horizontalHeader().setStretchLastSection(True)
    for row in range(2):
        table.setItem(row, 0, QTableWidgetItem('Dados'))
    layout.addWidget(table)
    window.resize(400, 240)
    window.show()
    try:
        for theme, high_contrast in [(theme, contrast) for theme in ('dark', 'light', 'navy') for contrast in (False, True)]:
            apply_appearance(window, theme, high_contrast=high_contrast)
            qt_app.processEvents()
            image = table.viewport().grab().toImage()
            foreground = luminance(QColor(PALETTE.text))
            backgrounds = []
            for row in range(2):
                rect = table.visualItemRect(table.item(row, 0))
                color = image.pixelColor(rect.right() - 18, rect.center().y())
                backgrounds.append(color.name())
                background = luminance(color)
                ratio = (max(foreground, background) + .05) / (min(foreground, background) + .05)
                assert ratio >= 4.5, (theme, high_contrast, row, color.name(), ratio)
            assert backgrounds[0] != backgrounds[1]
    finally:
        apply_appearance(window)
        window.close()


def test_rich_text_scales_on_font_changes_preserving_math_and_anchors(qt_app):
    window = QWidget()
    layout = QVBoxLayout(window)
    browser = QTextBrowser()
    layout.addWidget(browser)
    browser.setHtml('<h1>Título</h1><p><a name="estado"></a>Estado α<sub>2</sub> + β<sup>2</sup> <a href="#estado">Rever</a> @seed@</p>')
    window.resize(400, 250)
    window.show()
    try:
        heights = []
        for size in (15, 18, 24, 15):
            apply_appearance(window, 'light', size)
            qt_app.processEvents()
            cursor = browser.document().find('Estado')
            assert not cursor.isNull()
            # Measure the resolved layout, rather than only the default font:
            # stale serialized spans formerly kept the text at the first size.
            block = cursor.block()
            heights.append(block.layout().lineAt(0).height())
            assert browser.document().defaultFont().pixelSize() == size
            html = browser.toHtml()
            assert 'href="#estado"' in html and 'name="estado"' in html
            assert 'vertical-align:sub' in html and 'vertical-align:super' in html
            assert '@seed@' in browser.toPlainText()
        assert heights[1] > heights[0] and heights[2] > heights[1]
        assert heights[-1] == heights[0]
        # Selecting another concept after a font change also uses the new size.
        apply_appearance(window, 'dark', 24)
        browser.setHtml('<p>Novo conceito</p>')
        qt_app.processEvents()
        assert browser.document().defaultFont().pixelSize() == 24
    finally:
        apply_appearance(window)
        window.close()
