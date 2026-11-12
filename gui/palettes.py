"""Perfis visuais da interface, independentes dos parâmetros científicos."""

from dataclasses import asdict

from gui.theme import Palette

DARK = asdict(Palette())
LIGHT = {
    **DARK,
    "bg": "#f2f5f8", "bg_elevated": "#ffffff", "surface": "#ffffff",
    "surface_hover": "#e9f0f6", "surface_active": "#ddeaf3",
    "border": "#d9e2eb", "border_strong": "#93a8bb",
    "primary": "#1b6f94", "primary_hover": "#155c7c", "primary_pressed": "#104962",
    "primary_muted": "#e0f0f6", "primary_faint": "#e0f0f6",
    "primary_on": "#ffffff", "text_on_primary": "#ffffff",
    "text": "#1c2e42", "text_muted": "#4b6178", "text_dim": "#526b82",
    "success": "#11763f", "success_bg": "#e0f4e8",
    "warning": "#925400", "warning_bg": "#fff0ce",
    "danger": "#bb293e", "danger_bg": "#ffe7eb",
    "info": "#1b6f94", "info_bg": "#e0f0f6",
    "q1": "#1b6f94", "q2": "#7043c5", "q3": "#11763f",
    "q4": "#925400", "q5": "#bb293e", "q6": "#2258bc",
}
NAVY = {
    **DARK,
    "bg": "#0c1524", "bg_elevated": "#121f32", "surface": "#1a2a40",
    "surface_hover": "#21344d", "surface_active": "#29415b",
    "border": "#2c405a", "border_strong": "#637f9e",
    "text": "#e5eef9", "text_muted": "#adc0d7", "text_dim": "#9fb5cf",
    "primary": "#86baff", "primary_hover": "#b0d2ff", "primary_pressed": "#659fea",
    "primary_muted": "#203750", "primary_faint": "#203750",
    "info": "#86baff", "info_bg": "#203750", "q1": "#86baff",
}

THEMES = {"dark": DARK, "light": LIGHT, "navy": NAVY}
THEME_CHOICES = (
    ("Grafite · padrão Entrela", "dark"),
    ("Claro científico", "light"),
    ("Azul escuro", "navy"),
    ("Automático · acompanhar o sistema", "auto"),
)
THEME_DESCRIPTIONS = {
    "dark": "Grafite: superfícies neutras e ciano discreto para destacar ações e seleção.",
    "light": "Claro científico: fundo claro e destaque azul para leitura de parâmetros, tabelas e resultados.",
    "navy": "Azul escuro: superfícies azuladas e destaque azul suave para explorar circuitos e visualizações.",
    "auto": "Automático: alterna entre Grafite e Claro científico conforme a aparência do sistema operacional.",
}
