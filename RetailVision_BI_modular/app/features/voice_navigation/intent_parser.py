"""Axe 1 — Parsing d'intention : triple pipeline Regex -> Fuzzy -> LLM. Pur (pas de Streamlit)."""
from __future__ import annotations
import re
from datetime import datetime

from core import config
from core.domain.models import Intent
from core.llm.client import LLMClient
from core.llm import prompts

FAST_TRACK = [
    (r"\b(accueil|home|global|vue globale|retour)\b", {"action": "navigate", "target_page": "Vue Globale"}),
    (r"\b(performance|perf)\b", {"action": "navigate", "target_page": "Performance"}),
    (r"\b(r[eé]gions|regions|carte)\b", {"action": "navigate", "target_page": "Régions"}),
    (r"\b(reset|r[eé]initialise[rz]?|efface[rz]?|tout effacer)\b", {"action": "reset"}),
    (r"\b(r[eé]sum[eé]|synth[eè]se)\b", {"action": "narrate", "target_page": "Vue Globale"}),
    (r"\b(aide|help|\?)\b", {"action": "help"}),
    (r"\b(enl[eè]ve|supprime|retire|sans)\b.+\br[eé]gion\b", {"action": "clear_filter", "parameters": {"field": "region"}}),
    (r"\b(enl[eè]ve|supprime|retire|sans)\b.+\bcat[eé]gorie\b", {"action": "clear_filter", "parameters": {"field": "categorie"}}),
    (r"\b(enl[eè]ve|supprime|retire|sans)\b.+\b(date|p[eé]riode)\b", {"action": "clear_filter", "parameters": {"field": "dates"}}),
    # Filtres région — noms fixes, pas besoin du LLM
    (r"\bnord\b", {"action": "filter", "parameters": {"region": "Nord"}}),
    (r"\bsud\b", {"action": "filter", "parameters": {"region": "Sud"}}),
    (r"\bouest\b", {"action": "filter", "parameters": {"region": "Ouest"}}),
    (r"\b(île[- ]de[- ]france|ile[- ]de[- ]france|idf)\b", {"action": "filter", "parameters": {"region": "Île-de-France"}}),
    (r"(?<!c')(?<!n')(?<!qu')\best\b", {"action": "filter", "parameters": {"region": "Est"}}),
    # Filtres catégorie — noms fixes, pas besoin du LLM
    (r"\b(électronique|electronique)\b", {"action": "filter", "parameters": {"categorie": "Électronique"}}),
    (r"\b(vêtements|vetements|vêtement|vetement)\b", {"action": "filter", "parameters": {"categorie": "Vêtements"}}),
    (r"\b(alimentation|alim)\b", {"action": "filter", "parameters": {"categorie": "Alimentation"}}),
    (r"\bmaison\b", {"action": "filter", "parameters": {"categorie": "Maison"}}),
    (r"\bsport\b", {"action": "filter", "parameters": {"categorie": "Sport"}}),
]

_REGIONS_MAP = {r.lower(): r for r in config.REGIONS}
_CATEGORIES_MAP = {c.lower(): c for c in config.CATEGORIES}

_DATE_RE = re.compile(
    r"\b(2024|2025|janvier|f[eé]vrier|mars|avril|mai|juin|"
    r"juillet|ao[uû]t|septembre|octobre|novembre|d[eé]cembre|"
    r"entre|trimestre|semestre)\b"
)
_REGION_RE = re.compile(r"\b(nord|sud|ouest|île[- ]de[- ]france|ile[- ]de[- ]france|idf|(?<!c')(?<!n')(?<!qu')est)\b")
_CAT_RE = re.compile(r"\b(électronique|electronique|vêtements|vetements|alimentation|alim|maison|sport)\b")

_LLM_VALID_ACTIONS = {"filter", "unknown"}


def _is_complex_filter(text: str) -> bool:
    """Retourne True si le texte contient des dates OU plusieurs entités — le LLM doit tout extraire."""
    if _DATE_RE.search(text):
        return True
    return bool(_REGION_RE.search(text)) and bool(_CAT_RE.search(text))

_FUZZY = [
    ("accueil", {"action": "navigate", "target_page": "Vue Globale"}),
    ("vue globale", {"action": "navigate", "target_page": "Vue Globale"}),
    ("performance", {"action": "navigate", "target_page": "Performance"}),
    ("régions", {"action": "navigate", "target_page": "Régions"}),
    ("reset", {"action": "reset"}),
    ("réinitialiser", {"action": "reset"}),
    ("résumé", {"action": "narrate", "target_page": "Vue Globale"}),
    ("synthèse", {"action": "narrate", "target_page": "Vue Globale"}),
    ("aide", {"action": "help"}),
]
_FUZZY_KEYS = [k for k, _ in _FUZZY]
_FUZZY_MAP = {k: v for k, v in _FUZZY}
FUZZY_THRESHOLD = 80


class IntentParser:
    def __init__(self, llm: LLMClient | None = None):
        self.llm = llm or LLMClient()

    def parse(self, text: str) -> Intent:
        if not text or not text.strip():
            return Intent(action="unknown")
        return self._fast(text) or self._fuzzy(text) or self._llm(text)

    def _fast(self, text):
        n = text.lower().strip()
        complex_filter = _is_complex_filter(n)
        for pat, res in FAST_TRACK:
            if re.search(pat, n):
                if res.get("action") == "filter" and complex_filter:
                    continue  # laisser le LLM extraire l'ensemble (dates + entités)
                params = res.get("parameters", {})
                return Intent(pipeline="fast_track", parameters=params,
                              **{k: v for k, v in res.items() if k != "parameters"})
        return None

    def _fuzzy(self, text):
        try:
            from rapidfuzz import fuzz, process
        except ImportError:
            return None
        n = text.lower().strip()
        m = process.extractOne(n, _FUZZY_KEYS, scorer=fuzz.ratio)
        if m and m[1] >= FUZZY_THRESHOLD:
            return Intent(pipeline="fuzzy", **_FUZZY_MAP[m[0]])
        words = n.split()
        if len(words) == 1 and len(words[0]) >= 4:
            m = process.extractOne(words[0], _FUZZY_KEYS, scorer=fuzz.ratio)
            if m and m[1] >= FUZZY_THRESHOLD:
                return Intent(pipeline="fuzzy", **_FUZZY_MAP[m[0]])
        return None

    def _llm(self, text):
        res = self.llm.chat_json(prompts.intent_extraction(text, datetime.now().year), num_predict=150)
        if not res.ok:
            return Intent(action="unknown",
                          pipeline="llm_unavailable" if res.error == "ollama_unavailable" else "llm_error")
        d = res.data or {}
        # Validation stricte — protège contre les injections et hallucinations
        action = d.get("action", "unknown")
        if action not in _LLM_VALID_ACTIONS:
            action = "unknown"
        region = _REGIONS_MAP.get((d.get("region") or "").lower())
        categorie = _CATEGORIES_MAP.get((d.get("categorie") or "").lower())
        params = {"date_start": d.get("date_start"), "date_end": d.get("date_end"),
                  "region": region, "categorie": categorie}
        return Intent(action=action, parameters=params, pipeline="llm")
