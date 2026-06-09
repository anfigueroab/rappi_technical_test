# 🛵 Rappi AI Analytics System

Sistema de análisis inteligente para operaciones Rappi. Permite a equipos
no técnicos hacer preguntas en lenguaje natural sobre métricas operacionales
y recibir automáticamente insights accionables sobre zonas geográficas en
9 países de Latinoamérica.

---

## Índice

1. [Contexto y solución](#1-contexto-y-solución)
2. [Arquitectura](#2-arquitectura)
3. [Componentes](#3-componentes)
4. [Stack tecnológico](#4-stack-tecnológico)
5. [Instalación](#5-instalación)
6. [Configuración del LLM](#6-configuración-del-llm)
7. [Cómo usar el bot](#7-cómo-usar-el-bot)
8. [Generar reporte de insights](#8-generar-reporte-de-insights)
9. [Tests](#9-tests)
10. [Estructura del proyecto](#10-estructura-del-proyecto)
11. [Costos de API](#11-costos-de-api)
12. [Decisiones técnicas](#12-decisiones-técnicas)
13. [Limitaciones y próximos pasos](#13-limitaciones-y-próximos-pasos)

---

## 1. Contexto y solución

### El problema

Los equipos de SP&A y Operations de Rappi necesitan tomar decisiones
data-driven constantemente, pero enfrentan dos desafíos:

- Los datos requieren conocimiento técnico (SQL, Python) para extraer insights.
- El análisis semanal es manual y repetitivo.

### La solución

Un sistema de dos componentes:

**Bot Conversacional** — permite a cualquier persona del equipo hacer
preguntas como *"¿Qué zonas de México tienen Gross Profit UE negativo?"*
y recibir respuestas precisas con tablas y gráficos, sin escribir una
sola línea de código.

**Sistema de Insights Automáticos** — analiza todo el dataset cada semana
y genera un reporte ejecutivo HTML con anomalías, tendencias preocupantes,
benchmarking entre zonas similares, correlaciones y oportunidades de
crecimiento.

---

## 2. Arquitectura

```
datos_rappi.xlsx
       ↓
  data_loader.py        Carga, limpieza y deduplicación
       ↓
    ┌──────────────────────────────────────────┐
    │            Capa analítica                │
    │  analytics.py — funciones pandas puras   │
    │  insights_engine.py — detección batch    │
    └──────────────────────────────────────────┘
           ↓                        ↓
      app.py                generate_report.py
  Bot Streamlit              Reporte HTML
  + LLM (Claude)
```

### Flujo del bot

```
Usuario escribe pregunta
        ↓
  LLM genera código pandas    ← System prompt con esquema + métricas
        ↓
  exec() en namespace seguro  ← Solo pandas, numpy, plotly
        ↓
  Si falla → reintento con el error como contexto
        ↓
  LLM reformula resultado     ← Lenguaje natural orientado al negocio
        ↓
  Streamlit muestra texto + tabla + gráfico
```

---

## 3. Componentes

### 3.1 Bot Conversacional

Capacidades demostradas:

| Tipo de pregunta | Ejemplo |
|-----------------|---------|
| Filtrado | ¿Cuáles son las 5 zonas con mayor Lead Penetration? |
| Comparación | Compara Perfect Orders entre Wealthy y Non Wealthy en México |
| Tendencia temporal | Muestra la evolución de Gross Profit UE en Chapinero |
| Agregación | ¿Cuál es el promedio de Lead Penetration por país? |
| Multivariable | ¿Qué zonas tienen alto Lead Penetration pero bajo Gross Profit UE? |
| Inferencia | ¿Qué zonas crecen más en órdenes y qué podría explicarlo? |

Características adicionales:

- Memoria conversacional (el bot recuerda el contexto de la sesión)
- Sugerencias proactivas de análisis que se actualizan con cada respuesta
- Visualizaciones automáticas (líneas para tendencias, barras para comparaciones)
- Toggle para ver el código pandas generado en cada respuesta
- Reintento automático si el código generado falla

### 3.2 Sistema de Insights Automáticos

Detecta cinco categorías de hallazgos:

| Categoría | Lógica |
|-----------|--------|
| Anomalías | Cambio mayor al 10% entre L1W y L0W en métricas proporcionales, o cambio absoluto mayor a 1.5 en Gross Profit UE |
| Tendencias preocupantes | 3 o más semanas consecutivas de deterioro en métricas donde más alto es mejor |
| Benchmarking | Zonas con más de 1.5 desviaciones estándar por debajo del promedio de su grupo (mismo país y tipo) |
| Correlaciones | Pares de métricas con correlación mayor a 0.6 o menor a -0.6 a nivel de zona |
| Oportunidades | Zonas con órdenes creciendo pero métricas operacionales en el percentil 35 o menor |

### 3.3 Reporte HTML

Genera un archivo HTML autocontenido con:

- Resumen ejecutivo con los top 5 hallazgos críticos
- Gráficos de distribución por categoría y severidad embebidos como base64
- Detalle por categoría con badges de severidad
- Métricas de soporte por cada hallazgo

---

## 4. Stack tecnológico

| Capa | Tecnología | Justificación |
|------|-----------|---------------|
| LLM | Claude (Anthropic) | Mejor manejo de contexto largo para el system prompt con diccionario de métricas completo |
| Estrategia LLM | Text-to-Python | Más flexible que SQL para análisis ad-hoc; pandas ya conocido por el modelo |
| UI | Streamlit | Permite demo funcional en 2 días sin sacrificar calidad |
| Datos | pandas + openpyxl | Estándar para análisis tabular en Python |
| Visualizaciones | Plotly | Gráficos interactivos nativos en Streamlit |
| Reporte | HTML + CSS inline | Archivo autocontenido con gráficos embebidos, sin dependencias externas |
| Tests | pytest | Estándar de la industria para Python |

---

## 5. Instalación

### Requisitos

- Python 3.10 o superior
- pip

### Pasos

```bash
# 1. Clonar el repositorio
git clone <url-del-repo>
cd rappi-ai-system

# 2. Crear entorno virtual
python -m venv venv

# Mac/Linux:
source venv/bin/activate
# Windows:
venv\Scripts\activate

# 3. Instalar dependencias
python -m pip install -r requirements.txt

# 4. Configurar variables de entorno
cp .env.example .env
# Editar .env y agregar tu API key (ver sección 6)

# 5. Copiar los datos
# Pegar datos_rappi.xlsx en la carpeta data/
```

---

## 6. Configuración del LLM

El sistema soporta tres opciones de LLM. Por defecto usa **Claude de Anthropic**,
que es la opción recomendada por su calidad en generación de código pandas.

---

### Opción A — Claude (Anthropic) · Recomendado

1. Crear cuenta en [console.anthropic.com](https://console.anthropic.com)
2. Agregar créditos en **Settings → Billing** (mínimo $5 USD)
3. Crear key en **Settings → API Keys → Create Key**
4. Agregar al `.env`:

```bash
ANTHROPIC_API_KEY=sk-ant-tu-clave-aqui
```

El modelo usado es `claude-sonnet-4-5`. Sin cambios adicionales en el código.

---

### Opción B — Gemini (Google) · Gratuito con límites

Útil para pruebas rápidas sin tarjeta de crédito.

1. Obtener key en [aistudio.google.com/apikey](https://aistudio.google.com/apikey)
2. Instalar la librería:

```bash
python -m pip install google-generativeai
```

3. Agregar al `.env`:

```bash
GOOGLE_API_KEY=AIzaSy-tu-clave-aqui
```

4. En `app.py`, reemplazar el cliente por:

```python
import google.generativeai as genai

GEMINI_MODEL = "gemini-2.0-flash"

def get_client():
    load_dotenv()
    genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
    return genai.GenerativeModel(
        model_name         = GEMINI_MODEL,
        system_instruction = SYSTEM_PROMPT_CODE,
    )
```

> **Nota:** El tier gratuito de Gemini tiene un límite de 15 requests por
> minuto y 1 millón de tokens por día. Para sesiones largas puede alcanzar
> el límite y devolver error 429.

---

### Opción C — Ollama (local) · Sin costo, sin internet

Ideal para entornos sin acceso a APIs externas o con datos sensibles.

1. Instalar Ollama desde [ollama.com](https://ollama.com)
2. Descargar un modelo:

```bash
# Modelo general (recomendado para empezar):
ollama pull llama3.1

# Modelo especializado en código (mejor calidad en pandas):
ollama pull codellama
```

3. Instalar la librería:

```bash
python -m pip install ollama
```

4. En `app.py`, reemplazar las funciones de llamada al LLM:

```python
import ollama

OLLAMA_MODEL = "llama3.1"

def get_client():
    return None  # Ollama no necesita cliente con API key

def call_llm_for_code(client, question, history):
    messages = [{"role": "system", "content": SYSTEM_PROMPT_CODE}]
    for msg in history:
        messages.append({"role": msg["role"], "content": msg["content"]})
    messages.append({"role": "user", "content": question})
    response = ollama.chat(model=OLLAMA_MODEL, messages=messages)
    return response["message"]["content"]

def call_llm_for_reformulation(client, question, result_df):
    if result_df is not None and not result_df.empty:
        result_preview = result_df.head(20).to_markdown(index=False)
    else:
        result_preview = "No se encontraron datos para esta consulta."
    prompt = (
        f"{SYSTEM_PROMPT_REFORMULATION}\n\n"
        f"Pregunta: {question}\n\n"
        f"Resultado:\n{result_preview}"
    )
    response = ollama.chat(
        model    = OLLAMA_MODEL,
        messages = [{"role": "user", "content": prompt}],
    )
    return response["message"]["content"]
```

> **Nota:** Los modelos locales son más lentos (10–30 segundos por respuesta)
> y pueden generar código pandas con más errores que los modelos cloud.
> El sistema de reintento automático mitiga esto parcialmente.
> Requiere mínimo 8 GB de RAM para modelos 7B y 16 GB para modelos 13B.

---

## 7. Cómo usar el bot

```bash
python -m streamlit run app.py
```

Se abre automáticamente en `http://localhost:8501`.

### Ejemplos de preguntas

```
# Filtrado
¿Cuáles son las 5 zonas con mayor Gross Profit UE esta semana?
¿Qué zonas de Brasil tienen Gross Profit UE negativo?

# Comparaciones
Compara Perfect Orders entre Wealthy y Non Wealthy en México
¿Cuál es el promedio de Lead Penetration por país?

# Tendencias temporales
Muestra la evolución de Gross Profit UE en Chapinero las últimas 8 semanas
¿Cuáles son las zonas de Colombia con caída sostenida en órdenes?

# Análisis multivariable
¿Qué zonas tienen alto Lead Penetration pero bajo Gross Profit UE?
Muestra las zonas High Priority de México con peor desempeño

# Inferencia
¿Qué zonas crecen más en órdenes en las últimas 5 semanas y qué podría explicarlo?
```

### Funcionalidades del chat

- **Sugerencias proactivas** — el sidebar muestra 3 preguntas sugeridas
  que se actualizan automáticamente después de cada respuesta.
- **Ver código generado** — cada respuesta tiene un toggle para ver el
  código pandas que el LLM generó.
- **Memoria conversacional** — puedes hacer preguntas de seguimiento
  como "¿y en Argentina?" sin repetir el contexto.
- **Limpiar conversación** — botón en el sidebar para resetear el chat.

---

## 8. Generar reporte de insights

```bash
python generate_report.py
```

Genera `reporte_rappi.html` en la raíz del proyecto. Ábrelo en cualquier
navegador — es un archivo autocontenido que no necesita conexión ni servidor.

Output esperado:

```
Cargando datos...
Detectando insights...
Generando reporte (N insights)...

Reporte listo: reporte_rappi.html
  Alta severidad : X
  Media severidad: Y
```

---

## 9. Tests

```bash
# Correr todos los tests
python -m pytest tests/ -v

# Por módulo
python -m pytest tests/test_data_loader.py -v
python -m pytest tests/test_analytics.py -v
python -m pytest tests/test_insights_engine.py -v
python -m pytest tests/test_report_generator.py -v
python -m pytest tests/test_prompts.py -v
```

Cobertura de tests:

| Módulo | Tests | Qué valida |
|--------|-------|-----------|
| data_loader | 18 | Carga, limpieza, deduplicación, merge |
| analytics | 24 | Las 7 funciones analíticas con edge cases |
| insights_engine | 28 | Los 5 detectores y run_all |
| report_generator | 12 | Generación HTML, gráficos, guardado |
| prompts | 16 | Contenido y estructura de los prompts |

---

## 10. Estructura del proyecto

```
rappi-ai-system/
│
├── app.py                    # Bot conversacional (Streamlit)
├── generate_report.py        # Script standalone de reporte
├── requirements.txt          # Dependencias Python
├── .env.example              # Template de variables de entorno
├── .gitignore
├── README.md
│
├── data/
│   └── datos_rappi.xlsx      # Dataset (no incluido en el repo)
│
├── src/
│   ├── __init__.py
│   ├── data_loader.py        # Carga y limpieza de datos
│   ├── analytics.py          # Funciones analíticas pandas
│   ├── insights_engine.py    # Detección automática de insights
│   ├── report_generator.py   # Generación de reporte HTML
│   └── prompts.py            # System prompts del LLM
│
└── tests/
    ├── __init__.py
    ├── test_data_loader.py
    ├── test_analytics.py
    ├── test_insights_engine.py
    ├── test_report_generator.py
    └── test_prompts.py
```

---

## 11. Costos de API

### Claude (Anthropic) — claude-sonnet-4-5

| Concepto | Costo |
|----------|-------|
| Input tokens | $3.00 USD / millón de tokens |
| Output tokens | $15.00 USD / millón de tokens |

Estimación por caso de uso:

| Caso | Tokens aproximados | Costo aproximado |
|------|--------------------|-----------------|
| 1 pregunta simple | 2K input + 300 output | $0.01 USD |
| 1 pregunta con gráfico | 2K input + 600 output | $0.015 USD |
| Sesión de 10 preguntas | 20K input + 4K output | $0.12 USD |
| Demo completa (30 preguntas) | 60K input + 12K output | $0.36 USD |
| Uso mensual intensivo (500 preguntas) | 1M input + 200K output | $6.00 USD |

> El system prompt ocupa aproximadamente 1,500 tokens y se envía en cada
> llamada al LLM. El costo real puede variar según la complejidad de las
> preguntas y el tamaño de los resultados.

Para reducir costos se puede:

- Usar `claude-haiku-4-5` en lugar de `claude-sonnet-4-5` (10x más barato,
  algo menos preciso en código complejo).
- Truncar el historial conversacional a las últimas 6 interacciones.
- Limitar el preview del resultado a 10 filas en lugar de 20.

### Gemini (Google) — gemini-2.0-flash

| Tier | Límite | Costo |
|------|--------|-------|
| Gratuito | 15 requests/min, 1M tokens/día | $0 |
| Pay-as-you-go | Sin límite de rate | ~$0.075 USD / 1M tokens |

### Ollama (local)

Costo de API: $0. Costo de infraestructura: electricidad del equipo local.

---

## 12. Decisiones técnicas

### Por qué Text-to-Python en lugar de RAG o SQL

Los datos están en memoria como DataFrames. Pandas es más flexible que SQL
para análisis ad-hoc como percentiles, slopes y pivots. RAG no aplica porque
no es búsqueda semántica sino análisis numérico estructurado. El LLM ya conoce
pandas muy bien por su presencia masiva en datos de entrenamiento.

### Por qué Streamlit en lugar de React o FastAPI

El objetivo es una demo funcional que un Operational Manager pueda usar
realmente. Streamlit permite eso en 2 días sin sacrificar calidad. La capa
de procesamiento en `src/` es completamente independiente del frontend y
puede exponerse como API REST en el futuro sin modificaciones.

### Por qué HTML para el reporte en lugar de PDF

El HTML embebe gráficos interactivos, es un archivo único autocontenido y
no requiere librerías de renderizado PDF que suelen tener problemas de
compatibilidad entre sistemas operativos.

### Por qué pandas puro para los insights automáticos

Garantiza reproducibilidad y auditabilidad total. Cualquier analista puede
revisar exactamente qué cálculo detectó cada anomalía. Usar el LLM para
detectar insights hubiera sido más lento, más caro y menos confiable para
cálculos estadísticos precisos.

---

## 13. Limitaciones y próximos pasos

### Limitaciones actuales

- **Datos en memoria**: el sistema carga todo el Excel en RAM al iniciar.
  Con datasets de millones de filas necesitaría una base de datos.
- **Sin autenticación**: cualquier persona con acceso al puerto puede
  usar el bot y ver todos los datos.
- **Historial no persistente**: al cerrar el navegador se pierde el
  historial de la sesión.
- **Un usuario a la vez**: Streamlit en modo local no escala a múltiples
  usuarios simultáneos sin deployment en la nube.

### Próximos pasos con más tiempo

1. **Deployment en la nube**: Streamlit Cloud o Railway para acceso remoto
   sin instalación local.
2. **Base de datos**: reemplazar el Excel por PostgreSQL o BigQuery para
   datos en tiempo real actualizados automáticamente.
3. **Exportación desde el chat**: botón para descargar resultados como CSV
   directamente desde cada respuesta del bot.
4. **Alertas automáticas**: envío del reporte semanal por email usando
   SendGrid o similar, sin intervención manual.
5. **Autenticación**: integración con SSO corporativo para control de
   acceso por rol.
6. **Caché de consultas frecuentes**: guardar resultados de preguntas
   comunes para reducir costos de API y tiempo de respuesta.
7. **Feedback loop**: botón de pulgar arriba y abajo en cada respuesta
   para mejorar los prompts con el tiempo.