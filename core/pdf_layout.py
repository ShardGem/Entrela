"""Physical page geometry shared by scientific PDF exports.

Matplotlib retains vector text and paths. ``raster_dpi`` controls only artists
that explicitly require rasterization; it never changes the physical page size.
"""

from dataclasses import dataclass
from typing import Mapping

from matplotlib.lines import Line2D


A4_INCHES = (210 / 25.4, 297 / 25.4)
A4_POINTS = (210 * 72 / 25.4, 297 * 72 / 25.4)
REPORT_SECTIONS = (
    "include_distribution", "include_temporal", "include_bloch",
    "include_circuit", "include_configuration", "include_analyses",
)


@dataclass(frozen=True)
class ReportOptions:
    template: str = "complete"
    include_distribution: bool = True
    include_temporal: bool = True
    include_bloch: bool = True
    include_circuit: bool = True
    include_configuration: bool = True
    include_analyses: bool = True


def report_options(options=None):
    """Resolve a reproducible content selection without retaining mutable input."""
    if isinstance(options, ReportOptions):
        return options
    if options is not None and not isinstance(options, Mapping):
        raise ValueError("As opções de relatório devem ser um objeto de configuração.")
    values = dict(options or {})
    if set(values) - {"template", *REPORT_SECTIONS}:
        raise ValueError("Opção de relatório desconhecida.")
    template = values.get("template", "complete")
    if template not in ("complete", "summary"):
        raise ValueError("Escolha o modelo completo ou resumido.")
    resolved = {key: True for key in REPORT_SECTIONS}
    if template == "summary":
        resolved.update(include_circuit=False, include_configuration=False)
    for key in REPORT_SECTIONS:
        if key in values:
            if not isinstance(values[key], bool):
                raise ValueError("A seleção de seções deve usar valores booleanos.")
            resolved[key] = values[key]
    return ReportOptions(template=template, **resolved)


def validate_raster_dpi(value):
    if type(value) is not int or not 72 <= value <= 1200:
        raise ValueError("A resolução de exportação deve ficar entre 72 e 1200 DPI.")
    return value


class A4Pages:
    """Reserve a 16 mm margin and stable running furniture on every page."""

    def __init__(self, pdf, *, raster_dpi=300, is_cancelled=None):
        self.pdf = pdf
        self.raster_dpi = validate_raster_dpi(raster_dpi)
        self.is_cancelled = is_cancelled
        self.count = 0

    def add(self, fig, title, *, text_page=False, clear=True):
        from core.analysis import checkpoint

        checkpoint(self.is_cancelled, None, 0)
        self.count += 1
        if not text_page:
            # Resolve the source layout first, then place it into the page body
            # with one physical scale factor. Resizing axes independently would
            # turn circuit circles into ellipses and move suptitles into headers.
            fig.canvas.draw()
            source_width, source_height = fig.get_size_inches()
            positions = [(ax, ax.get_position().frozen()) for ax in fig.axes]
            text_positions = [(text, text.get_position()) for text in fig.texts]
            scale = min(.84*A4_INCHES[0]/source_width,
                        .765*A4_INCHES[1]/source_height)
            width = scale*source_width/A4_INCHES[0]
            height = scale*source_height/A4_INCHES[1]
            left = .08+(.84-width)/2
            bottom = .87-height
            fig.set_layout_engine(None)
            fig.set_size_inches(*A4_INCHES, forward=False)
            for ax, position in positions:
                ax.set_position((left+position.x0*width, bottom+position.y0*height,
                                 position.width*width, position.height*height))
            for text, (x,y) in text_positions:
                text.set_position((left+x*width, bottom+y*height))
        else:
            fig.set_size_inches(*A4_INCHES, forward=False)
        fig.text(.0762, .956, "ENTRELA · RELATÓRIO CIENTÍFICO", fontsize=8,
                 color="#526a7c", weight="bold", parse_math=False)
        fig.text(.0762, .925, title[:110], fontsize=12, color="#18364e",
                 weight="bold", va="top", parse_math=False)
        fig.add_artist(Line2D([.0762, .9238], [.903, .903],
                             transform=fig.transFigure, color="#d1dfe8", linewidth=.5))
        fig.text(.0762, .047, "Simulação computacional · preserve os dados brutos e a proveniência",
                 fontsize=7, color="#526a7c", parse_math=False)
        fig.text(.9238, .047, str(self.count), fontsize=8, ha="right", color="#526a7c")
        try:
            # Prevent user-level savefig.bbox='tight' from silently cropping A4.
            from matplotlib import rc_context
            with rc_context({"savefig.bbox": None, "pdf.fonttype": 42}):
                self.pdf.savefig(fig, dpi=self.raster_dpi, bbox_inches=None)
        finally:
            if clear:
                fig.clear()


def export_figure_a4(fig, filepath, *, raster_dpi=300, title="Vista da simulação"):
    """Export an existing camera view without modifying its live canvas.

    The live figure may belong to a Qt widget. Copying through pickle is unsafe
    for arbitrary artists, so temporarily change page geometry and restore the
    original figure state immediately after saving. No screenshots are used.
    """
    from pathlib import Path
    import tempfile
    from matplotlib.backends.backend_pdf import PdfPages
    from matplotlib import rc_context

    validate_raster_dpi(raster_dpi)
    path = Path(filepath)
    size = fig.get_size_inches().copy()
    engine = fig.get_layout_engine()
    texts, artists = set(fig.texts), set(fig.artists)
    positions = [(ax, ax.get_position().frozen(), ax.get_in_layout()) for ax in fig.axes]
    text_positions = [(text,text.get_position()) for text in fig.texts]
    try:
        with tempfile.TemporaryDirectory(prefix=".entrela-view-", dir=path.parent) as directory:
            temporary = Path(directory) / "view.pdf"
            with rc_context({"pdf.fonttype":42}), PdfPages(temporary) as pdf:
                A4Pages(pdf, raster_dpi=raster_dpi).add(fig, title, clear=False)
            temporary.replace(path)
    finally:
        for text in list(fig.texts):
            if text not in texts:
                text.remove()
        for artist in list(fig.artists):
            if artist not in artists:
                artist.remove()
        fig.set_size_inches(size, forward=False)
        fig.set_layout_engine(engine)
        for ax, position, in_layout in positions:
            ax.set_position(position)
            ax.set_in_layout(in_layout)
        for text,position in text_positions:
            text.set_position(position)
        if fig.canvas:
            fig.canvas.draw_idle()
    return path
