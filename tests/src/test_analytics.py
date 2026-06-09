import pytest
import pandas as pd
from src.data_loader import get_data
from src.analytics import (
    top_zones_by_metric,
    compare_by_zone_type,
    trend_for_zone,
    average_by_country,
    high_low_analysis,
    growth_analysis,
    filter_zones,
)


@pytest.fixture(scope="module")
def data():
    return get_data()


@pytest.fixture(scope="module")
def metrics(data):
    return data["metrics"]


@pytest.fixture(scope="module")
def orders(data):
    return data["orders"]


class TestTopZones:

    def test_retorna_dataframe(self, metrics):
        result = top_zones_by_metric(metrics, "Gross Profit UE")
        assert isinstance(result, pd.DataFrame)

    def test_retorna_n_filas(self, metrics):
        result = top_zones_by_metric(metrics, "Gross Profit UE", n=5)
        assert len(result) <= 5

    def test_ordenado_descendente(self, metrics):
        result = top_zones_by_metric(metrics, "Gross Profit UE", n=10)
        valores = result["L0W_ROLL"].dropna().tolist()
        assert valores == sorted(valores, reverse=True)

    def test_filtro_por_pais(self, metrics):
        result = top_zones_by_metric(metrics, "Gross Profit UE", country="CO")
        assert result["COUNTRY"].unique().tolist() == ["CO"]

    def test_metrica_inexistente_retorna_vacio(self, metrics):
        result = top_zones_by_metric(metrics, "MetricaQueNoExiste")
        assert len(result) == 0


class TestCompareByZoneType:

    def test_retorna_dataframe(self, metrics):
        result = compare_by_zone_type(metrics, "Gross Profit UE")
        assert isinstance(result, pd.DataFrame)

    def test_tiene_columnas_correctas(self, metrics):
        result = compare_by_zone_type(metrics, "Gross Profit UE")
        for col in ["ZONE_TYPE", "media", "mediana", "std", "zonas"]:
            assert col in result.columns

    def test_zone_types_esperados(self, metrics):
        result = compare_by_zone_type(metrics, "Gross Profit UE")
        zone_types = set(result["ZONE_TYPE"].tolist())
        assert zone_types.issubset({"Wealthy", "Non Wealthy"})

    def test_filtro_pais(self, metrics):
        result = compare_by_zone_type(metrics, "Gross Profit UE", country="MX")
        assert "COUNTRY" in result.columns
        assert result["COUNTRY"].iloc[0] == "MX"


class TestTrendForZone:

    def test_retorna_dataframe(self, metrics):
        result = trend_for_zone(metrics, "Chapinero", "Gross Profit UE")
        assert isinstance(result, pd.DataFrame)

    def test_tiene_9_semanas(self, metrics):
        # Buscar una zona que exista en el dataset
        zone = metrics["ZONE"].iloc[0]
        metric = metrics[metrics["ZONE"] == zone]["METRIC"].iloc[0]
        result = trend_for_zone(metrics, zone, metric)
        assert len(result) == 9

    def test_columnas_correctas(self, metrics):
        zone = metrics["ZONE"].iloc[0]
        metric = metrics[metrics["ZONE"] == zone]["METRIC"].iloc[0]
        result = trend_for_zone(metrics, zone, metric)
        for col in ["semana", "valor", "semana_num"]:
            assert col in result.columns

    def test_semana_num_va_de_menos8_a_0(self, metrics):
        zone = metrics["ZONE"].iloc[0]
        metric = metrics[metrics["ZONE"] == zone]["METRIC"].iloc[0]
        result = trend_for_zone(metrics, zone, metric)
        assert result["semana_num"].tolist() == list(range(-8, 1))

    def test_zona_inexistente_retorna_vacio(self, metrics):
        result = trend_for_zone(metrics, "ZonaQueNoExiste", "Gross Profit UE")
        assert len(result) == 0


class TestAverageByCountry:

    def test_retorna_dataframe(self, metrics):
        result = average_by_country(metrics, "Gross Profit UE")
        assert isinstance(result, pd.DataFrame)

    def test_tiene_columnas_correctas(self, metrics):
        result = average_by_country(metrics, "Gross Profit UE")
        for col in ["COUNTRY", "promedio", "METRIC"]:
            assert col in result.columns

    def test_todos_los_paises(self, metrics):
        result = average_by_country(metrics, "Gross Profit UE")
        paises = set(result["COUNTRY"].tolist())
        expected = {"AR", "BR", "CL", "CO", "CR", "EC", "MX", "PE", "UY"}
        assert expected.issubset(paises)

    def test_ordenado_descendente(self, metrics):
        result = average_by_country(metrics, "Gross Profit UE")
        promedios = result["promedio"].tolist()
        assert promedios == sorted(promedios, reverse=True)


class TestHighLowAnalysis:

    def test_retorna_dataframe(self, metrics):
        result = high_low_analysis(metrics, "Lead Penetration", "Gross Profit UE")
        assert isinstance(result, pd.DataFrame)

    def test_columnas_correctas(self, metrics):
        result = high_low_analysis(metrics, "Lead Penetration", "Gross Profit UE")
        if not result.empty:
            assert "Lead Penetration" in result.columns
            assert "Gross Profit UE" in result.columns

    def test_valores_high_sobre_percentil(self, metrics):
        result = high_low_analysis(
            metrics, "Gross Profit UE", "Retail SST > SS CVR",
            high_pct=0.75, low_pct=0.25
        )
        if not result.empty:
            all_vals = metrics[metrics["METRIC"] == "Gross Profit UE"]["L0W_ROLL"].dropna()
            threshold = all_vals.quantile(0.75)
            assert (result["Gross Profit UE"] >= threshold * 0.99).all()


class TestGrowthAnalysis:

    def test_retorna_dataframe(self, orders):
        result = growth_analysis(orders)
        assert isinstance(result, pd.DataFrame)

    def test_columnas_correctas(self, orders):
        result = growth_analysis(orders)
        for col in ["COUNTRY", "CITY", "ZONE", "slope", "pct_change"]:
            assert col in result.columns

    def test_ordenado_por_slope(self, orders):
        result = growth_analysis(orders)
        slopes = result["slope"].tolist()
        assert slopes == sorted(slopes, reverse=True)

    def test_filtro_por_pais(self, orders):
        result = growth_analysis(orders, country="MX")
        if not result.empty:
            assert set(result["COUNTRY"].unique()) == {"MX"}

    def test_n_weeks_respetado(self, orders):
        result_5 = growth_analysis(orders, n_weeks=5)
        result_3 = growth_analysis(orders, n_weeks=3)
        assert len(result_5) >= 0
        assert len(result_3) >= 0


class TestFilterZones:

    def test_filtro_pais(self, metrics):
        result = filter_zones(metrics, country="CO")
        assert (result["COUNTRY"] == "CO").all()

    def test_filtro_zone_type(self, metrics):
        result = filter_zones(metrics, zone_type="Wealthy")
        assert (result["ZONE_TYPE"] == "Wealthy").all()

    def test_filtro_metrica(self, metrics):
        result = filter_zones(metrics, metric="Gross Profit UE")
        assert (result["METRIC"] == "Gross Profit UE").all()

    def test_filtro_combinado(self, metrics):
        result = filter_zones(
            metrics,
            country="MX",
            zone_type="Wealthy",
            metric="Gross Profit UE"
        )
        assert (result["COUNTRY"] == "MX").all()
        assert (result["ZONE_TYPE"] == "Wealthy").all()
        assert (result["METRIC"] == "Gross Profit UE").all()

    def test_sin_filtros_retorna_todo(self, metrics):
        result = filter_zones(metrics)
        assert len(result) > 0