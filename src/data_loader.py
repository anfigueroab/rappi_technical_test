import pandas as pd
import numpy as np
from pathlib import Path

DATA_PATH = Path(__file__).parent.parent / "data" / "datos_rappi.xlsx"

WEEK_COLS = [
    "L8W_ROLL", "L7W_ROLL", "L6W_ROLL", "L5W_ROLL",
    "L4W_ROLL", "L3W_ROLL", "L2W_ROLL", "L1W_ROLL", "L0W_ROLL"
]

ORDER_COLS = ["L8W", "L7W", "L6W", "L5W", "L4W", "L3W", "L2W", "L1W", "L0W"]

ID_COLS = ["COUNTRY", "CITY", "ZONE", "ZONE_TYPE", "ZONE_PRIORITIZATION", "METRIC"]
GEO_COLS = ["COUNTRY", "CITY", "ZONE"]


def _load_raw(path: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    metrics = pd.read_excel(path, sheet_name="RAW_INPUT_METRICS", engine="openpyxl")
    orders  = pd.read_excel(path, sheet_name="RAW_ORDERS",        engine="openpyxl")
    return metrics, orders


def _clean_metrics(df: pd.DataFrame) -> pd.DataFrame:
    # 1. Normalizar nombres de columnas (quitar espacios)
    df.columns = df.columns.str.strip()

    # 2. Castear columnas semana a float
    for col in WEEK_COLS:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # 3. Eliminar duplicados exactos
    df = df.drop_duplicates()

    # 4. Resolver duplicados parciales: misma zona+métrica, valores distintos
    #    Estrategia: promediar las columnas numéricas, quedarse con el
    #    primer valor de las columnas categóricas
    id_key = ["COUNTRY", "CITY", "ZONE", "METRIC"]
    has_duplicates = df.duplicated(subset=id_key, keep=False)

    if has_duplicates.any():
        cat_cols  = ["ZONE_TYPE", "ZONE_PRIORITIZATION"]
        num_cols  = [c for c in WEEK_COLS if c in df.columns]

        cat_part = (
            df[id_key + cat_cols]
            .groupby(id_key, as_index=False)
            .first()
        )
        num_part = (
            df[id_key + num_cols]
            .groupby(id_key, as_index=False)
            .mean(numeric_only=True)
        )
        df = cat_part.merge(num_part, on=id_key, how="left")

    # 5. Resetear índice
    df = df.reset_index(drop=True)
    return df


def _clean_orders(df: pd.DataFrame) -> pd.DataFrame:
    df.columns = df.columns.str.strip()

    for col in ORDER_COLS:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    df = df.drop_duplicates()

    id_key = ["COUNTRY", "CITY", "ZONE", "METRIC"]
    has_duplicates = df.duplicated(subset=id_key, keep=False)

    if has_duplicates.any():
        num_cols = [c for c in ORDER_COLS if c in df.columns]
        df = (
            df[id_key + num_cols]
            .groupby(id_key, as_index=False)
            .mean(numeric_only=True)
        )

    df = df.reset_index(drop=True)
    return df


def _build_merged(metrics: pd.DataFrame, orders: pd.DataFrame) -> pd.DataFrame:
    """
    Agrega columnas de órdenes al DataFrame de métricas.
    Útil para contextualizar: ¿es una zona grande o chica?
    Las columnas de órdenes se renombran a orders_L0W, orders_L1W, etc.
    """
    orders_slim = orders[GEO_COLS + ORDER_COLS].copy()
    rename_map  = {col: f"orders_{col}" for col in ORDER_COLS}
    orders_slim = orders_slim.rename(columns=rename_map)

    merged = metrics.merge(orders_slim, on=GEO_COLS, how="left")
    return merged


def get_data() -> dict:
    """
    Función principal del módulo.

    Retorna un diccionario con:
      - metrics  : DataFrame limpio de RAW_INPUT_METRICS
      - orders   : DataFrame limpio de RAW_ORDERS
      - merged   : métricas + columnas de órdenes
      - metric_names : lista de métricas únicas disponibles
      - countries    : lista de países únicos
      - zones        : lista de zonas únicas
      - week_cols    : nombres de las columnas semana (métricas)
      - order_cols   : nombres de las columnas semana (órdenes)
    """
    raw_metrics, raw_orders = _load_raw(DATA_PATH)

    metrics = _clean_metrics(raw_metrics)
    orders  = _clean_orders(raw_orders)
    merged  = _build_merged(metrics, orders)

    return {
        "metrics"      : metrics,
        "orders"       : orders,
        "merged"       : merged,
        "metric_names" : sorted(metrics["METRIC"].dropna().unique().tolist()),
        "countries"    : sorted(metrics["COUNTRY"].dropna().unique().tolist()),
        "zones"        : sorted(metrics["ZONE"].dropna().unique().tolist()),
        "week_cols"    : WEEK_COLS,
        "order_cols"   : ORDER_COLS,
    }
