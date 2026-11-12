"""Contratos de aparência: escolha persistida, dados preservados e legibilidade."""

from hashlib import sha256

import pytest
from PySide6.QtCore import QSettings
from PySide6.QtGui import QColor

from core.examples import create_example_config
from core.simulation import run_experiment
from data.repository import ExperimentRepository
from gui.controllers.appearance import apply_appearance, resolve_theme
from gui.main_window import MainWindow
from gui.pages.settings import SettingsPage
from gui.theme import PALETTE


def _settle(app):
    for _ in range(8):
        app.processEvents()


def _luminance(value):
    color = QColor(value)
    values = (color.redF(), color.greenF(), color.blueF())
    linear = [v / 12.92 if v <= .04045 else ((v + .055) / 1.055) ** 2.4 for v in values]
    return sum(v * w for v, w in zip(linear, (.2126, .7152, .0722)))


def _contrast(a, b):
    x, y = sorted((_luminance(a), _luminance(b)))
    return (y + .05) / (x + .05)


@pytest.mark.parametrize('theme', ['dark', 'light', 'navy'])
def test_profiles_have_readable_text_and_primary_actions(window, theme):
    for high_contrast in (False, True):
        apply_appearance(window, theme, high_contrast=high_contrast)
        for text in (PALETTE.text, PALETTE.text_muted, PALETTE.text_dim):
            for surface in (PALETTE.bg, PALETTE.bg_elevated, PALETTE.surface, PALETTE.surface_hover):
                assert _contrast(text, surface) >= 4.5, (theme, high_contrast, text, surface)
        assert _contrast(PALETTE.primary_on, PALETTE.primary) >= 4.5
    assert resolve_theme(theme) == theme


def test_profiles_restore_legacy_choices_and_keep_scientific_data(window, qt_app, tmp_path):
    experiment = run_experiment(create_example_config('bell'))
    window.repository.save(experiment)
    window._current_experiment = experiment
    window._display_experiment(experiment)
    window._apply_draft(experiment.config, 'Configuração preservada')
    paths = list(window.repository.base_dir.rglob('*.json'))
    before = {path: sha256(path.read_bytes()).hexdigest() for path in paths}
    states = [state.data.copy() for state in experiment.result.states]
    assert before and states
    page = window.page_settings
    for theme in ('navy', 'light', 'dark'):
        page.theme.setCurrentIndex(page.theme.findData(theme))
        _settle(qt_app)
        assert window.settings.value('appearance/theme') == theme
        assert window._current_experiment is experiment
        assert window.page_simulation.config_panel.get_config() == experiment.config
        assert {path: sha256(path.read_bytes()).hexdigest() for path in paths} == before
        assert all((state.data == saved).all() for state, saved in zip(experiment.result.states, states))
    page.accent.setCurrentIndex(page.accent.findData('violet'))
    page.theme.setCurrentIndex(page.theme.findData('navy'))
    assert PALETTE.primary == '#c1a4ff'
    settings_path = tmp_path / 'restore.ini'
    settings = QSettings(str(settings_path), QSettings.IniFormat)
    settings.setValue('appearance/theme', 'navy')
    settings.setValue('appearance/accent', 'violet')
    settings.sync()
    restored = MainWindow(ExperimentRepository(tmp_path / 'other-runs'), QSettings(str(settings_path), QSettings.IniFormat))
    try:
        assert restored.page_settings.collect_values()['theme'] == 'navy'
        assert restored.page_settings.collect_values()['accent'] == 'violet'
        assert 'Azul escuro' in restored.page_settings.theme_description.text()
        assert restored.property('entrelaTheme') == 'navy'
    finally:
        restored.close()
        restored.deleteLater()


@pytest.mark.parametrize('size,font', [((1440, 960), 15), ((1024, 768), 15), ((1024, 768), 24)])
def test_metric_layout_adapts_without_losing_values(window, qt_app, size, font):
    window._show_page('results')
    apply_appearance(window, 'navy', font)
    window.resize(*size)
    window.show()
    _settle(qt_app)
    assert (window.width(), window.height()) == size
    cards = window.page_results.metric_grid.cards
    rects = [card.geometry() for card in cards]
    assert all(card.isVisible() and rect.width() > 0 for card, rect in zip(cards, rects))
    for i, rect in enumerate(rects):
        assert all(not rect.intersects(other) for other in rects[i + 1:])
        assert rect.right() < window.page_results.metric_grid.width()
    if size[0] == 1440:
        assert len({rect.y() for rect in rects}) == 1
    else:
        assert len({rect.y() for rect in rects}) >= 2
    assert window.page_results._scroll.horizontalScrollBar().maximum() == 0


def test_window_uses_one_page_heading_and_keeps_explanations(window, qt_app):
    for key in window.pages:
        window._show_page(key)
        _settle(qt_app)
        page = window.pages[key]
        assert not page._title.isVisible()
        assert window.topbar.title.text()
    assert not window.page_results.btn_report.isHidden()
    assert window.page_settings._subtitle.text()
    assert SettingsPage.DEFAULTS['theme'] == 'dark'
