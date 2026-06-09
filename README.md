# Rappi AI Analytics System

Sistema de análisis inteligente para operaciones Rappi.
Construido como prueba técnica para la posición de AI Engineer.

## Componentes

- **Bot conversacional**: responde preguntas en lenguaje natural sobre
  métricas operacionales de zonas en 9 países.
- **Sistema de insights automáticos**: detecta anomalías, tendencias
  preocupantes, benchmarking y oportunidades sin intervención manual.

## Stack

| Capa | Tecnología |
|------|-----------|
| LLM | Claude (Anthropic) via `anthropic` SDK |
| UI | Streamlit |
| Datos | pandas + openpyxl |
| Visualizaciones | Plotly |
| Reporte | Jinja2 + HTML |

## Setup

### 1. Clonar e instalar

```bash
git clone <repo-url>
cd rappi-technical_test
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Variables de entorno

```bash
cp .env.example .env
# Editar .env y agregar tu ANTHROPIC_API_KEY
```

### 3. Datos

Copiar `datos_rappi.xlsx` a la carpeta `data/`.

### 4. Correr el bot

```bash
streamlit run app.py
```

### 5. Generar reporte de insights

```bash
python generate_report.py
```

## Costo estimado de API

Con `claude-sonnet-4-20250514`:
- Input: ~$3 / millón de tokens
- Output: ~$15 / millón de tokens
- Sesión típica de 10 preguntas: ~$0.15–0.30 USD

## Estructura del proyecto

```
rappi-ai-system/
├── app.py                   # Bot Streamlit
├── generate_report.py       # Script de reporte standalone
├── requirements.txt
├── .env.example
├── data/
│   └── datos_rappi.xlsx
└── src/
    ├── data_loader.py       # Carga y limpieza de datos
    ├── analytics.py         # Funciones analíticas pandas
    ├── insights_engine.py   # Detección automática de insights
    ├── report_generator.py  # Generación de reporte HTML
    └── prompts.py           # System prompts del LLM
```