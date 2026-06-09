import pytest
import pandas as pd
from src.data_loader import get_data
from src.insights_engine import (
    Insight,
    detect_anomalies,
    detect_concerning_trends,
    detect_benchmarking_gaps,
    detect_correlations,
    detect_opportunities,
    run_all,
    SEVERITY_ORDER,
)

VALID_CATEGORIES = {"anomaly", "trend", "benchmark", "correlation", "opportunity"}
VALID_SEVERITIES = {"high", "medium", "low"}


@pytest.fixture(scope="module")
def data():
    return get_data()

@pytest.fixture(scope="module")
def metrics(data):
    return data["metrics"]

@pytest.fixture(scope="module")
def orders(data):
    return data["orders"]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def assert_valid_insight(insight: Insight):
    assert isinstance(insight, Insight)
    assert insight.category in VALID_CATEGORIES
    assert insight.severity in VALID_SEVERITIES
    assert isinstance(insight.title, str) and len(insight.title) > 0
    assert isinstance(insight.description, str) and len(insight.description) > 0
    assert isinstance(insight.metric, str)
    assert isinstance(insight.zones, list)
    assert isinstance(insight.data, dict)


# ---------------------------------------------------------------------------
# Insight dataclass
# ---------------------------------------------------------------------------

class TestInsightDataclass:

    def test_creacion_basica(self):
        insight = Insight(
            category    = "anomaly",
            severity    = "high",
            title       = "Test",
            description = "Descripción",
            metric      = "Gross Profit UE",
        )
        assert insight.zones == []
        assert insight.data  == {}

    def test_categoria_invalida_no_rompe(self):
        insight = Insight(
            category    = "custom",
            severity    = "low",
            title       = "T",
            description = "D",
            metric      = "M",
        )
        assert insight.category == "custom"


# ---------------------------------------------------------------------------
# Anomalías
# ---------------------------------------------------------------------------

class TestDetectAnomalies:

    def test_retorna_lista(self, metrics):
        result = detect_anomalies(metrics)
        assert isinstance(result, list)

    def test_detecta_al_menos_una_anomalia(self, metrics):
        result = detect_anomalies(metrics)
        assert len(result) > 0, "Debería haber anomalías en el dataset"

    def test_cada_insight_es_valido(self, metrics):
        result = detect_anomalies(metrics)
        for ins in result[:20]:
            assert_valid_insight(ins)

    def test_categoria_correcta(self, metrics):
        result = detect_anomalies(metrics)
        for ins in result:
            assert ins.category == "anomaly"

    def test_data_tiene_campos_requeridos(self, metrics):
        result = detect_anomalies(metrics)
        for ins in result[:10]:
            assert "l0w" in ins.data
            assert "l1w" in ins.data
            assert "change" in ins.data

    def test_threshold_mayor_reduce_resultados(self, metrics):
        default = detect_anomalies(metrics, rel_threshold=0.10)
        strict  = detect_anomalies(metrics, rel_threshold=0.50)
        assert len(strict) <= len(default)


# ---------------------------------------------------------------------------
# Tendencias
# ---------------------------------------------------------------------------

class TestDetectConcerningTrends:

    def test_retorna_lista(self, metrics):
        result = detect_concerning_trends(metrics)
        assert isinstance(result, list)

    def test_detecta_tendencias(self, metrics):
        result = detect_concerning_trends(metrics, n_weeks=2)
        assert len(result) > 0

    def test_cada_insight_es_valido(self, metrics):
        result = detect_concerning_trends(metrics)
        for ins in result[:20]:
            assert_valid_insight(ins)

    def test_categoria_correcta(self, metrics):
        result = detect_concerning_trends(metrics)
        for ins in result:
            assert ins.category == "trend"

    def test_data_tiene_campos_requeridos(self, metrics):
        result = detect_concerning_trends(metrics)
        for ins in result[:10]:
            assert "weeks_down" in ins.data
            assert "slope" in ins.data
            assert "current_value" in ins.data

    def test_mas_semanas_reduce_resultados(self, metrics):
        r3 = detect_concerning_trends(metrics, n_weeks=3)
        r5 = detect_concerning_trends(metrics, n_weeks=5)
        assert len(r5) <= len(r3)


# ---------------------------------------------------------------------------
# Benchmarking
# ---------------------------------------------------------------------------

class TestDetectBenchmarkingGaps:

    def test_retorna_lista(self, metrics):
        result = detect_benchmarking_gaps(metrics)
        assert isinstance(result, list)

    def test_detecta_gaps(self, metrics):
        result = detect_benchmarking_gaps(metrics, std_threshold=1.0)
        assert len(result) > 0

    def test_cada_insight_es_valido(self, metrics):
        result = detect_benchmarking_gaps(metrics)
        for ins in result[:20]:
            assert_valid_insight(ins)

    def test_categoria_correcta(self, metrics):
        result = detect_benchmarking_gaps(metrics)
        for ins in result:
            assert ins.category == "benchmark"

    def test_data_tiene_campos_requeridos(self, metrics):
        result = detect_benchmarking_gaps(metrics, std_threshold=1.0)
        for ins in result[:10]:
            assert "group_mean"  in ins.data
            assert "zone_value"  in ins.data
            assert "sigmas_below" in ins.data

    def test_threshold_mayor_reduce_resultados(self, metrics):
        r1 = detect_benchmarking_gaps(metrics, std_threshold=1.0)
        r2 = detect_benchmarking_gaps(metrics, std_threshold=2.0)
        assert len(r2) <= len(r1)


# ---------------------------------------------------------------------------
# Correlaciones
# ---------------------------------------------------------------------------

class TestDetectCorrelations:

    def test_retorna_lista(self, metrics):
        result = detect_correlations(metrics)
        assert isinstance(result, list)

    def test_detecta_correlaciones(self, metrics):
        result = detect_correlations(metrics, corr_threshold=0.40)
        assert len(result) > 0

    def test_cada_insight_es_valido(self, metrics):
        result = detect_correlations(metrics)
        for ins in result:
            assert_valid_insight(ins)

    def test_categoria_correcta(self, metrics):
        result = detect_correlations(metrics)
        for ins in result:
            assert ins.category == "correlation"

    def test_data_tiene_campos_requeridos(self, metrics):
        result = detect_correlations(metrics, corr_threshold=0.40)
        for ins in result[:10]:
            assert "metric_1"    in ins.data
            assert "metric_2"    in ins.data
            assert "correlation" in ins.data

    def test_correlacion_dentro_de_rango(self, metrics):
        result = detect_correlations(metrics, corr_threshold=0.40)
        for ins in result:
            corr = abs(ins.data["correlation"])
            assert 0.0 <= corr <= 1.0

    def test_no_duplica_pares(self, metrics):
        result = detect_correlations(metrics, corr_threshold=0.40)
        pares = [tuple(sorted([ins.data["metric_1"], ins.data["metric_2"]])) for ins in result]
        assert len(pares) == len(set(pares)), "Hay pares de métricas duplicados"


# ---------------------------------------------------------------------------
# Oportunidades
# ---------------------------------------------------------------------------

class TestDetectOpportunities:

    def test_retorna_lista(self, metrics, orders):
        result = detect_opportunities(metrics, orders)
        assert isinstance(result, list)

    def test_cada_insight_es_valido(self, metrics, orders):
        result = detect_opportunities(metrics, orders)
        for ins in result[:20]:
            assert_valid_insight(ins)

    def test_categoria_correcta(self, metrics, orders):
        result = detect_opportunities(metrics, orders)
        for ins in result:
            assert ins.category == "opportunity"

    def test_data_tiene_campos_requeridos(self, metrics, orders):
        result = detect_opportunities(metrics, orders)
        for ins in result[:10]:
            assert "orders_slope"  in ins.data
            assert "weak_metrics"  in ins.data
            assert "country"       in ins.data

    def test_ordenado_por_slope_descendente(self, metrics, orders):
        result = detect_opportunities(metrics, orders)
        if len(result) >= 2:
            slopes = [ins.data["orders_slope"] for ins in result]
            assert slopes == sorted(slopes, reverse=True)


# ---------------------------------------------------------------------------
# run_all
# ---------------------------------------------------------------------------

class TestRunAll:

    def test_retorna_lista(self, data):
        result = run_all(data)
        assert isinstance(result, list)

    def test_contiene_todas_las_categorias(self, data):
        result = run_all(data)
        categorias = {ins.category for ins in result}
        assert categorias == VALID_CATEGORIES

    def test_ordenado_por_severidad(self, data):
        result = run_all(data)
        orders_num = [SEVERITY_ORDER.get(ins.severity, 99) for ins in result]
        assert orders_num == sorted(orders_num)

    def test_cantidad_razonable_de_insights(self, data):
        result = run_all(data)
        assert 10 <= len(result) <= 5000

    def test_todos_los_insights_son_validos(self, data):
        result = run_all(data)
        for ins in result:
            assert_valid_insight(ins)
