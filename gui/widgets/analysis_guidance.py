"""Rótulos e orientação de estudos; identificadores científicos ficam intactos."""
from copy import deepcopy
from core.figure_labels import STUDY_TITLES
from PySide6.QtWidgets import QComboBox


PARAMETERS = {
    "p1": ("Despolarização por porta de 1 qubit — p₁", "0, 0.01, 0.03, 0.05, 0.1", "Adimensional, entre 0 e 1. Variar p₁ ativa o modelo despolarizador."),
    "p2": ("Despolarização por porta de 2 qubits — p₂", "0, 0.01, 0.03, 0.05, 0.1", "Adimensional, entre 0 e 1. Variar p₂ ativa o modelo despolarizador."),
    "J": ("Acoplamento entre qubits — J", "0, 0.25, 0.5, 1", "Intensidade da interação no Hamiltoniano. Os outros parâmetros são mantidos."),
    "h": ("Campo transversal — h", "0, 0.25, 0.5, 1", "Campo usado em Ising e Custom. Não participa de Heisenberg, XY ou XXZ."),
    "t1_us": ("Relaxamento da população — T₁ (µs)", "20, 50, 100", "Tempo em microssegundos. Ativa o modelo térmico; cada ponto deve satisfazer T₂ ≤ 2T₁."),
    "t2_us": ("Perda de coerência — T₂ (µs)", "10, 20, 30", "Tempo em microssegundos. Ativa o modelo térmico; cada ponto deve satisfazer T₂ ≤ 2T₁."),
    "trotter_steps": ("Quantidade de passos Trotter", "1, 2, 4, 8, 16", "Inteiros de 1 a 200. Mais passos aumentam a profundidade do circuito."),
}

STUDIES = {
    "temporal": (STUDY_TITLES["temporal"], "Leia fidelidade, pureza, energia e correlações nos snapshots salvos. Clique na curva ou tabela para selecionar o mesmo estado em 3D. Requer estados salvos na execução."),
    "convergence": (STUDY_TITLES["convergence"], "Compare diferentes quantidades de passos com a evolução exata exp(−iHt). Este estudo desliga o ruído e calcula a fidelidade diretamente do estado, sem erro de amostragem. Requer evolução por Hamiltoniano."),
    "sweep": (STUDY_TITLES["sweep"], "Escolha a variável e os valores; obtenha curvas de fidelidade, pureza, energia e ⟨Z₀⟩ amostrado. Limites: 20 valores, 5 sementes e 50 execuções. Sementes variam as contagens, não a incerteza das métricas do ensemble."),
    "trotter_noise": (STUDY_TITLES["trotter_noise"], "Compare o erro ideal e o ruidoso contra a evolução exata nos mesmos passos. Mantém o tempo final, a ordem Suzuki e o ruído da fonte. O melhor ponto vale apenas entre os valores calculados; requer Hamiltoniano."),
    "mitigation_benchmark": (STUDY_TITLES["mitigation_benchmark"], "Compare sem mitigação, extrapolação para ruído zero (ZNE) linear/quadrática e verificação de paridade, quando aplicável. O resultado informa erro do observável, amostragem e custo. ZNE não reconstrói um estado: sua fidelidade fica indisponível; os ajustes compartilham medições."),
    "heatmap": (STUDY_TITLES["heatmap"], "Escolha dois eixos distintos, com até 8 valores por eixo e 64 simulações. Cada célula representa um ponto calculado, sem interpolação física. Não combine parâmetros de ruído térmico e despolarizador no mesmo mapa."),
    "zne_stability": (STUDY_TITLES["zne_stability"], "Varie fatores de ruído e medições com repetições independentes. Obtenha viés, variância amostral e RMSE do estimador de ⟨Z⟩ contra o circuito ideal. Essas incertezas não são da fidelidade do ensemble."),
    "equal_budget": (STUDY_TITLES["equal_budget"], "Sem mitigação e ZNE usam o mesmo total de shots por repetição. Na ZNE, o orçamento é dividido entre os fatores; os ajustes compartilham amostras. Isso não iguala profundidade nem tempo de execução."),
}


class ParameterCombo(QComboBox):
    """Exibe nomes humanos e também aceita os códigos nas APIs já existentes."""
    def __init__(self, order, parent=None):
        super().__init__(parent)
        self.setMinimumContentsLength(18)
        self.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLengthWithIcon)
        for key in order:
            self.addItem(PARAMETERS[key][0], key)

    def setCurrentText(self, text):
        index = self.findData(text)
        if index >= 0:
            self.setCurrentIndex(index)
        else:
            super().setCurrentText(text)


def artifact_options(data):
    """Reconstitui somente entradas já registradas, sem recalcular resultados."""
    kind = data["kind"]
    registered = data.get("protocol", {}).get("execution_options")
    rows = data["rows"]
    options = {}
    if kind in ("heatmap", "zne_stability", "equal_budget"):
        options = deepcopy(data.get("options", {}))
    elif kind in ("convergence", "trotter_noise"):
        options = {"steps": [row["steps"] for row in rows]}
    elif kind == "sweep":
        options = dict(values=list(dict.fromkeys(row["value"] for row in rows)))
        if data.get("parameter") in PARAMETERS:
            options["parameter"] = data["parameter"]
        if data.get("seeds"):
            options["seeds"] = list(data["seeds"])
    elif kind == "mitigation_benchmark":
        if "qubit" in data:
            options["qubit"] = data["qubit"]
        if isinstance(data.get("config"), dict) and "shots" in data["config"]:
            options["shots"] = data["config"]["shots"]
    if isinstance(registered, dict):
        options.update(deepcopy(registered))
    return options
