import pytest
from src.data_loader import get_data
from src.insights_engine import run_all, Insight
from src.report_generator import (
    generate_html_report,
    save_report,
    _insight_card,
    _section,
    OUTPUT_PATH,
)


@pytest.fixture(scope="module")
def data():
    return get_data()

@pytest.fixture(scope="module")
def insights(data):
    return run_all(data)

@pytest.fixture(scope="module")
def html_report(insights, data):
    return generate_html_report(insights, data)


class TestInsightCard:

    def test_retorna_string(self):
        ins = Insight(
            category="anomaly", severity="high",
            title="Test", description="Descripción de prueba",
            metric="Gross Profit UE",
            zones=["Chapinero"],
            data={"country": "CO", "l0w": 2.5, "l1w": 1.0, "change": "+150%"},
        )
        result = _insight_card(ins)
        assert isinstance(result, str)

    def test_contiene_titulo(self):
        ins = Insight(
            category="anomaly", severity="high",
            title="Mi título único", description="Desc",
            metric="M",
        )
        card = _insight_card(ins)
        assert "Mi título único" in card

    def test_contiene_descripcion(self):
        ins = Insight(
            category="trend", severity="medium",
            title="T", description="Mi descripción única",
            metric="M",
        )
        card = _insight_card(ins)
        assert "Mi descripción única" in card

    def test_contiene_badge_severidad(self):
        ins = Insight(
            category="anomaly", severity="high",
            title="T", description="D", metric="M",
        )
        card = _insight_card(ins)
        assert "Alta" in card

    def test_severidades_validas_generan_html(self):
        for sev in ["high", "medium", "low"]:
            ins = Insight(
                category="anomaly", severity=sev,
                title="T", description="D", metric="M",
            )
            card = _insight_card(ins)
            assert len(card) > 0


class TestSection:

    def test_seccion_vacia_retorna_string_vacio(self):
        result = _section("anomaly", [])
        assert result == ""

    def test_seccion_con_insights_retorna_html(self):
        ins = Insight(
            category="anomaly", severity="high",
            title="T", description="D", metric="M",
        )
        result = _section("anomaly", [ins])
        assert "Anomalías" in result
        assert len(result) > 0

    def test_contiene_contador(self):
        insights = [
            Insight(category="trend", severity="medium",
                    title=f"T{i}", description="D", metric="M")
            for i in range(3)
        ]
        result = _section("trend", insights)
        assert "3" in result


class TestGenerateHtmlReport:

    def test_retorna_string(self, html_report):
        assert isinstance(html_report, str)

    def test_es_html_valido(self, html_report):
        assert "<!DOCTYPE html>" in html_report
        assert "<html" in html_report
        assert "</html>" in html_report

    def test_contiene_titulo(self, html_report):
        assert "Rappi" in html_report

    def test_contiene_resumen_ejecutivo(self, html_report):
        assert "Resumen Ejecutivo" in html_report

    def test_contiene_graficos_base64(self, html_report):
        assert "data:image/png;base64," in html_report

    def test_contiene_todas_las_secciones(self, html_report):
        assert "Anomalías" in html_report
        assert "Tendencias" in html_report
        assert "Benchmarking" in html_report
        assert "Correlaciones" in html_report
        assert "Oportunidades" in html_report

    def test_contiene_stats(self, html_report):
        assert "Total insights" in html_report
        assert "Países" in html_report

    def test_sin_insights_no_rompe(self, data):
        html = generate_html_report([], data)
        assert isinstance(html, str)
        assert "<!DOCTYPE html>" in html


class TestSaveReport:

    def test_guarda_archivo(self, html_report, tmp_path):
        path = tmp_path / "test_report.html"
        result = save_report(html_report, path)
        assert result == path
        assert path.exists()

    def test_archivo_tiene_contenido(self, html_report, tmp_path):
        path = tmp_path / "test_report.html"
        save_report(html_report, path)
        content = path.read_text(encoding="utf-8")
        assert len(content) > 1000

    def test_archivo_es_utf8(self, html_report, tmp_path):
        path = tmp_path / "test_report.html"
        save_report(html_report, path)
        content = path.read_text(encoding="utf-8")
        assert "utf-8" in content.lower() or "UTF-8" in content
