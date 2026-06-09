import pandas as pd
import numpy as np
from dataclasses import dataclass, field
from typing import Optional
from src.data_loader import WEEK_COLS, ORDER_COLS


@dataclass
class Insight:
    category:    str            # anomaly | trend | benchmark | correlation | opportunity
    severity:    str            # high | medium | low
    title:       str
    description: str
    metric:      str
    zones:       list[str]      = field(default_factory=list)
    data:        dict           = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _consecutive_decreases(values: list[float], n: int) -> bool:
    """Retorna True si hay n o más decrementos consecutivos al final de la serie."""
    clean = [v for v in values if not (v is None or (isinstance(v, float) and np.isnan(v)))]
    if len(clean) < n:
        return False
    tail = clean[-n:]
    return all(tail[i] > tail[i + 1] for i in range(len(tail) - 1))


def _slope(values: list[float]) -> float:
    """Pendiente de regresión lineal simple. Ignora NaN."""
    y = np.array(values, dtype=float)
    x = np.arange(len(y), dtype=float)
    valid = ~np.isnan(y)
    if valid.sum() < 2:
        return 0.0
    return float(np.polyfit(x[valid], y[valid], 1)[0])


def _pct_change(old: float, new: float) -> Optional[float]:
    """Cambio porcentual entre dos valores. None si no se puede calcular."""
    if pd.isna(old) or pd.isna(new) or old == 0:
        return None
    return (new - old) / abs(old)


# ---------------------------------------------------------------------------
# 1. Anomalías
# ---------------------------------------------------------------------------

def detect_anomalies(
    df: pd.DataFrame,
    rel_threshold: float = 0.10,
    abs_threshold: float = 1.5,
) -> list[Insight]:
    """
    Detecta cambios bruscos entre L1W y L0W.

    Para métricas de proporción (CVRs, entre 0 y 1):
      usa cambio relativo > rel_threshold (10%).
    Para métricas de magnitud (Gross Profit UE):
      usa cambio absoluto > abs_threshold.
    """
    insights = []

    proportion_metrics = {
        "Retail SST > SS CVR",
        "Restaurants SST > SS CVR",
        "Restaurants SS > ATC CVR",
        "Non-Pro PTC > OP",
        "Lead Penetration",
        "Pro Adoption (Last Week Status)",
        "% PRO Users Who Breakeven",
        "% Restaurants Sessions With Optimal Assortment",
        "MLTV Top Verticals Adoption",
        "Restaurants Markdowns / GMV",
        "Turbo Adoption",
        "Perfect Orders",
    }

    subset = df.dropna(subset=["L0W_ROLL", "L1W_ROLL"])

    for _, row in subset.iterrows():
        l0 = row["L0W_ROLL"]
        l1 = row["L1W_ROLL"]
        metric = row["METRIC"]
        zone   = row["ZONE"]

        if metric in proportion_metrics:
            change = _pct_change(l1, l0)
            if change is None:
                continue
            is_anomaly = abs(change) >= rel_threshold
            severity   = "high" if abs(change) >= 0.30 else "medium"
            change_str = f"{change:+.1%}"
        else:
            change = l0 - l1
            is_anomaly = abs(change) >= abs_threshold
            severity   = "high" if abs(change) >= 3.0 else "medium"
            change_str = f"{change:+.2f}"

        if not is_anomaly:
            continue

        direction = "subió" if change > 0 else "bajó"
        insights.append(Insight(
            category    = "anomaly",
            severity    = severity,
            title       = f"Anomalía en {metric} — {zone}",
            description = (
                f"{zone} ({row['COUNTRY']}) {direction} {change_str} en {metric} "
                f"de {l1:.3f} a {l0:.3f} entre la semana pasada y la actual."
            ),
            metric      = metric,
            zones       = [zone],
            data        = {
                "country"   : row["COUNTRY"],
                "city"      : row["CITY"],
                "zone_type" : row["ZONE_TYPE"],
                "l1w"       : round(l1, 4),
                "l0w"       : round(l0, 4),
                "change"    : change_str,
            },
        ))

    return insights


# ---------------------------------------------------------------------------
# 2. Tendencias preocupantes
# ---------------------------------------------------------------------------

def detect_concerning_trends(
    df: pd.DataFrame,
    n_weeks: int = 3,
) -> list[Insight]:
    """
    Detecta zonas con n_weeks o más semanas consecutivas de deterioro.
    Solo evalúa métricas donde más alto es mejor.
    """
    # Métricas donde un valor más bajo es peor
    higher_is_better = {
        "Gross Profit UE",
        "Lead Penetration",
        "Perfect Orders",
        "Retail SST > SS CVR",
        "Restaurants SST > SS CVR",
        "Restaurants SS > ATC CVR",
        "Non-Pro PTC > OP",
        "Pro Adoption (Last Week Status)",
        "MLTV Top Verticals Adoption",
        "Turbo Adoption",
    }

    insights = []

    for _, row in df.iterrows():
        metric = row["METRIC"]
        if metric not in higher_is_better:
            continue

        values = [row[c] for c in WEEK_COLS]

        if not _consecutive_decreases(values, n_weeks):
            continue

        clean   = [v for v in values if not pd.isna(v)]
        slope   = _slope(clean[-n_weeks:]) if len(clean) >= n_weeks else 0.0
        current = clean[-1] if clean else None

        severity = "high" if abs(slope) > 0.5 else "medium"

        insights.append(Insight(
            category    = "trend",
            severity    = severity,
            title       = f"Deterioro sostenido en {metric} — {row['ZONE']}",
            description = (
                f"{row['ZONE']} ({row['COUNTRY']}) lleva {n_weeks}+ semanas "
                f"consecutivas de caída en {metric}. "
                f"Valor actual: {current:.3f}. Pendiente: {slope:.3f}/semana."
            ),
            metric      = metric,
            zones       = [row["ZONE"]],
            data        = {
                "country"      : row["COUNTRY"],
                "city"         : row["CITY"],
                "zone_type"    : row["ZONE_TYPE"],
                "prioritization": row["ZONE_PRIORITIZATION"],
                "current_value": round(current, 4) if current else None,
                "slope"        : round(slope, 4),
                "weeks_down"   : n_weeks,
            },
        ))

    return insights


# ---------------------------------------------------------------------------
# 3. Benchmarking
# ---------------------------------------------------------------------------

def detect_benchmarking_gaps(
    df: pd.DataFrame,
    week: str = "L0W_ROLL",
    std_threshold: float = 1.5,
) -> list[Insight]:
    """
    Detecta zonas del mismo país y tipo que rinden significativamente
    por debajo de sus pares (más de std_threshold desviaciones estándar).
    """
    insights = []
    group_cols = ["COUNTRY", "ZONE_TYPE", "METRIC"]

    subset = df.dropna(subset=[week])

    for (country, zone_type, metric), group in subset.groupby(group_cols):
        if len(group) < 4:
            continue

        mean = group[week].mean()
        std  = group[week].std()

        if std < 1e-6:
            continue

        underperformers = group[group[week] < mean - std_threshold * std]

        for _, row in underperformers.iterrows():
            gap      = row[week] - mean
            severity = "high" if abs(gap) > 2 * std else "medium"

            insights.append(Insight(
                category    = "benchmark",
                severity    = severity,
                title       = f"Underperformer: {row['ZONE']} vs pares en {metric}",
                description = (
                    f"{row['ZONE']} ({country}, {zone_type}) tiene {metric} = "
                    f"{row[week]:.3f}, mientras el promedio de zonas similares "
                    f"es {mean:.3f} (diferencia: {gap:+.3f}, "
                    f"{abs(gap)/std:.1f}σ por debajo)."
                ),
                metric      = metric,
                zones       = [row["ZONE"]],
                data        = {
                    "country"       : country,
                    "zone_type"     : zone_type,
                    "zone_value"    : round(row[week], 4),
                    "group_mean"    : round(mean, 4),
                    "group_std"     : round(std, 4),
                    "gap"           : round(gap, 4),
                    "sigmas_below"  : round(abs(gap) / std, 2),
                    "peer_count"    : len(group),
                },
            ))

    return insights


# ---------------------------------------------------------------------------
# 4. Correlaciones
# ---------------------------------------------------------------------------

def detect_correlations(
    df: pd.DataFrame,
    week: str = "L0W_ROLL",
    corr_threshold: float = 0.60,
) -> list[Insight]:
    """
    Construye una matriz de correlación entre métricas a nivel de zona
    y reporta pares con correlación fuerte (positiva o negativa).
    """
    pivot = (
        df.dropna(subset=[week])
        .pivot_table(index=["COUNTRY", "CITY", "ZONE"], columns="METRIC", values=week)
        .reset_index()
    )

    metric_cols = [c for c in pivot.columns if c not in ["COUNTRY", "CITY", "ZONE"]]

    if len(metric_cols) < 2:
        return []

    corr_matrix = pivot[metric_cols].corr()

    insights = []
    reported  = set()

    for i, m1 in enumerate(metric_cols):
        for m2 in metric_cols[i + 1:]:
            pair = tuple(sorted([m1, m2]))
            if pair in reported:
                continue

            corr = corr_matrix.loc[m1, m2]
            if pd.isna(corr) or abs(corr) < corr_threshold:
                continue

            reported.add(pair)
            direction = "positiva" if corr > 0 else "negativa"
            severity  = "high" if abs(corr) >= 0.75 else "medium"

            if corr > 0:
                description = (
                    f"Las zonas con mayor {m1} tienden a tener también mayor {m2} "
                    f"(correlación {direction}: r = {corr:.2f})."
                )
            else:
                description = (
                    f"Las zonas con mayor {m1} tienden a tener menor {m2} "
                    f"(correlación {direction}: r = {corr:.2f})."
                )

            insights.append(Insight(
                category    = "correlation",
                severity    = severity,
                title       = f"Correlación {direction} entre {m1} y {m2}",
                description = description,
                metric      = f"{m1} × {m2}",
                zones       = [],
                data        = {
                    "metric_1"    : m1,
                    "metric_2"    : m2,
                    "correlation" : round(corr, 4),
                    "direction"   : direction,
                },
            ))

    return insights


# ---------------------------------------------------------------------------
# 5. Oportunidades
# ---------------------------------------------------------------------------

def detect_opportunities(
    df: pd.DataFrame,
    orders_df: pd.DataFrame,
    n_weeks: int = 5,
    growth_threshold: float = 0.0,
    weak_pct: float = 0.35,
) -> list[Insight]:
    """
    Detecta zonas con órdenes creciendo pero métricas operacionales débiles.
    Estas son zonas con demanda pero con margen de mejora operacional.
    """
    order_cols_used = ORDER_COLS[-n_weeks:]

    # Calcular slope de órdenes por zona
    def calc_slope(row):
        y = [row[c] for c in order_cols_used]
        return _slope(y)

    orders_copy = orders_df.copy()
    orders_copy["orders_slope"] = orders_copy.apply(calc_slope, axis=1)

    growing_zones = orders_copy[
        orders_copy["orders_slope"] > growth_threshold
    ][["COUNTRY", "CITY", "ZONE", "orders_slope", "L0W"]].copy()

    growing_zones = growing_zones.rename(columns={"L0W": "orders_l0w"})

    if growing_zones.empty:
        return []

    # Métricas operacionales clave a revisar
    key_metrics = [
        "Gross Profit UE",
        "Perfect Orders",
        "Lead Penetration",
    ]

    insights = []

    for _, zone_row in growing_zones.iterrows():
        zone    = zone_row["ZONE"]
        country = zone_row["COUNTRY"]

        zone_metrics = df[
            (df["ZONE"] == zone) &
            (df["COUNTRY"] == country) &
            (df["METRIC"].isin(key_metrics))
        ]

        if zone_metrics.empty:
            continue

        weak_metrics = []

        for _, m_row in zone_metrics.iterrows():
            metric = m_row["METRIC"]
            value  = m_row["L0W_ROLL"]

            if pd.isna(value):
                continue

            country_vals = df[
                (df["METRIC"] == metric) &
                (df["COUNTRY"] == country)
            ]["L0W_ROLL"].dropna()

            if country_vals.empty:
                continue

            percentile = (country_vals < value).mean()

            if percentile <= weak_pct:
                weak_metrics.append({
                    "metric"    : metric,
                    "value"     : round(value, 4),
                    "percentile": round(percentile * 100, 1),
                })

        if not weak_metrics:
            continue

        weak_names = ", ".join(m["metric"] for m in weak_metrics)

        insights.append(Insight(
            category    = "opportunity",
            severity    = "medium",
            title       = f"Oportunidad: {zone} crece en órdenes pero falla en operación",
            description = (
                f"{zone} ({country}) muestra crecimiento en órdenes "
                f"(pendiente: {zone_row['orders_slope']:+.1f} órdenes/semana) "
                f"pero tiene métricas débiles en: {weak_names}. "
                f"Hay demanda — el foco debería ser mejorar la operación."
            ),
            metric      = "Orders + " + weak_names,
            zones       = [zone],
            data        = {
                "country"      : country,
                "city"         : zone_row["CITY"],
                "orders_slope" : round(zone_row["orders_slope"], 2),
                "orders_l0w"   : zone_row["orders_l0w"],
                "weak_metrics" : weak_metrics,
            },
        ))

    return sorted(insights, key=lambda x: x.data["orders_slope"], reverse=True)


# ---------------------------------------------------------------------------
# Runner principal
# ---------------------------------------------------------------------------

SEVERITY_ORDER = {"high": 0, "medium": 1, "low": 2}


def run_all(data: dict) -> list[Insight]:
    """
    Corre los cinco detectores y retorna todos los insights
    ordenados por severidad (high primero).
    """
    metrics   = data["metrics"]
    orders    = data["orders"]

    all_insights = []
    all_insights.extend(detect_anomalies(metrics))
    all_insights.extend(detect_concerning_trends(metrics))
    all_insights.extend(detect_benchmarking_gaps(metrics))
    all_insights.extend(detect_correlations(metrics))
    all_insights.extend(detect_opportunities(metrics, orders))

    all_insights.sort(key=lambda x: SEVERITY_ORDER.get(x.severity, 99))

    return all_insights
