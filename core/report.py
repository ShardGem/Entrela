"""Portable academic report with escaped data and embedded figures."""

from dataclasses import asdict
from html import escape
from io import BytesIO
from base64 import b64encode
import json
from matplotlib.figure import Figure
from matplotlib.backends.backend_agg import FigureCanvasAgg
from core.export import result_interpretation


def report_html(experiment, analysis=None, annotation=None):
    c, r = experiment.config, experiment.result

    def pre(value):
        return (
            "<pre>"
            + escape(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False))
            + "</pre>"
        )

    fig = Figure(figsize=(9, 3), layout="constrained")
    FigureCanvasAgg(fig)
    ax = fig.add_subplot(111)
    keys = sorted(r.counts or {})
    total = sum((r.counts or {}).values())
    ax.bar(keys, [(r.counts[k] / total) if total else 0 for k in keys], color="#007ea7")
    ax.set_ylabel("Frequência observada")
    ax.set_xlabel("Bitstring (q0 à direita)")
    if len(keys) > 8:
        ax.tick_params(axis="x", rotation=90)
    buffer = BytesIO()
    fig.savefig(buffer, format="png", dpi=120)
    image = b64encode(buffer.getvalue()).decode("ascii")
    metrics = "".join(
        f"<tr><td>{escape(label)}</td><td>{'—' if value is None else format(value, '.12g')}</td></tr>"
        for label, value in [
            ("Fidelidade ao circuito ideal", r.fidelity),
            ("Pureza global", r.purity),
            ("Energia ⟨H⟩", r.energy),
        ]
    )
    return f"""<!doctype html><html lang="pt-BR"><meta charset="utf-8"><title>Entrela · {escape(experiment.id)}</title>
<style>body{{font:16px system-ui,sans-serif;color:#172b46;max-width:1000px;margin:40px auto;padding:0 24px;line-height:1.6}}h1,h2{{color:#006e96}}pre{{white-space:pre-wrap;overflow-wrap:anywhere;background:#f1f5fa;padding:16px;font:12px monospace}}table{{border-collapse:collapse;width:100%}}td,th{{border-bottom:1px solid #ccd6e0;padding:10px;text-align:left}}img{{width:100%}}@media print{{body{{margin:0}}h2{{break-after:avoid}}pre{{font-size:9px}}}}</style>
<h1>Entrela · Relatório de experimento</h1>
<p>Registro {escape(experiment.id)} · {escape(experiment.created_at.isoformat())} · {experiment.duration_s:.6g} s de execução</p>
<h2>Resultados</h2><table>{metrics}</table><p>{escape(result_interpretation(experiment)).replace(chr(10), "<br>")}</p>
<img alt="Distribuição das medições" src="data:image/png;base64,{image}">
<h2>Configuração reproduzível</h2>{pre(asdict(c))}<h2>Ambiente e proveniência</h2>{pre({k: (f"{len(v)} operações no JSON completo" if k == "operations" else v) for k, v in r.metadata.items()})}
<h2>Convenções e limitações</h2><p>Ising H=+J ΣZZ+h ΣX. Tempo adimensional, ℏ=1; q0 à direita nas bitstrings. O modelo térmico aplica 50 ns por porta, inclusive na preparação, sem calibração de hardware. Fidelidade ao circuito ideal não é a fidelidade à evolução exata. Matrizes densidade descrevem o ensemble, enquanto contagens têm flutuação de amostragem. Pureza local baixa também pode decorrer de emaranhamento. ZNE estima Z, não reconstrói um estado mitigado e não garante melhoria. Erros padrão cobrem amostragem, não viés de extrapolação.</p>
<h2>Análise ZNE</h2>{pre(r.mitigation)}
{("<h2>Análise científica adicional</h2>" + pre(analysis)) if analysis else ""}
{("<h2>Projeto e notas</h2>" + pre(annotation)) if annotation else ""}
<h2>Circuito (primeiros 10.000 caracteres)</h2><pre>{escape(r.circuit_text[:10000])}</pre>
<p>Para reprodução completa, preserve também o JSON com os estados e as versões registradas. Reprodução entre versões não é garantida.</p></html>"""


def export_report(experiment, filepath, analysis=None, annotation=None):
    from pathlib import Path

    path = Path(filepath)
    html = report_html(experiment, analysis, annotation)
    if path.suffix.lower() == ".pdf":
        from PySide6.QtGui import QTextDocument
        from PySide6.QtPrintSupport import QPrinter

        printer = QPrinter(QPrinter.HighResolution)
        printer.setOutputFormat(QPrinter.PdfFormat)
        printer.setOutputFileName(str(path))
        doc = QTextDocument()
        doc.setHtml(html)
        doc.print_(printer)
    else:
        path.write_text(html, encoding="utf-8")
    return path
