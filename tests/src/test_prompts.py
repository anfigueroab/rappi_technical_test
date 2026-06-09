import json
import pytest
from src.prompts import (
    METRIC_DICTIONARY,
    SYSTEM_PROMPT_CODE,
    SYSTEM_PROMPT_REFORMULATION,
    SYSTEM_PROMPT_SUGGESTIONS,
    SIDEBAR_SUGGESTIONS,
)


class TestMetricDictionary:

    def test_existe_y_no_vacio(self):
        assert isinstance(METRIC_DICTIONARY, str)
        assert len(METRIC_DICTIONARY) > 0

    def test_contiene_metricas_clave(self):
        metricas = [
            "Gross Profit UE",
            "Lead Penetration",
            "Perfect Orders",
            "Retail SST > SS CVR",
            "Pro Adoption",
            "Turbo Adoption",
        ]
        for m in metricas:
            assert m in METRIC_DICTIONARY, f"Falta métrica: {m}"

    def test_contiene_descripcion_de_rango(self):
        assert "Rango" in METRIC_DICTIONARY or "0 a 1" in METRIC_DICTIONARY


class TestSystemPromptCode:

    def test_existe_y_no_vacio(self):
        assert isinstance(SYSTEM_PROMPT_CODE, str)
        assert len(SYSTEM_PROMPT_CODE) > 500

    def test_contiene_estructura_dataframes(self):
        assert "df" in SYSTEM_PROMPT_CODE
        assert "orders" in SYSTEM_PROMPT_CODE

    def test_contiene_columnas_semana(self):
        assert "L0W_ROLL" in SYSTEM_PROMPT_CODE
        assert "L8W_ROLL" in SYSTEM_PROMPT_CODE

    def test_contiene_paises(self):
        for pais in ["AR", "BR", "CO", "MX", "PE"]:
            assert pais in SYSTEM_PROMPT_CODE

    def test_contiene_instruccion_result(self):
        assert "result" in SYSTEM_PROMPT_CODE

    def test_contiene_instruccion_fig(self):
        assert "fig" in SYSTEM_PROMPT_CODE

    def test_contiene_ejemplos_de_codigo(self):
        assert "```python" in SYSTEM_PROMPT_CODE

    def test_contiene_terminos_de_negocio(self):
        assert "zonas problemáticas" in SYSTEM_PROMPT_CODE
        assert "Wealthy" in SYSTEM_PROMPT_CODE

    def test_contiene_diccionario_de_metricas(self):
        assert "Gross Profit UE" in SYSTEM_PROMPT_CODE
        assert "Lead Penetration" in SYSTEM_PROMPT_CODE


class TestSystemPromptReformulation:

    def test_existe_y_no_vacio(self):
        assert isinstance(SYSTEM_PROMPT_REFORMULATION, str)
        assert len(SYSTEM_PROMPT_REFORMULATION) > 100

    def test_menciona_espanol(self):
        assert "español" in SYSTEM_PROMPT_REFORMULATION.lower()

    def test_menciona_limite_de_parrafos(self):
        assert "párrafo" in SYSTEM_PROMPT_REFORMULATION.lower()

    def test_menciona_resultado_vacio(self):
        assert "vacío" in SYSTEM_PROMPT_REFORMULATION.lower()


class TestSystemPromptSuggestions:

    def test_existe_y_no_vacio(self):
        assert isinstance(SYSTEM_PROMPT_SUGGESTIONS, str)
        assert len(SYSTEM_PROMPT_SUGGESTIONS) > 100

    def test_menciona_formato_json(self):
        assert "JSON" in SYSTEM_PROMPT_SUGGESTIONS

    def test_menciona_cantidad_sugerencias(self):
        assert "3" in SYSTEM_PROMPT_SUGGESTIONS


class TestSidebarSuggestions:

    def test_es_lista(self):
        assert isinstance(SIDEBAR_SUGGESTIONS, list)

    def test_tiene_suficientes_sugerencias(self):
        assert len(SIDEBAR_SUGGESTIONS) >= 5

    def test_todas_son_strings(self):
        for s in SIDEBAR_SUGGESTIONS:
            assert isinstance(s, str)

    def test_todas_son_preguntas_o_comandos(self):
        for s in SIDEBAR_SUGGESTIONS:
            assert len(s) > 10, f"Sugerencia muy corta: {s}"

    def test_cubre_distintos_tipos_de_analisis(self):
        texto = " ".join(SIDEBAR_SUGGESTIONS).lower()
        assert "top" in texto or "mayor" in texto or "menor" in texto
        assert "evolución" in texto or "muestra" in texto or "tendencia" in texto
        assert "compara" in texto or "promedio" in texto
