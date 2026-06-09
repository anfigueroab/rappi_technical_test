import base64
from datetime import datetime
from pathlib import Path
from collections import defaultdict

import pandas as pd
import plotly.graph_objects as go
import plotly.io as pio

from src.insights_engine import Insight

OUTPUT_PATH = Path(__file__).parent.parent / "reporte_rappi.html"

CATEGORY_LABELS = {
    "anomaly"     : "Anomalías",
    "trend"       : "Tendencias Preocupantes",
    "benchmark"   : "Benchmarking",
    "correlation" : "Correlaciones",
    "opportunity" : "Oportunidades",
}

CATEGORY_ICONS = {
    "anomaly"     : "⚡",
    "trend"       : "📉",
    "benchmark"   : "📊",
    "correlation" : "🔗",
    "opportunity" : "🚀",
}

SEVERITY_COLORS = {
    "high"   : "#E24B4A",
    "medium" : "#BA7517",
    "low"    : "#3B6D11",
}

SEVERITY_BG = {
    "high"   : "#FCEBEB",
    "medium" : "#FAEEDA",
    "low"    : "#EAF3DE",
}

SEVERITY_LABELS = {
    "high"   : "Alta",
    "medium" : "Media",
    "low"    : "Baja",
}


# ---------------------------------------------------------------------------
# Gráficos
# ---------------------------------------------------------------------------

def _fig_to_base64(fig: go.Figure) -> str:
    """Convierte una figura Plotly a imagen PNG en base64."""
    img_bytes = pio.to_image(fig, format="png", width=700, height=320, scale=1.5)
    return base64.b64encode(img_bytes).decode("utf-8")


def _bar_chart_top_insights(insights: list[Insight]) -> str:
    """Gráfico de barras: cantidad de insights por categoría y severidad."""
    counts = defaultdict(lambda: defaultdict(int))
    for ins in insights:
        counts[ins.category][ins.severity] += 1

    categories = list(CATEGORY_LABELS.keys())
    labels     = [CATEGORY_LABELS[c] for c in categories]

    fig = go.Figure()
    for severity, color in SEVERITY_COLORS.items():
        y_vals = [counts[cat][severity] for cat in categories]
        fig.add_trace(go.Bar(
            name      = SEVERITY_LABELS[severity],
            x         = labels,
            y         = y_vals,
            marker_color = color,
        ))

    fig.update_layout(
        barmode     = "stack",
        title       = "Insights por categoría y severidad",
        plot_bgcolor= "#ffffff",
        paper_bgcolor="#ffffff",
        font        = dict(family="Arial, sans-serif", size=12),
        margin      = dict(l=40, r=20, t=50, b=60),
        legend      = dict(orientation="h", y=-0.25),
        height      = 320,
    )
    fig.update_xaxes(tickangle=-20)
    return _fig_to_base64(fig)


def _severity_pie(insights: list[Insight]) -> str:
    """Pie chart de distribución por severidad."""
    counts = defaultdict(int)
    for ins in insights:
        counts[ins.severity] += 1

    labels = [SEVERITY_LABELS[s] for s in ["high", "medium", "low"]]
    values = [counts["high"], counts["medium"], counts["low"]]
    colors = [SEVERITY_COLORS["high"], SEVERITY_COLORS["medium"], SEVERITY_COLORS["low"]]

    fig = go.Figure(go.Pie(
        labels       = labels,
        values       = values,
        marker_colors= colors,
        hole         = 0.4,
        textinfo     = "label+percent",
    ))
    fig.update_layout(
        title         = "Distribución por severidad",
        paper_bgcolor = "#ffffff",
        font          = dict(family="Arial, sans-serif", size=12),
        margin        = dict(l=20, r=20, t=50, b=20),
        height        = 320,
        showlegend    = False,
    )
    return _fig_to_base64(fig)


# ---------------------------------------------------------------------------
# Componentes HTML
# ---------------------------------------------------------------------------

def _css() -> str:
    return """
    <style>
      * { box-sizing: border-box; margin: 0; padding: 0; }
      body {
        font-family: 'Segoe UI', Arial, sans-serif;
        background: #f5f5f0;
        color: #1a1a1a;
        font-size: 14px;
        line-height: 1.6;
      }
      .container { max-width: 960px; margin: 0 auto; padding: 32px 24px; }

      /* Header */
      .header {
        background: #1a1a1a;
        color: #fff;
        padding: 32px 40px;
        border-radius: 12px;
        margin-bottom: 32px;
      }
      .header h1 { font-size: 26px; font-weight: 500; margin-bottom: 6px; }
      .header .subtitle { color: #aaa; font-size: 13px; }
      .header .meta {
        display: flex; gap: 24px; margin-top: 16px;
        font-size: 12px; color: #888;
      }
      .header .meta span b { color: #fff; }

      /* Executive summary */
      .exec-summary {
        background: #fff;
        border-radius: 12px;
        border: 0.5px solid #e0e0d8;
        padding: 24px 28px;
        margin-bottom: 24px;
      }
      .exec-summary h2 {
        font-size: 16px; font-weight: 500;
        margin-bottom: 16px; color: #1a1a1a;
      }
      .top-findings { list-style: none; }
      .top-findings li {
        padding: 10px 0;
        border-bottom: 0.5px solid #f0f0e8;
        display: flex; align-items: flex-start; gap: 10px;
        font-size: 13px;
      }
      .top-findings li:last-child { border-bottom: none; }
      .finding-num {
        min-width: 24px; height: 24px;
        background: #1a1a1a; color: #fff;
        border-radius: 50%;
        display: flex; align-items: center; justify-content: center;
        font-size: 11px; font-weight: 500; flex-shrink: 0;
      }

      /* Charts row */
      .charts-row {
        display: grid; grid-template-columns: 1fr 1fr;
        gap: 16px; margin-bottom: 24px;
      }
      .chart-card {
        background: #fff;
        border-radius: 12px;
        border: 0.5px solid #e0e0d8;
        padding: 16px;
        text-align: center;
      }
      .chart-card img { width: 100%; border-radius: 6px; }

      /* Stats row */
      .stats-row {
        display: grid; grid-template-columns: repeat(5, 1fr);
        gap: 12px; margin-bottom: 24px;
      }
      .stat-card {
        background: #fff;
        border-radius: 10px;
        border: 0.5px solid #e0e0d8;
        padding: 14px 12px;
        text-align: center;
      }
      .stat-icon { font-size: 20px; margin-bottom: 4px; }
      .stat-number { font-size: 24px; font-weight: 500; margin-bottom: 2px; }
      .stat-label { font-size: 11px; color: #888; }

      /* Section */
      .section {
        background: #fff;
        border-radius: 12px;
        border: 0.5px solid #e0e0d8;
        margin-bottom: 20px;
        overflow: hidden;
      }
      .section-header {
        padding: 16px 24px;
        border-bottom: 0.5px solid #f0f0e8;
        display: flex; align-items: center; gap: 10px;
      }
      .section-header h2 { font-size: 15px; font-weight: 500; }
      .section-count {
        margin-left: auto;
        background: #f0f0e8;
        border-radius: 20px;
        padding: 2px 10px;
        font-size: 12px;
        color: #666;
      }

      /* Insight card */
      .insight {
        padding: 16px 24px;
        border-bottom: 0.5px solid #f8f8f4;
      }
      .insight:last-child { border-bottom: none; }
      .insight-header {
        display: flex; align-items: flex-start;
        gap: 10px; margin-bottom: 6px;
      }
      .severity-badge {
        font-size: 10px; font-weight: 500;
        padding: 2px 8px; border-radius: 20px;
        flex-shrink: 0; margin-top: 2px;
      }
      .insight-title { font-size: 13px; font-weight: 500; }
      .insight-desc { font-size: 12px; color: #555; margin-bottom: 8px; }
      .insight-data {
        display: flex; flex-wrap: wrap; gap: 8px;
      }
      .data-chip {
        background: #f5f5f0;
        border-radius: 6px;
        padding: 3px 8px;
        font-size: 11px;
        color: #444;
      }
      .data-chip b { color: #1a1a1a; }

      /* Footer */
      .footer {
        text-align: center;
        color: #aaa;
        font-size: 11px;
        margin-top: 32px;
        padding-top: 16px;
        border-top: 0.5px solid #e0e0d8;
      }
    </style>
    """


def _insight_card(ins: Insight) -> str:
    severity_color = SEVERITY_COLORS.get(ins.severity, "#888")
    severity_bg    = SEVERITY_BG.get(ins.severity, "#f5f5f0")
    severity_label = SEVERITY_LABELS.get(ins.severity, ins.severity)

    chips = []
    for key, val in ins.data.items():
        if key == "weak_metrics":
            for wm in (val or []):
                chips.append(
                    f'<span class="data-chip">'
                    f'<b>{wm["metric"]}</b>: {wm["value"]} '
                    f'(p{wm["percentile"]})'
                    f'</span>'
                )
        elif isinstance(val, (int, float)) and not isinstance(val, bool):
            chips.append(
                f'<span class="data-chip"><b>{key}</b>: {val}</span>'
            )
        elif isinstance(val, str) and key not in ("description",):
            chips.append(
                f'<span class="data-chip"><b>{key}</b>: {val}</span>'
            )

    chips_html = "\n".join(chips) if chips else ""

    return f"""
    <div class="insight">
      <div class="insight-header">
        <span class="severity-badge"
              style="background:{severity_bg};color:{severity_color}">
          {severity_label}
        </span>
        <span class="insight-title">{ins.title}</span>
      </div>
      <p class="insight-desc">{ins.description}</p>
      <div class="insight-data">{chips_html}</div>
    </div>
    """


def _section(category: str, insights: list[Insight]) -> str:
    if not insights:
        return ""

    icon  = CATEGORY_ICONS.get(category, "•")
    label = CATEGORY_LABELS.get(category, category)
    cards = "\n".join(_insight_card(ins) for ins in insights)

    return f"""
    <div class="section">
      <div class="section-header">
        <span style="font-size:18px">{icon}</span>
        <h2>{label}</h2>
        <span class="section-count">{len(insights)} hallazgos</span>
      </div>
      {cards}
    </div>
    """


# ---------------------------------------------------------------------------
# Generador principal
# ---------------------------------------------------------------------------

def generate_html_report(
    insights: list[Insight],
    data: dict,
) -> str:
    """Genera el HTML completo del reporte ejecutivo."""

    now         = datetime.now().strftime("%d/%m/%Y %H:%M")
    n_total     = len(insights)
    n_high      = sum(1 for i in insights if i.severity == "high")
    n_medium    = sum(1 for i in insights if i.severity == "medium")
    n_countries = len(data["countries"])
    n_zones     = len(data["zones"])

    by_category = defaultdict(list)
    for ins in insights:
        by_category[ins.category].append(ins)

    # Top 5 hallazgos para resumen ejecutivo
    top5 = [i for i in insights if i.severity == "high"][:5]
    if len(top5) < 5:
        top5 += [i for i in insights if i.severity == "medium"][:5 - len(top5)]

    top5_html = "\n".join(
        f"""<li>
          <span class="finding-num">{idx + 1}</span>
          <span>{ins.title} — {ins.description[:120]}...</span>
        </li>"""
        for idx, ins in enumerate(top5)
    )

    # Gráficos
    bar_b64 = _bar_chart_top_insights(insights)
    pie_b64 = _severity_pie(insights)

    # Stats cards
    stats_html = f"""
    <div class="stats-row">
      <div class="stat-card">
        <div class="stat-icon">📋</div>
        <div class="stat-number">{n_total}</div>
        <div class="stat-label">Total insights</div>
      </div>
      <div class="stat-card">
        <div class="stat-icon" style="color:{SEVERITY_COLORS['high']}">🔴</div>
        <div class="stat-number" style="color:{SEVERITY_COLORS['high']}">{n_high}</div>
        <div class="stat-label">Severidad alta</div>
      </div>
      <div class="stat-card">
        <div class="stat-icon" style="color:{SEVERITY_COLORS['medium']}">🟡</div>
        <div class="stat-number" style="color:{SEVERITY_COLORS['medium']}">{n_medium}</div>
        <div class="stat-label">Severidad media</div>
      </div>
      <div class="stat-card">
        <div class="stat-icon">🌎</div>
        <div class="stat-number">{n_countries}</div>
        <div class="stat-label">Países</div>
      </div>
      <div class="stat-card">
        <div class="stat-icon">📍</div>
        <div class="stat-number">{n_zones}</div>
        <div class="stat-label">Zonas analizadas</div>
      </div>
    </div>
    """

    # Secciones por categoría
    sections_html = "\n".join(
        _section(cat, by_category[cat])
        for cat in ["anomaly", "trend", "benchmark", "correlation", "opportunity"]
    )

    html = f"""<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Rappi — Reporte de Insights Operacionales</title>
  {_css()}
</head>
<body>
  <div class="container">

    <div class="header">
      <h1>🛵 Rappi — Reporte de Insights Operacionales</h1>
      <p class="subtitle">Análisis automático de métricas por zona geográfica</p>
      <div class="meta">
        <span>Generado: <b>{now}</b></span>
        <span>Países: <b>{n_countries}</b></span>
        <span>Zonas: <b>{n_zones}</b></span>
        <span>Semanas analizadas: <b>9</b></span>
      </div>
    </div>

    <div class="exec-summary">
      <h2>Resumen Ejecutivo — Top Hallazgos</h2>
      <ul class="top-findings">
        {top5_html}
      </ul>
    </div>

    {stats_html}

    <div class="charts-row">
      <div class="chart-card">
        <img src="data:image/png;base64,{bar_b64}" alt="Insights por categoría"/>
      </div>
      <div class="chart-card">
        <img src="data:image/png;base64,{pie_b64}" alt="Distribución por severidad"/>
      </div>
    </div>

    {sections_html}

    <div class="footer">
      Generado automáticamente por Rappi Analytics System ·
      {now} · {n_total} insights detectados
    </div>

  </div>
</body>
</html>"""

    return html


def save_report(html: str, path: Path = OUTPUT_PATH) -> Path:
    path.write_text(html, encoding="utf-8")
    return path
