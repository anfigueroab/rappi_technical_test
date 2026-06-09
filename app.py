import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

import re
import json
import traceback
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import streamlit as st
from anthropic import Anthropic

from src.data_loader import get_data
from src.prompts import (
    SYSTEM_PROMPT_CODE,
    SYSTEM_PROMPT_REFORMULATION,
    SYSTEM_PROMPT_SUGGESTIONS,
    SIDEBAR_SUGGESTIONS,
)

ANTHROPIC_MODEL = "claude-sonnet-4-5"

# ---------------------------------------------------------------------------
# Configuración de página
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="Rappi Analytics Bot",
    page_icon="🛵",
    layout="wide",
)

# ---------------------------------------------------------------------------
# CSS personalizado
# ---------------------------------------------------------------------------

st.markdown("""
<style>
  .main-header {
    background: #1a1a1a;
    color: white;
    padding: 20px 28px;
    border-radius: 12px;
    margin-bottom: 24px;
  }
  .main-header h1 { font-size: 24px; font-weight: 500; margin: 0 0 4px 0; }
  .main-header p  { font-size: 13px; color: #aaa; margin: 0; }

  .error-box {
    background: #FCEBEB;
    border: 0.5px solid #E24B4A;
    border-radius: 8px;
    padding: 12px 16px;
    font-size: 13px;
    color: #A32D2D;
  }
  .empty-box {
    background: #FAEEDA;
    border: 0.5px solid #BA7517;
    border-radius: 8px;
    padding: 12px 16px;
    font-size: 13px;
    color: #633806;
  }
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Carga de datos (cacheada)
# ---------------------------------------------------------------------------

@st.cache_data(show_spinner="Cargando datos de Rappi...")
def load_data():
    return get_data()

# ---------------------------------------------------------------------------
# Cliente Anthropic (cacheado)
# ---------------------------------------------------------------------------

@st.cache_resource
def get_client():
    import os
    from dotenv import load_dotenv
    load_dotenv()
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        st.error("No se encontró ANTHROPIC_API_KEY en el archivo .env")
        st.stop()
    return Anthropic(api_key=api_key)

# ---------------------------------------------------------------------------
# Helpers de procesamiento
# ---------------------------------------------------------------------------

def extract_code_block(text: str) -> str | None:
    """Extrae el primer bloque ```python ... ``` del texto."""
    pattern = r"```python\s*(.*?)\s*```"
    match   = re.search(pattern, text, re.DOTALL)
    return match.group(1).strip() if match else None


def execute_code(
    code   : str,
    df     : pd.DataFrame,
    orders : pd.DataFrame,
) -> tuple[pd.DataFrame | None, go.Figure | None, str | None]:
    """
    Ejecuta el código generado por el LLM en un namespace seguro.
    Retorna (result, fig, error_message).
    """
    namespace = {
        "df"    : df.copy(),
        "orders": orders.copy(),
        "pd"    : pd,
        "np"    : np,
        "go"    : go,
    }

    try:
        exec(code, namespace)
    except Exception:
        return None, None, traceback.format_exc()

    result = namespace.get("result", None)
    fig    = namespace.get("fig",    None)

    if result is not None and not isinstance(result, (pd.DataFrame, pd.Series)):
        try:
            result = pd.DataFrame(result)
        except Exception:
            result = None

    if isinstance(result, pd.Series):
        result = result.reset_index()
        result.columns = ["índice", "valor"]

    return result, fig, None


def call_llm_for_code(
    client   : Anthropic,
    question : str,
    history  : list[dict],
) -> str:
    """Primera llamada al LLM: genera código pandas."""
    messages = history + [{"role": "user", "content": question}]
    response = client.messages.create(
        model      = ANTHROPIC_MODEL,
        max_tokens = 1500,
        system     = SYSTEM_PROMPT_CODE,
        messages   = messages,
    )
    return response.content[0].text


def call_llm_for_reformulation(
    client   : Anthropic,
    question : str,
    result_df: pd.DataFrame | None,
) -> str:
    """Segunda llamada al LLM: reformula el resultado en lenguaje natural."""
    if result_df is not None and not result_df.empty:
        result_preview = result_df.head(20).to_markdown(index=False)
    else:
        result_preview = "No se encontraron datos para esta consulta."

    user_content = (
        f"Pregunta del usuario: {question}\n\n"
        f"Resultado de los datos:\n{result_preview}"
    )

    response = client.messages.create(
        model      = ANTHROPIC_MODEL,
        max_tokens = 500,
        system     = SYSTEM_PROMPT_REFORMULATION,
        messages   = [{"role": "user", "content": user_content}],
    )
    return response.content[0].text


def call_llm_for_suggestions(
    client : Anthropic,
    history: list[dict],
) -> list[str]:
    """Genera sugerencias proactivas basadas en el historial."""
    if not history:
        return []

    last_turns = history[-4:]
    context    = "\n".join(
        f"{m['role'].upper()}: {m['content'][:200]}"
        for m in last_turns
    )

    try:
        response = client.messages.create(
            model      = ANTHROPIC_MODEL,
            max_tokens = 200,
            system     = SYSTEM_PROMPT_SUGGESTIONS,
            messages   = [{"role": "user", "content": context}],
        )
        raw         = response.content[0].text.strip()
        suggestions = json.loads(raw)
        return suggestions[:3] if isinstance(suggestions, list) else []
    except Exception:
        return []


def process_question(
    question : str,
    data     : dict,
    history  : list[dict],
    client   : Anthropic,
) -> dict:
    """
    Orquesta el flujo completo:
      1. LLM genera código
      2. Ejecutamos el código
      3. Si falla, reintentamos con el error como contexto
      4. LLM reformula el resultado
    """
    df     = data["metrics"]
    orders = data["orders"]

    # ── Primera llamada: generar código ──────────────────────────────────
    raw_response = call_llm_for_code(client, question, history)
    code         = extract_code_block(raw_response)

    if not code:
        return {
            "text"  : raw_response,
            "result": None,
            "fig"   : None,
            "code"  : None,
            "error" : None,
        }

    # ── Ejecutar código ──────────────────────────────────────────────────
    result, fig, error = execute_code(code, df, orders)

    # ── Reintento si hay error ───────────────────────────────────────────
    if error:
        retry_question = (
            f"{question}\n\n"
            f"El código anterior falló con este error:\n{error}\n"
            f"Por favor corrige el código."
        )
        raw_response = call_llm_for_code(client, retry_question, history)
        code         = extract_code_block(raw_response)

        if code:
            result, fig, error = execute_code(code, df, orders)

    # ── Segunda llamada: reformular resultado ────────────────────────────
    natural_response = call_llm_for_reformulation(client, question, result)

    return {
        "text"  : natural_response,
        "result": result,
        "fig"   : fig,
        "code"  : code,
        "error" : error,
    }

# ---------------------------------------------------------------------------
# Inicialización de estado
# ---------------------------------------------------------------------------

if "messages"         not in st.session_state:
    st.session_state.messages         = []
if "llm_history"      not in st.session_state:
    st.session_state.llm_history      = []
if "suggestions"      not in st.session_state:
    st.session_state.suggestions      = SIDEBAR_SUGGESTIONS[:3]
if "pending_question" not in st.session_state:
    st.session_state.pending_question = None

# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------

with st.sidebar:
    st.markdown("### 🛵 Rappi Analytics Bot")
    st.markdown("---")

    data = load_data()
    col1, col2 = st.columns(2)
    col1.metric("Países",   len(data["countries"]))
    col2.metric("Zonas",    len(data["zones"]))
    col1.metric("Métricas", len(data["metric_names"]))
    col2.metric("Semanas",  9)

    st.markdown("---")

    st.markdown("**Preguntas sugeridas**")
    for suggestion in st.session_state.suggestions:
        if st.button(
            suggestion,
            key                 = f"sug_{suggestion[:30]}",
            use_container_width = True,
        ):
            st.session_state.pending_question = suggestion

    st.markdown("---")

    if st.button("🗑️ Limpiar conversación", use_container_width=True):
        st.session_state.messages         = []
        st.session_state.llm_history      = []
        st.session_state.suggestions      = SIDEBAR_SUGGESTIONS[:3]
        st.rerun()

    st.markdown("---")
    st.markdown(
        "<p style='font-size:11px;color:#aaa'>"
        "Costo estimado: ~$0.15–0.30 USD por sesión de 10 preguntas"
        "</p>",
        unsafe_allow_html=True,
    )

# ---------------------------------------------------------------------------
# Layout principal
# ---------------------------------------------------------------------------

st.markdown("""
<div class="main-header">
  <h1>🛵 Rappi Analytics Bot</h1>
  <p>Pregunta en lenguaje natural sobre las métricas operacionales de Rappi</p>
</div>
""", unsafe_allow_html=True)

# ── Historial de mensajes ────────────────────────────────────────────────

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

        if msg.get("result") is not None and not msg["result"].empty:
            st.dataframe(msg["result"], use_container_width=True)

        if msg.get("fig") is not None:
            st.plotly_chart(msg["fig"], use_container_width=True)

        if msg.get("code"):
            msg_id = msg.get("id", id(msg))
            if st.toggle("Ver código generado", key=f"code_{msg_id}"):
                st.code(msg["code"], language="python")

# ── Input ────────────────────────────────────────────────────────────────

if st.session_state.pending_question:
    user_input = st.session_state.pending_question
    st.session_state.pending_question = None
else:
    user_input = st.chat_input("Escribe tu pregunta sobre los datos de Rappi...")

if user_input:
    client = get_client()

    with st.chat_message("user"):
        st.markdown(user_input)

    st.session_state.messages.append({
        "role"   : "user",
        "content": user_input,
    })

    with st.chat_message("assistant"):
        with st.spinner("Analizando datos..."):
            response = process_question(
                question = user_input,
                data     = data,
                history  = st.session_state.llm_history,
                client   = client,
            )

        st.markdown(response["text"])

        if response["result"] is not None and not response["result"].empty:
            st.dataframe(response["result"], use_container_width=True)
        elif response["result"] is not None and response["result"].empty:
            st.markdown(
                '<div class="empty-box">No se encontraron datos para esta consulta.</div>',
                unsafe_allow_html=True,
            )

        if response["fig"] is not None:
            st.plotly_chart(response["fig"], use_container_width=True)

        if response["error"]:
            with st.expander("⚠️ Error de ejecución"):
                st.code(response["error"])

        if response["code"]:
            msg_id = len(st.session_state.messages)
            if st.toggle("Ver código generado", key=f"code_new_{msg_id}"):
                st.code(response["code"], language="python")

    st.session_state.messages.append({
        "role"   : "assistant",
        "content": response["text"],
        "result" : response["result"],
        "fig"    : response["fig"],
        "code"   : response["code"],
        "id"     : len(st.session_state.messages),
    })

    st.session_state.llm_history.append({
        "role"   : "user",
        "content": user_input,
    })
    st.session_state.llm_history.append({
        "role"   : "assistant",
        "content": response["text"],
    })

    new_suggestions = call_llm_for_suggestions(
        client  = client,
        history = st.session_state.llm_history,
    )
    if new_suggestions:
        st.session_state.suggestions = new_suggestions

    st.rerun()
