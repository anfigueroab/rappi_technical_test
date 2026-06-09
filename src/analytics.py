import pandas as pd
import numpy as np
from src.data_loader import WEEK_COLS, ORDER_COLS


def top_zones_by_metric(
    df: pd.DataFrame,
    metric: str,
    week: str = "L0W_ROLL",
    n: int = 5,
    ascending: bool = False,
    country: str = None,
) -> pd.DataFrame:
    """
    '¿Cuáles son las 5 zonas con mayor Lead Penetration esta semana?'

    Retorna un DataFrame con columnas:
      COUNTRY, CITY, ZONE, ZONE_TYPE, ZONE_PRIORITIZATION, <week>, METRIC
    ordenado por el valor de la semana pedida.
    """
    mask = df["METRIC"] == metric
    if country:
        mask &= df["COUNTRY"] == country

    result = (
        df[mask][["COUNTRY", "CITY", "ZONE", "ZONE_TYPE", "ZONE_PRIORITIZATION", week]]
        .dropna(subset=[week])
        .sort_values(week, ascending=ascending)
        .head(n)
        .reset_index(drop=True)
    )
    result["METRIC"] = metric
    return result


def compare_by_zone_type(
    df: pd.DataFrame,
    metric: str,
    country: str = None,
    week: str = "L0W_ROLL",
) -> pd.DataFrame:
    """
    'Compara el Perfect Order entre zonas Wealthy y Non Wealthy en México'

    Retorna tabla con media, mediana, std y conteo por ZONE_TYPE.
    """
    mask = df["METRIC"] == metric
    if country:
        mask &= df["COUNTRY"] == country

    result = (
        df[mask]
        .groupby("ZONE_TYPE")[week]
        .agg(
            media="mean",
            mediana="median",
            std="std",
            zonas="count",
        )
        .round(4)
        .reset_index()
    )
    result["METRIC"] = metric
    if country:
        result["COUNTRY"] = country
    return result


def trend_for_zone(
    df: pd.DataFrame,
    zone: str,
    metric: str,
    country: str = None,
) -> pd.DataFrame:
    """
    'Muestra la evolución de Gross Profit UE en Chapinero las últimas 8 semanas'

    Retorna un DataFrame en formato largo con columnas:
      semana, valor, semana_num
    Listo para graficar directamente.
    """
    mask = (df["ZONE"] == zone) & (df["METRIC"] == metric)
    if country:
        mask &= df["COUNTRY"] == country

    subset = df[mask]

    if subset.empty:
        return pd.DataFrame(columns=["semana", "valor", "semana_num"])

    # Si hay más de una fila (duplicados residuales) promediamos
    valores = subset[WEEK_COLS].mean(numeric_only=True)

    result = pd.DataFrame({
        "semana"    : WEEK_COLS,
        "valor"     : valores.values,
        "semana_num": list(range(-8, 1)),  # -8 = hace 8 semanas, 0 = actual
    })
    result["ZONE"]   = zone
    result["METRIC"] = metric
    return result


def average_by_country(
    df: pd.DataFrame,
    metric: str,
    week: str = "L0W_ROLL",
) -> pd.DataFrame:
    """
    '¿Cuál es el promedio de Lead Penetration por país?'

    Retorna media por país, ordenada de mayor a menor.
    """
    mask = df["METRIC"] == metric

    result = (
        df[mask]
        .groupby("COUNTRY")[week]
        .mean()
        .round(4)
        .reset_index()
        .rename(columns={week: "promedio"})
        .sort_values("promedio", ascending=False)
        .reset_index(drop=True)
    )
    result["METRIC"] = metric
    return result


def high_low_analysis(
    df: pd.DataFrame,
    high_metric: str,
    low_metric: str,
    week: str = "L0W_ROLL",
    high_pct: float = 0.75,
    low_pct: float = 0.25,
    country: str = None,
) -> pd.DataFrame:
    """
    '¿Qué zonas tienen alto Lead Penetration pero bajo Perfect Order?'

    Usa percentiles para definir alto/bajo si no se dan thresholds.
    Retorna zonas que cumplen ambas condiciones simultáneamente.
    """
    def get_values(metric):
        mask = df["METRIC"] == metric
        if country:
            mask &= df["COUNTRY"] == country
        return (
            df[mask][["COUNTRY", "CITY", "ZONE", week]]
            .dropna(subset=[week])
            .rename(columns={week: metric})
        )

    high_df = get_values(high_metric)
    low_df  = get_values(low_metric)

    combined = high_df.merge(low_df, on=["COUNTRY", "CITY", "ZONE"], how="inner")

    if combined.empty:
        return combined

    high_threshold = combined[high_metric].quantile(high_pct)
    low_threshold  = combined[low_metric].quantile(low_pct)

    result = combined[
        (combined[high_metric] >= high_threshold) &
        (combined[low_metric]  <= low_threshold)
    ].sort_values(high_metric, ascending=False).reset_index(drop=True)

    result["high_metric"] = high_metric
    result["low_metric"]  = low_metric
    return result


def growth_analysis(
    df: pd.DataFrame,
    n_weeks: int = 5,
    country: str = None,
    min_orders: float = None,
    orders_df: pd.DataFrame = None,
) -> pd.DataFrame:
    """
    'Zonas que más crecen en órdenes en las últimas 5 semanas'

    Calcula la pendiente (slope) de regresión lineal sobre las últimas
    n_weeks semanas de órdenes. Una pendiente positiva = crecimiento sostenido.

    Si se pasa orders_df y min_orders, filtra zonas con pocas órdenes
    para evitar ruido estadístico.

    Retorna DataFrame con columnas:
      COUNTRY, CITY, ZONE, slope, pct_change, orders_L0W
    ordenado de mayor a menor crecimiento.
    """
    # Usar las últimas n_weeks columnas de órdenes
    cols_used = ORDER_COLS[-n_weeks:]

    target = df.copy()
    if country:
        target = target[target["COUNTRY"] == country]

    # Filtro por volumen mínimo de órdenes
    if orders_df is not None and min_orders is not None:
        zonas_validas = (
            orders_df[orders_df["L0W"] >= min_orders]["ZONE"].unique()
        )
        target = target[target["ZONE"].isin(zonas_validas)]

    if target.empty:
        return pd.DataFrame(
            columns=["COUNTRY", "CITY", "ZONE", "slope", "pct_change", "orders_L0W"]
        )

    # Calcular slope por zona
    x = np.arange(n_weeks, dtype=float)

    def calc_slope(row):
        y = row[cols_used].values.astype(float)
        valid = ~np.isnan(y)
        if valid.sum() < 2:
            return np.nan
        return float(np.polyfit(x[valid], y[valid], 1)[0])

    def calc_pct_change(row):
        first = row[cols_used[0]]
        last  = row[cols_used[-1]]
        if pd.isna(first) or pd.isna(last) or first == 0:
            return np.nan
        return round((last - first) / abs(first) * 100, 2)

    target = target.copy()
    target["slope"]      = target.apply(calc_slope, axis=1)
    target["pct_change"] = target.apply(calc_pct_change, axis=1)

    # Renombrar L0W a orders_L0W para claridad
    if "L0W" in target.columns:
        target = target.rename(columns={"L0W": "orders_L0W"})

    keep_cols = ["COUNTRY", "CITY", "ZONE", "slope", "pct_change"]
    if "orders_L0W" in target.columns:
        keep_cols.append("orders_L0W")

    result = (
        target[keep_cols]
        .dropna(subset=["slope"])
        .sort_values("slope", ascending=False)
        .reset_index(drop=True)
    )
    return result


def filter_zones(
    df: pd.DataFrame,
    country: str = None,
    zone_type: str = None,
    prioritization: str = None,
    metric: str = None,
    week: str = "L0W_ROLL",
) -> pd.DataFrame:
    """
    Filtro genérico reutilizable por todos los demás análisis.
    Cualquier parámetro None se ignora.
    """
    mask = pd.Series(True, index=df.index)

    if country:
        mask &= df["COUNTRY"] == country
    if zone_type:
        mask &= df["ZONE_TYPE"] == zone_type
    if prioritization:
        mask &= df["ZONE_PRIORITIZATION"] == prioritization
    if metric:
        mask &= df["METRIC"] == metric

    result = df[mask].copy()

    if week in result.columns:
        result = result.dropna(subset=[week])

    return result.reset_index(drop=True)