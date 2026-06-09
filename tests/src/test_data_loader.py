import pytest
import pandas as pd
from src.data_loader import get_data, WEEK_COLS, ORDER_COLS

EXPECTED_COUNTRIES = {"AR", "BR", "CL", "CO", "CR", "EC", "MX", "PE", "UY"}
EXPECTED_METRICS = {
    "Gross Profit UE",
    "Lead Penetration",
    "Perfect Orders",
    "Retail SST > SS CVR",
    "Restaurants SST > SS CVR",
    "Restaurants SS > ATC CVR",
    "Non-Pro PTC > OP",
    "Pro Adoption (Last Week Status)",
    "% PRO Users Who Breakeven",
    "% Restaurants Sessions With Optimal Assortment",
    "MLTV Top Verticals Adoption",
    "Restaurants Markdowns / GMV",
    "Turbo Adoption",
}


@pytest.fixture(scope="module")
def data():
    """Carga los datos una sola vez para todos los tests del módulo."""
    return get_data()


class TestMetrics:

    def test_carga_sin_errores(self, data):
        assert data is not None

    def test_keys_presentes(self, data):
        expected_keys = {
            "metrics", "orders", "merged",
            "metric_names", "countries", "zones",
            "week_cols", "order_cols"
        }
        assert expected_keys.issubset(data.keys())

    def test_metrics_es_dataframe(self, data):
        assert isinstance(data["metrics"], pd.DataFrame)

    def test_metrics_no_vacio(self, data):
        assert len(data["metrics"]) > 0

    def test_columnas_semana_presentes(self, data):
        for col in WEEK_COLS:
            assert col in data["metrics"].columns, f"Falta columna {col}"

    def test_columnas_id_presentes(self, data):
        for col in ["COUNTRY", "CITY", "ZONE", "ZONE_TYPE", "ZONE_PRIORITIZATION", "METRIC"]:
            assert col in data["metrics"].columns, f"Falta columna {col}"

    def test_paises_correctos(self, data):
        paises_en_datos = set(data["metrics"]["COUNTRY"].unique())
        assert paises_en_datos == EXPECTED_COUNTRIES

    def test_metricas_conocidas_presentes(self, data):
        metricas_en_datos = set(data["metric_names"])
        for m in EXPECTED_METRICS:
            assert m in metricas_en_datos, f"Métrica esperada no encontrada: {m}"

    def test_sin_duplicados_exactos(self, data):
        df = data["metrics"]
        id_key = ["COUNTRY", "CITY", "ZONE", "METRIC"]
        duplicados = df.duplicated(subset=id_key, keep=False).sum()
        assert duplicados == 0, f"Hay {duplicados} filas con clave duplicada"

    def test_columnas_semana_son_numericas(self, data):
        df = data["metrics"]
        for col in WEEK_COLS:
            assert pd.api.types.is_float_dtype(df[col]), f"{col} no es float"

    def test_l0w_tiene_valores(self, data):
        nulos = data["metrics"]["L0W_ROLL"].isna().sum()
        total = len(data["metrics"])
        pct_nulos = nulos / total
        assert pct_nulos < 0.30, f"L0W_ROLL tiene {pct_nulos:.0%} nulos — demasiados"


class TestOrders:

    def test_orders_es_dataframe(self, data):
        assert isinstance(data["orders"], pd.DataFrame)

    def test_orders_no_vacio(self, data):
        assert len(data["orders"]) > 0

    def test_columnas_order_presentes(self, data):
        for col in ORDER_COLS:
            assert col in data["orders"].columns, f"Falta columna {col}"

    def test_orders_son_numericos(self, data):
        df = data["orders"]
        for col in ORDER_COLS:
            assert pd.api.types.is_float_dtype(df[col]), f"{col} no es float"

    def test_orders_no_negativos(self, data):
        df = data["orders"]
        for col in ORDER_COLS:
            min_val = df[col].min()
            assert min_val >= 0 or pd.isna(min_val), \
                f"{col} tiene valores negativos (min={min_val})"


class TestMerged:

    def test_merged_es_dataframe(self, data):
        assert isinstance(data["merged"], pd.DataFrame)

    def test_merged_tiene_columnas_orders(self, data):
        expected = [f"orders_{col}" for col in ORDER_COLS]
        for col in expected:
            assert col in data["merged"].columns, f"Falta columna {col} en merged"

    def test_merged_no_pierde_filas(self, data):
        assert len(data["merged"]) == len(data["metrics"])

    def test_merged_orders_l0w_razonables(self, data):
        col = "orders_L0W"
        valores_validos = data["merged"][col].dropna()
        assert len(valores_validos) > 0
        assert valores_validos.max() < 1_000_000, "Valor de órdenes sospechosamente alto"