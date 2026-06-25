"""Axe 1 — Routage : Intent -> mutation d'AppState (pur). Renvoie (state, message)."""
from __future__ import annotations
import pandas as pd

from core import config
from core.domain.models import Intent
from core.domain.state import AppState, Filters


def route(intent: Intent, state: AppState) -> tuple[AppState, str]:
    a = intent.action
    if a == "navigate" and intent.target_page:
        state.current_page = intent.target_page
        return state, f"Navigation vers : {intent.target_page}"
    if a == "narrate":
        state.current_page = "Vue Globale"; state.narrate_requested = True
        return state, "Génération de la synthèse en cours…"
    if a == "reset":
        state.filters = Filters.default()
        return state, "Filtres réinitialisés."
    if a == "help":
        return state, ("Dites : 'Accueil', 'Performance', 'Régions', 'Assistant', "
                       "'Reset', 'Résumé', un filtre comme 'Région Nord', ou posez une question.")
    if a == "clear_filter":
        field = (intent.parameters or {}).get("field")
        if field == "region": state.filters.region = None; return state, "Filtre région supprimé."
        if field == "categorie": state.filters.categorie = None; return state, "Filtre catégorie supprimé."
        if field == "dates":
            state.filters.date_start = pd.Timestamp(config.DATE_MIN)
            state.filters.date_end = pd.Timestamp(config.DATE_MAX)
            return state, "Filtre date réinitialisé."
        return state, "Filtre non reconnu."
    if a == "filter":
        return _apply_filter(intent, state)
    if intent.pipeline == "llm_unavailable":
        return state, "Ollama non disponible. Seules les commandes rapides sont actives."
    return state, "Commande non reconnue. Dites 'Aide'."


def _apply_filter(intent: Intent, state: AppState) -> tuple[AppState, str]:
    p = intent.parameters or {}
    msgs, has_region, has_date, has_cat = [], False, False, False
    for key, ts_attr in (("date_start", "date_start"), ("date_end", "date_end")):
        if p.get(key):
            try:
                setattr(state.filters, ts_attr, pd.Timestamp(p[key]))
                msgs.append(f"{key} {p[key]}"); has_date = True
            except Exception:
                pass
    if p.get("region") in config.REGIONS:
        state.filters.region = p["region"]; msgs.append(f"région {p['region']}"); has_region = True
    if p.get("categorie") in config.CATEGORIES:
        state.filters.categorie = p["categorie"]; msgs.append(f"catégorie {p['categorie']}"); has_cat = True
    if not msgs:
        return state, "Aucun filtre reconnu dans la commande."
    cur = state.current_page
    on_regions = cur == "Régions" and has_region and not has_date and not has_cat
    if not on_regions and cur != "Performance":
        state.current_page = "Performance"
    return state, "Filtre appliqué : " + ", ".join(msgs)
