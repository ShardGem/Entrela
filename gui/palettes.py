"""Perfis de aparência e papéis de cor compartilhados pelo aplicativo."""

from dataclasses import asdict

from gui.theme import Palette

DARK = asdict(Palette())
LIGHT = {
    **DARK,
    "bg": "#F3F5FA", "bg_elevated": "#FFFFFF", "surface": "#E9EDF6",
    "surface_hover": "#E1E7F3", "surface_active": "#D8E0F2",
    "border": "#D6DEED", "border_strong": "#808DAB",
    "primary": "#354BC2", "primary_hover": "#2940B3", "primary_pressed": "#21338D",
    "primary_muted": "#DCE4FF", "primary_faint": "#EDF0FF",
    "primary_on": "#FFFFFF", "text_on_primary": "#FFFFFF",
    "action_bg": "#354BC2", "action_hover": "#2940B3", "action_pressed": "#21338D", "action_on": "#FFFFFF",
    "text": "#191F36", "text_muted": "#454F6A", "text_dim": "#596680",
    "chrome": "#E4E9F4", "chrome_border": "#CCD6EA", "chrome_text": "#222B46",
    "chrome_muted": "#455475", "chrome_hover": "#DBE2F2", "chrome_selected": "#D2DDFB",
    "chrome_accent": "#3045AD",
    "success": "#187152", "success_bg": "#E1F3EB",
    "warning": "#82500F", "warning_bg": "#F9EEDB",
    "danger": "#A72C53", "danger_bg": "#F9E9F0",
    "info": "#3353A2", "info_bg": "#E6EDFA",
    "q1": "#5065C8", "q2": "#8550A0", "q3": "#137877",
    "q4": "#996021", "q5": "#AB4F68", "q6": "#326C9D",
}
NAVY = {
    **LIGHT,
    "bg": "#F8F9FD", "border": "#DCE2EF",
    "chrome": "#E8EDF7", "chrome_border": "#CCD7EA", "chrome_text": "#24324A",
    "chrome_muted": "#4C5A73", "chrome_hover": "#DFE7F5", "chrome_selected": "#D3DFF8",
    "chrome_accent": "#2F459F",
}

THEMES = {"dark": DARK, "light": LIGHT, "navy": NAVY}
THEME_CHOICES = (
    ("Grafite", "dark"),
    ("Claro", "light"),
    ("Azul Entrela · padrão", "navy"),
    ("Automático · acompanhar o sistema", "auto"),
)
THEME_DESCRIPTIONS = {
    "dark": "Grafite combina fundo escuro, superfícies neutras e azul claro para ações.",
    "light": "Claro usa superfícies claras em toda a janela, com índigo para foco e ações.",
    "navy": "Azul Entrela usa tons de azul ardósia na navegação e índigo para ações e seleções.",
    "auto": "Automático acompanha a aparência do sistema operacional.",
}
