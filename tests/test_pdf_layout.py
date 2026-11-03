"""Physical report pages, vector text and independent report paths stay consistent."""
from dataclasses import replace
from pathlib import Path
import re

import numpy as np
import pytest

from core.documentation import export_pdf
from core.examples import create_example_config
from core.figures import figure, temporal_figure, analysis_table_figures
from core.pdf_layout import A4_POINTS, REPORT_SECTIONS, export_figure_a4, report_options
from core.report import export_report
from core.simulation import SimulationCancelled, run_experiment
from gui.pages.documentation import DocumentationPage
from gui.workers.report_worker import ReportWorker


@pytest.fixture(scope="module")
def run():
    return run_experiment(replace(create_example_config("bell"), shots=32))


def media_boxes(path):
    data=Path(path).read_bytes()
    boxes=re.findall(rb"/MediaBox\s*\[\s*([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s*\]",data)
    assert boxes, "PDF did not contain physical page boxes"
    return [tuple(float(value) for value in box) for box in boxes]


def assert_a4(path):
    for left,bottom,width,height in media_boxes(path):
        assert (left,bottom)==(0,0)
        assert width==pytest.approx(A4_POINTS[0],abs=1e-5)
        assert height==pytest.approx(A4_POINTS[1],abs=1e-5)


def test_complete_pdf_has_uniform_a4_and_embedded_vector_fonts(run,tmp_path):
    path=export_pdf([run],tmp_path/"report.pdf",annotations={run.id:{"title":"Referência Bell","objective":"Comparar métricas","notes":"Notas do pesquisador"}})
    assert_a4(path)
    assert len(media_boxes(path))>=7
    assert b"/FontFile2" in path.read_bytes()
    # Matplotlib retains text as PDF font instructions, not full-page screenshots.
    assert b"/Subtype /Type0" in path.read_bytes()


def test_report_entry_point_and_worker_share_selected_a4_compositor(qt_app,run,tmp_path):
    options={key:False for key in REPORT_SECTIONS}
    direct=export_report(run,tmp_path/"direct.pdf",options=options)
    worker=ReportWorker(run,pdf_path=tmp_path/"worker.pdf",options=options)
    completed=[]
    worker.completed.connect(completed.append)
    worker.run()
    assert completed==[str(tmp_path/"worker.pdf")]
    assert len(media_boxes(direct))==3
    assert media_boxes(direct)==media_boxes(tmp_path/"worker.pdf")


def test_current_camera_pdf_restores_live_figure_and_uses_a4(tmp_path):
    fig=figure(6,4)
    ax=fig.add_subplot(111,projection="3d")
    ax.plot([0,1],[0,0],[0,0])
    ax.view_init(elev=17,azim=43)
    fig.canvas.draw()
    old_size=fig.get_size_inches().copy()
    old_position=ax.get_position().bounds
    old_texts=list(fig.texts)
    old_artists=list(fig.artists)
    path=export_figure_a4(fig,tmp_path/"camera.pdf")
    assert_a4(path)
    np.testing.assert_allclose(fig.get_size_inches(),old_size)
    np.testing.assert_allclose(ax.get_position().bounds,old_position)
    assert (ax.elev,ax.azim)==(17,43)
    assert list(fig.texts)==old_texts
    assert list(fig.artists)==old_artists


def test_pdf_cancellation_preserves_previous_destination(run,tmp_path):
    path=tmp_path/"existing.pdf"
    path.write_bytes(b"previous report")
    with pytest.raises(SimulationCancelled):
        export_pdf([run],path,is_cancelled=lambda:True)
    assert path.read_bytes()==b"previous report"
    assert list(tmp_path.iterdir())==[path]


def test_unlike_temporal_axes_are_never_overlaid(run):
    from core.circuit_document import CircuitDocument
    circuit=replace(run,config=replace(run.config,circuit=CircuitDocument(num_qubits=2,gates=())))
    with pytest.raises(ValueError,match="eixo"):
        temporal_figure([run,circuit])


def test_long_analysis_cells_are_bounded_and_paginated():
    data={"kind":"sweep","rows":[{"method":"method "*80,"fidelity":.99} for _ in range(25)]}
    figures=list(analysis_table_figures(data))
    assert len(figures)>1
    for fig in figures:
        table=list(fig.axes[0].tables)[0]
        assert sum(cell.get_height() for (row,col),cell in table.get_celld().items() if col==0)<1
        assert all(len(cell.get_text().get_text())<100 for cell in table.get_celld().values())
    assert data["rows"][0]["method"]=="method "*80


def test_report_sections_and_human_lineage(qt_app,run):
    page=DocumentationPage()
    page.report_template.setCurrentIndex(1)
    assert not page.report_options()["include_configuration"]
    assert page.report_options()["include_bloch"]
    page.report_sections["include_temporal"].setChecked(False)
    assert not page.report_options()["include_temporal"]
    page.set_lineage([run],[],[],{run.id:{"title":"Controle Bell"}})
    assert "Controle Bell" in page.context.text()
    assert run.id not in page.context.text()
    assert page.table.item(0,1).text()=="Controle Bell"
    saved=page.report_options()
    other=DocumentationPage()
    other.apply_report_options(saved)
    assert other.report_options()==saved
    other.close()
    page.close()


def test_report_options_reject_invalid_scientific_export_settings():
    with pytest.raises(ValueError):
        report_options({"include_bloch":"false"})
    with pytest.raises(ValueError):
        report_options({"unknown":True})
