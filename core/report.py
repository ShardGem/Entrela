"""Self-contained scientific reports with bounded plots and explicit provenance."""

from base64 import b64encode
from dataclasses import asdict
from html import escape
from io import BytesIO
import json

from core.export import result_interpretation
from core.figures import MAX_PLOT_SNAPSHOTS
from core.types import system_label
from data.workspace import experiment_title


def _printed_summary(value):
    """Bound bulky machine-readable payloads without mutating their source."""
    if isinstance(value, dict):
        if "real" in value and "imag" in value:
            dimensions = []
            component = value["real"]
            while isinstance(component, list):
                dimensions.append(len(component))
                component = component[0] if component else None
            return {
                "kind": value.get("kind", "complex_array"),
                "dimensions": dimensions,
                "reference": "Estado complexo integral preservado no JSON completo; componentes omitidos neste relatório.",
            }
        return {
            key: (
                f"{len(child)} operações preservadas no JSON completo; lista omitida neste relatório."
                if key == "operations" and isinstance(child, list)
                else _printed_summary(child)
            )
            for key, child in value.items()
        }
    if isinstance(value, list):
        return [_printed_summary(child) for child in value]
    return value


def _pre(value):
    return "<pre>" + escape(json.dumps(_printed_summary(value), ensure_ascii=False, indent=2, allow_nan=False)) + "</pre>"


def _fit_limitation(data):
    fits = list(data.get("fits", {}).values())
    if "degrees_of_freedom" in data:
        fits.append(data)
    if any(fit.get("degrees_of_freedom") == 0 for fit in fits):
        return (
            "<p><strong>Diagnóstico de ajuste:</strong> há um ajuste com zero graus de liberdade residual "
            "(como o quadrático com três pontos). Resíduos nulos não demonstram a adequação do polinômio. "
            "O erro padrão propagado descreve amostragem; não cobre viés de extrapolação.</p>"
        )
    return ""


def _number(value):
    return "—" if value is None else format(value, ".10g")


def _image(figure, description):
    buffer = BytesIO()
    figure.savefig(buffer, format="png", dpi=140, facecolor="white")
    figure.clear()
    return '<img alt="' + escape(description, quote=True) + '" src="data:image/png;base64,' + b64encode(buffer.getvalue()).decode("ascii") + '">'


def _report_analysis_data(analysis):
    presented = dict(analysis)
    if "source_metadata" in presented:
        presented["source_metadata"] = {
            key: (f"{len(value)} operações no JSON completo" if key == "operations" else value)
            for key, value in presented["source_metadata"].items()
        }
    if "runs" in presented:
        presented["runs"] = [
            {key: run.get(key) for key in ("id", "condition", "steps", "created_at", "duration_s")}
            for run in presented["runs"]
        ]
    return presented


def hamiltonian_description(config):
    if config.circuit is not None:
        return "Circuito livre: índice da porta lógica; sem Hamiltoniano, energia ou tempo físico definido."
    descriptions = {
        "Ising": "Ising: H = +J Σ⟨i,j⟩ ZiZj + h Σi Xi.",
        "Custom": "Custom (compatibilidade legada com Ising): H = +J Σ⟨i,j⟩ ZiZj + h Σi Xi; não é um Hamiltoniano personalizado.",
        "Heisenberg": "Heisenberg: H = J Σ⟨i,j⟩ (XiXj + YiYj + ZiZj).",
        "XY": "XY: H = J Σ⟨i,j⟩ (XiXj + YiYj).",
        "XXZ": "XXZ: H = J Σ⟨i,j⟩ (XiXj + YiYj + 0,5 ZiZj).",
    }
    description = descriptions[config.system.hamiltonian]
    if config.system.hamiltonian not in ("Ising", "Custom"):
        description += " O parâmetro h não participa deste modelo."
    boundary = "periódica (elo final–inicial somente com mais de dois qubits)" if config.system.periodic else "aberta"
    return description + " Fronteira " + boundary + ". Tempo adimensional, ℏ = 1."


def _distribution(experiment):
    from core.figures import histogram_figure
    if not experiment.result.counts:
        return "<p>Esta execução não possui contagens registradas.</p>"
    return _image(histogram_figure([experiment]), "Distribuição das medições")


def _temporal_plot(experiment):
    from core.figures import temporal_figure, probability_figure
    r = experiment.result
    if not r.states or not r.times:
        return "<p>Snapshots não foram registrados nesta execução; não há curva temporal a reconstruir.</p>"
    count = min(len(r.states), len(r.times))
    selected = min(count, MAX_PLOT_SNAPSHOTS)
    note = f"Curvas derivadas de {selected} dos {count} snapshots reais; sem interpolação física."
    return _image(temporal_figure([experiment]), "Métricas dos snapshots da execução") + _image(probability_figure(experiment), "Probabilidades dos estados; seleção pelos maiores picos na trajetória e massa omitida em Outros") + "<p class=caption>" + note + "</p>"


def _analysis_section(analysis):
    if not analysis:
        return ""
    if analysis.get("kind") != "mitigation_benchmark":
        kind = analysis.get("kind")
        rows = analysis.get("rows", [])
        section = "<h2>Análise científica adicional</h2>"
        if rows:
            from core.figures import analysis_figure
            section += _image(analysis_figure(analysis), "Estudo científico calculado")
        if analysis.get("protocol"):
            section += "<h3>Protocolo e referência no TCC</h3>" + _pre(analysis["protocol"])
        # The machine-readable export preserves every underlying run, including
        # potentially thousands of operations. Keep the printed report bounded.
        presented = _report_analysis_data(analysis)
        if "runs" in analysis:
            section += "<p>O índice abaixo identifica as execuções do estudo; configurações, contagens e metadados integrais estão no JSON da análise.</p>"
        return section + _pre(presented)
    rows = analysis.get("rows", [])
    table_rows = []
    for row in rows:
        label = row.get("label", row.get("method", "Método"))
        status = row.get("status", "")
        if row.get("reason"):
            status += ": " + row["reason"]
        values = [label, status, row.get("estimate"), row.get("absolute_error"), row.get("stderr"), row.get("duration_s"), row.get("fidelity")]
        table_rows.append("<tr>" + "".join("<td>" + (escape(str(v)) if i < 2 else _number(v)) + "</td>" for i, v in enumerate(values)) + "</tr>")
    section = (
        "<h2>Benchmark de mitigação</h2><p>Estimativas do mesmo observável, com sua referência ideal. "
        "Fidelidade só se aplica quando há um estado físico; extrapolação de observável não reconstrói um estado mitigado.</p>"
        "<table><tr><th>Método</th><th>Estado</th><th>Estimativa</th><th>Erro absoluto</th><th>Erro padrão</th><th>Tempo (s)</th><th>Fidelidade</th></tr>"
        + "".join(table_rows) + "</table>"
    )
    section += "<p>Referência ideal do observável: " + _number(analysis.get("ideal_observable")) + ". Tempos por método incluem aquisição compartilhada quando indicada; não devem ser somados. Custo total de circuitos e shots efetivamente executados:</p>" + _pre(analysis.get("actual_cost", {}))
    valid = [row for row in rows if row.get("absolute_error") is not None]
    if valid:
        from core.figures import analysis_figure
        section += _image(analysis_figure(analysis, 'absolute_error'), "Erro de estimativa por método de mitigação")
    return section + _fit_limitation(analysis) + "<h3>Protocolo, custos e dados do benchmark</h3>" + _pre(_report_analysis_data(analysis))


def _bloch_image(experiment):
    if experiment.result.final_state is None and not experiment.result.states:
        return "<p>Estados não disponíveis neste registro.</p>"
    from core.figures import bloch_figure
    return _image(bloch_figure([experiment]),"Esferas de Bloch dos estados locais finais")


def report_html(experiment, analysis=None, annotation=None):
    c, r = experiment.config, experiment.result
    if analysis and analysis.get("source_id") not in (None, experiment.id):
        raise ValueError("A análise selecionada pertence a outra execução; reabra a análise desta fonte.")
    annotation = annotation or {}
    title = experiment_title(experiment, {experiment.id: annotation})
    metric_rows = "".join(
        f"<tr><td>{escape(label)}</td><td>{_number(value)}</td><td>{escape(reference)}</td></tr>"
        for label, value, reference in [
            ("Fidelidade de Uhlmann ao quadrado", r.fidelity, r.metadata.get("fidelity_reference", "Mesmo circuito sem ruído")),
            ("Pureza global Tr(ρ²)", r.purity, "Estado global final; diferente de pureza local"),
            ("Energia média ⟨H⟩", r.energy, "Hamiltoniano configurado" if c.circuit is None else "Não se aplica a circuito livre"),
        ]
    )
    parameters = [
        ("Sistema", system_label(c)),
        ("Qubits / estado inicial", f"{c.system.num_qubits} / {'|0…0⟩ + portas do documento' if c.circuit is not None else c.system.initial_state}"),
        ("Ruído", c.noise.kind if c.noise.enabled else "Desligado"),
        ("Amostras (shots)", str(c.shots)),
        ("Semente efetiva", str(r.metadata.get("effective_seed", "Não registrada"))),
        ("Profundidade do circuito", str(r.circuit_depth)),
        ("Mitigação do registro", "ZNE · " + str(r.mitigation.get("method", "")) if r.mitigation else "Sem mitigação neste registro"),
    ]
    parameter_rows = "".join(f"<tr><td>{escape(label)}</td><td>{escape(value)}</td></tr>" for label, value in parameters)
    operation_rows = "".join(
        "<tr><td>" + str(i + 1) + "</td><td>" + escape(op["name"].upper())
        + "</td><td>" + escape(str(op["qubits"])) + "</td><td>"
        + escape(", ".join(format(value, ".9g") for value in op.get("parameters", [])))
        + "</td><td>" + str(op.get("step", 0)) + "</td></tr>"
        for i, op in enumerate(r.metadata.get("operations", [])[:200])
    )
    metadata = {key: (f"{len(value)} operações preservadas no JSON completo" if key == "operations" else value) for key, value in r.metadata.items()}
    notes = ""
    if annotation:
        notes = "<h2>Projeto e observações</h2>" + _pre(annotation)
    mitigation = "<h2>Análise ZNE do registro</h2>" + _fit_limitation(r.mitigation) + _pre(r.mitigation) if r.mitigation else ""
    failure = "<p><strong>Execução com erro: " + escape(r.error) + "</strong></p>" if r.error else ""
    return f'''<!doctype html><html lang="pt-BR"><head><meta charset="utf-8"><title>Entrela · {escape(title)}</title>
<style>
body{{font:11pt sans-serif;color:#1f3048;max-width:960px;margin:36px auto;padding:0 24px;line-height:1.55}}
h1{{font-size:25pt;color:#12314b;margin-bottom:8px}}h2{{font-size:16pt;color:#006e96;margin-top:28px}}h3{{font-size:12pt}}
.kicker{{color:#006e96;font-size:10pt;font-weight:bold;letter-spacing:1px}}.caption{{font-size:9pt;color:#56677b}}.summary{{background:#f0f6fa;padding:16px}}
pre{{white-space:pre-wrap;overflow-wrap:anywhere;background:#f3f6f9;padding:12px;font:8pt monospace}}
table{{border-collapse:collapse;width:100%;font-size:10pt}}td,th{{border-bottom:1px solid #d5dfe8;padding:8px;text-align:left}}th{{background:#edf4f8}}img{{width:100%;height:auto}}
@media print{{body{{margin:0;padding:0}}h2,h3{{page-break-after:avoid}}tr,img{{page-break-inside:avoid}}}}
</style></head><body>
<p class="kicker">ENTRELA · RELATÓRIO CIENTÍFICO DE EXPERIMENTO</p><h1>{escape(title)}</h1>
<p class="caption">Identificador técnico: {escape(experiment.id)}<br>Data e fuso: {escape(experiment.created_at.isoformat())}<br>Duração da execução: {experiment.duration_s:.6g} s</p>
{failure}<div class="summary"><strong>Protocolo e rastreabilidade</strong><p>{escape(hamiltonian_description(c))}</p><table>{parameter_rows}</table></div>
{notes}<h2>Resultados e referências</h2><table><tr><th>Métrica</th><th>Valor</th><th>Referência e significado</th></tr>{metric_rows}</table>
<p>{escape(result_interpretation(experiment)).replace(chr(10), '<br>')}</p>
<h2>Distribuição das medições</h2>{_distribution(experiment)}
<h2>Evolução dos estados registrados</h2>{_temporal_plot(experiment)}
<h2>Estados locais de Bloch</h2>{_bloch_image(experiment)}
{mitigation}{_analysis_section(analysis)}
<h2>Convenções e limitações</h2><p>q0 fica à direita nas bitstrings. O modelo térmico aplica as durações assumidas registradas na configuração (padrão: 50 ns por porta 1q/2q), inclusive na preparação, sem calibração de hardware. Fidelidade ao circuito ideal não é fidelidade à evolução exata. Matrizes densidade descrevem o ensemble, enquanto contagens têm flutuação de amostragem. Pureza local baixa também pode decorrer de emaranhamento. ZNE estima um observável; não reconstrói um estado mitigado e não garante melhoria. Erros padrão cobrem amostragem sob o estimador utilizado, não viés do modelo de ruído ou da extrapolação. Repetir uma seed não constitui uma observação independente.</p>
<h2>Configuração completa para reprodução</h2>{_pre(asdict(c))}
<h2>Ambiente, versões e proveniência</h2>{_pre(metadata)}
<h2>Circuito — primeiras 200 operações</h2><table><tr><th>#</th><th>Porta</th><th>Qubits</th><th>Parâmetros (rad)</th><th>Passo</th></tr>{operation_rows}</table>
<p class="caption">Preserve o JSON completo com os estados e operações e os dados CSV/JSON das análises. Este relatório é uma apresentação dos resultados; reprodução entre versões e plataformas não é garantida.</p>
</body></html>'''


def export_report(experiment, filepath, analysis=None, annotation=None, *, options=None, raster_dpi=300):
    from pathlib import Path
    if Path(filepath).suffix.lower() == ".pdf":
        from core.documentation import export_pdf
        return export_pdf([experiment], filepath, [analysis] if analysis else (),
                          {experiment.id: annotation or {}}, options=options,
                          raster_dpi=raster_dpi)
    return export_rendered_report(report_html(experiment, analysis, annotation), filepath)


def export_rendered_report(html, filepath):
    """Write a prepared HTML report; PDF printing must run on the Qt GUI thread."""
    from pathlib import Path

    path = Path(filepath)
    if path.suffix.lower() == ".pdf":
        from PySide6.QtCore import QMarginsF
        from PySide6.QtGui import QTextDocument, QPageSize
        from PySide6.QtPrintSupport import QPrinter

        printer = QPrinter(QPrinter.HighResolution)
        printer.setOutputFormat(QPrinter.PdfFormat)
        printer.setOutputFileName(str(path))
        printer.setPageSize(QPageSize(QPageSize.A4))
        printer.setPageMargins(QMarginsF(16, 16, 16, 16))
        document = QTextDocument()
        document.setHtml(html)
        document.print_(printer)
    else:
        path.write_text(html, encoding="utf-8")
    return path
