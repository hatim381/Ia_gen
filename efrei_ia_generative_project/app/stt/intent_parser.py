import json
import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

import pandas as pd
import streamlit as st

REGIONS = ["Nord", "Sud", "Est", "Ouest", "Île-de-France"]
CATEGORIES = ["Électronique", "Vêtements", "Alimentation", "Maison", "Sport"]

OLLAMA_MODEL = "mistral"

FAST_TRACK_RULES: list[tuple[str, dict[str, Any]]] = [
    (r"\b(accueil|home|global|vue globale|retour)\b", {"action": "navigate", "target_page": "Vue Globale"}),
    (r"\b(performance|perf)\b", {"action": "navigate", "target_page": "Performance"}),
    (r"\b(r[eé]gions|regions|carte)\b", {"action": "navigate", "target_page": "Régions"}),
    (r"\b(reset|r[eé]initialise[rz]?|efface[rz]?|tout effacer|tout réinitialiser)\b", {"action": "reset"}),
    (r"\b(r[eé]sum[eé]|synth[eè]se)\b", {"action": "narrate", "target_page": "Vue Globale"}),
    (r"\b(aide|help|\?)\b", {"action": "help"}),
    # clear_filter : field stocké dans parameters pour rester compatible avec Intent.parameters
    (r"\b(enlève|supprime|retire|sans)\b.+\br[eé]gion\b", {"action": "clear_filter", "parameters": {"field": "region"}}),
    (r"\b(enlève|supprime|retire|sans)\b.+\bcat[eé]gorie\b", {"action": "clear_filter", "parameters": {"field": "categorie"}}),
    (r"\b(enlève|supprime|retire|sans)\b.+\b(date|p[eé]riode)\b", {"action": "clear_filter", "parameters": {"field": "dates"}}),
]


@dataclass
class Intent:
    action: str = "unknown"
    target_page: str | None = None
    parameters: dict = field(default_factory=dict)
    pipeline: str = "fast_track"


def _fast_track(text: str) -> Intent | None:
    normalized = text.lower().strip()
    for pattern, result in FAST_TRACK_RULES:
        if re.search(pattern, normalized):
            params = result.get("parameters", {})
            intent = Intent(
                pipeline="fast_track",
                parameters=params,
                **{k: v for k, v in result.items() if k != "parameters"},
            )
            return intent
    return None


# Vocabulaire de référence pour le fuzzy matching (commandes simples uniquement)
_FUZZY_VOCAB: list[tuple[str, dict]] = [
    ("accueil",       {"action": "navigate", "target_page": "Vue Globale"}),
    ("vue globale",   {"action": "navigate", "target_page": "Vue Globale"}),
    ("global",        {"action": "navigate", "target_page": "Vue Globale"}),
    ("performance",   {"action": "navigate", "target_page": "Performance"}),
    ("régions",       {"action": "navigate", "target_page": "Régions"}),
    ("regions",       {"action": "navigate", "target_page": "Régions"}),
    ("carte",         {"action": "navigate", "target_page": "Régions"}),
    ("reset",         {"action": "reset"}),
    ("réinitialiser", {"action": "reset"}),
    ("résumé",        {"action": "narrate", "target_page": "Vue Globale"}),
    ("synthèse",      {"action": "narrate", "target_page": "Vue Globale"}),
    ("aide",          {"action": "help"}),
]
_FUZZY_KEYS = [k for k, _ in _FUZZY_VOCAB]
_FUZZY_MAP  = {k: v for k, v in _FUZZY_VOCAB}
FUZZY_THRESHOLD = 80  # % — en dessous on laisse passer au LLM


def _fuzzy_track(text: str) -> Intent | None:
    try:
        from rapidfuzz import fuzz, process
    except ImportError:
        return None

    normalized = text.lower().strip()

    # 1. Texte complet contre le vocabulaire
    match = process.extractOne(normalized, _FUZZY_KEYS, scorer=fuzz.ratio)
    if match and match[1] >= FUZZY_THRESHOLD:
        data = _FUZZY_MAP[match[0]]
        return Intent(pipeline="fuzzy", **data)

    # 2. Mot par mot uniquement sur les commandes d'un seul mot
    # Les phrases multi-mots (ex: "Région Nord", "Ventes de janvier") sont des filtres
    # → les envoyer au LLM. Matcher "région" dans "Région Nord" déclencherait navigate.
    words = normalized.split()
    if len(words) == 1 and len(words[0]) >= 4:
        match = process.extractOne(words[0], _FUZZY_KEYS, scorer=fuzz.ratio)
        if match and match[1] >= FUZZY_THRESHOLD:
            data = _FUZZY_MAP[match[0]]
            return Intent(pipeline="fuzzy", **data)

    return None


def _ollama_parse(text: str) -> Intent:
    """Envoie le texte à Ollama pour extraction d'intention structurée."""
    try:
        import ollama
    except ImportError:
        return Intent(action="unknown", pipeline="llm_unavailable")

    current_year = datetime.now().year
    user_prompt = f"""Tu es un extracteur d'intentions pour un dashboard retail.
Extrais les informations depuis la commande vocale et retourne UNIQUEMENT un JSON.

Champs du JSON :
- action: "filter" si filtrage de données, "unknown" sinon
- date_start: date ISO YYYY-MM-DD ou null (premier jour de la période mentionnée)
- date_end: date ISO YYYY-MM-DD ou null (dernier jour de la période mentionnée)
- region: une parmi {REGIONS} ou null
- categorie: une parmi {CATEGORIES} ou null

Règles :
- Si un mois est mentionné sans année, utilise {current_year}.
- Si un filtre est détecté (date/région/catégorie), action = "filter".
- Si hors périmètre, action = "unknown" et tous les autres champs = null.

Commande : "{text}" """

    try:
        # timeout=30 : coupe si Ollama swappe ou est surchargé
        # num_predict=150 : le JSON attendu fait ~80-120 tokens, limite la génération
        response = ollama.Client(timeout=30).chat(
            model=OLLAMA_MODEL,
            messages=[{"role": "user", "content": user_prompt}],
            options={"temperature": 0, "num_predict": 150},
            format="json",
        )
        raw = response["message"]["content"].strip()
        data = json.loads(raw)

        params = {
            "date_start": data.get("date_start"),
            "date_end": data.get("date_end"),
            "region": data.get("region"),
            "categorie": data.get("categorie"),
        }

        return Intent(
            action=data.get("action", "unknown"),
            target_page=None,
            parameters=params,
            pipeline="llm",
        )
    except Exception as exc:
        st.warning(f"Erreur LLM : {exc}")
        return Intent(action="unknown", pipeline="llm_error")


def parse_intent(text: str) -> Intent:
    """Triple pipeline : Regex → Fuzzy → LLM."""
    if not text.strip():
        return Intent(action="unknown")

    fast = _fast_track(text)
    if fast is not None:
        return fast

    fuzzy = _fuzzy_track(text)
    if fuzzy is not None:
        return fuzzy

    return _ollama_parse(text)


def apply_intent(intent: Intent) -> str:
    """Applique l'intention sur le session_state et retourne un message utilisateur."""

    if intent.action == "navigate" and intent.target_page:
        st.session_state.current_page = intent.target_page
        return f"Navigation vers : {intent.target_page}"

    if intent.action == "narrate":
        st.session_state.current_page = "Vue Globale"
        st.session_state.stt_narrate = True
        return "Génération de la synthèse en cours…"

    if intent.action == "reset":
        st.session_state.filter_date_start = pd.Timestamp("2024-01-01")
        st.session_state.filter_date_end = pd.Timestamp("2025-12-31")
        st.session_state.filter_region = None
        st.session_state.filter_categorie = None
        return "Filtres réinitialisés."

    if intent.action == "help":
        return (
            "Aide : dites 'Accueil', 'Performance', 'Régions', 'Reset', 'Résumé', "
            "un filtre comme 'Région Nord', ou 'Enlève le filtre région'."
        )

    if intent.action == "clear_filter":
        field = (intent.parameters or {}).get("field")
        if field == "region":
            st.session_state.filter_region = None
            return "Filtre région supprimé."
        if field == "categorie":
            st.session_state.filter_categorie = None
            return "Filtre catégorie supprimé."
        if field == "dates":
            st.session_state.filter_date_start = pd.Timestamp("2024-01-01")
            st.session_state.filter_date_end = pd.Timestamp("2025-12-31")
            return "Filtre date réinitialisé."
        return "Filtre non reconnu."

    if intent.action == "filter":
        params = intent.parameters or {}
        messages = []
        has_region = has_date = has_cat = False

        if params.get("date_start"):
            try:
                st.session_state.filter_date_start = pd.Timestamp(params["date_start"])
                messages.append(f"début {params['date_start']}")
                has_date = True
            except Exception:
                pass

        if params.get("date_end"):
            try:
                st.session_state.filter_date_end = pd.Timestamp(params["date_end"])
                messages.append(f"fin {params['date_end']}")
                has_date = True
            except Exception:
                pass

        if params.get("region") and params["region"] in REGIONS:
            st.session_state.filter_region = params["region"]
            messages.append(f"région {params['region']}")
            has_region = True

        if params.get("categorie") and params["categorie"] in CATEGORIES:
            st.session_state.filter_categorie = params["categorie"]
            messages.append(f"catégorie {params['categorie']}")
            has_cat = True

        if messages:
            current = st.session_state.get("current_page", "Vue Globale")
            # rester sur Régions si c'est un filtre région seul et qu'on y est déjà
            on_regions = current == "Régions" and has_region and not has_date and not has_cat
            on_perf = current == "Performance"
            if not on_regions and not on_perf:
                st.session_state.current_page = "Performance"
            return "Filtre appliqué : " + ", ".join(messages)

        return "Aucun filtre reconnu dans la commande."

    if intent.pipeline == "llm_unavailable":
        return "Ollama non disponible. Seules les commandes rapides sont actives."

    return "Commande non reconnue. Dites 'Aide' pour voir les commandes disponibles."
