"""Shared scientific labels, independent of Qt and presentation themes."""

STUDY_TITLES = {
    "temporal": "Acompanhar métricas e correlações",
    "convergence": "Avaliar a precisão da Trotterização",
    "sweep": "Variar um parâmetro",
    "trotter_noise": "Estudar passos Trotter e ruído juntos",
    "mitigation_benchmark": "Comparar métodos de mitigação",
    "heatmap": "Variar dois parâmetros em um mapa",
    "zne_stability": "Avaliar a estabilidade da ZNE",
    "equal_budget": "Comparar com o mesmo total de medições",
}


def field_label(key):
    if key.startswith("entropy_q"):
        return "Entropia de q" + key.removeprefix("entropy_q") + " (bits)"
    return {
        "snapshot": "Snapshot",
        "time": "Tempo (ℏ=1)",
        "fidelity": "Fidelidade ao circuito ideal",
        "purity": "Pureza global",
        "energy": "Energia ⟨H⟩",
        "fidelity_exact": "Fidelidade à evolução exata",
        "trotter_infidelity": "Erro de Trotter (1−F ideal/exato)",
        "negativity_q0_rest": "Negatividade q0 | resto",
        "steps": "Passos Trotter",
        "infidelity": "Infidelidade à evolução exata",
        "depth": "Profundidade",
        "order": "Ordem Suzuki",
        "seed": "Semente",
        "sampled_Z0": "⟨Z0⟩ amostrado",
        "value": "Valor do parâmetro",
        "paired_infidelity": "Erro 1−F contra evolução exata (ideal e ruidoso)",
        "fidelity_ideal_exact": "Fidelidade Trotter ideal/exata",
        "fidelity_noisy_exact": "Fidelidade ruidosa/exata",
        "fidelity_noisy_ideal": "Fidelidade ruidosa/circuito ideal",
        "ideal_infidelity": "Erro Trotter ideal/exato (1−F)",
        "noisy_infidelity": "Erro ruidoso/exato (1−F)",
        "gate_count": "Portas unitárias",
        "ideal_runtime_s": "Tempo ideal (s)",
        "noisy_runtime_s": "Tempo ruidoso (s)",
        "method": "Método",
        "label": "Descrição",
        "status": "Disponibilidade",
        "reason": "Condição / limitação",
        "estimate": "Estimativa de ⟨Z⟩",
        "stderr": "Erro padrão de amostragem",
        "absolute_error": "Erro absoluto do observável",
        "circuits": "Circuitos por método",
        "shots": "Shots por método",
        "retained_shots": "Shots aceitos",
        "acceptance": "Fração amostral aceita",
        "acquisition_s": "Aquisição compartilhada (s)",
        "processing_s": "Processamento (s)",
        "duration_s": "Tempo equivalente do método (s)",
        "shared_samples": "Amostras compartilhadas",
        "state_metrics_source": "Origem das métricas de estado",
        "x":"Valor X", "y":"Valor Y", "factors":"Fatores efetivos",
        "shots_setting":"Shots configurados", "repetitions":"Repetições independentes",
        "mean_estimate":"Média de ⟨Z⟩", "bias":"Viés empírico", "sample_variance":"Variância amostral",
        "mse":"Erro quadrático médio empírico", "rmse":"Raiz do erro quadrático médio",
        "stderr_mean":"Erro padrão da média amostral", "out_of_range":"Estimativas fora de [-1,1]",
        "mean_reported_stderr":"Erro padrão previsto médio", "mean_absolute_error":"Erro absoluto médio",
        "shots_per_method":"Shots por método / repetição", "circuits_per_method":"Circuitos por método / repetição",
        "degrees_of_freedom":"Graus de liberdade residuais", "acquisition_group_s":"Aquisição total do grupo (s)",
        "mean_acquisition_s":"Aquisição média por método (s)","mean_processing_s":"Tempo médio do ajuste (s)",
        "mean_duration_s":"Aquisição + ajuste médios (s)",
    }.get(key, key)


PARAMETER_LABELS = {
    "p1": "Probabilidade de erro em portas de 1 qubit (0–1)",
    "p2": "Probabilidade de erro em portas de 2 qubits (0–1)",
    "t1_us": "Relaxação T₁ (µs)", "t2_us": "Descoerência T₂ (µs)",
    "gate_time_1q_ns": "Duração das portas de 1 qubit (ns)",
    "gate_time_2q_ns": "Duração das portas de 2 qubits (ns)",
    "J": "Acoplamento J", "h": "Campo h",
    "trotter_steps": "Passos Trotter", "total_time": "Tempo (ℏ=1)",
}


def axis_label(key, config=None, parameter=None):
    if key == "time" and (not isinstance(config, dict) or "circuit" not in config):
        return "Coordenada registrada (unidade não informada)"
    if key == "time" and isinstance(config, dict) and config.get("circuit") is not None:
        return "Índice da porta lógica (sem tempo físico)"
    if parameter is not None:
        return PARAMETER_LABELS.get(parameter, field_label(parameter))
    return field_label(key)
