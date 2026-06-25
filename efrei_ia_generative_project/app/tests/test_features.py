"""Tests unitaires des features — logique pure, sans Streamlit ni Ollama."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.domain.state import AppState
from core.domain.models import Intent, QuerySpec
from core.data import repository as repo
from features.voice_navigation.intent_parser import IntentParser
from features.voice_navigation import command_router
from features.analytics_qa import query_engine as qe

PASS = 0; FAIL = 0
def ok(name, cond):
    global PASS, FAIL
    if cond: PASS += 1; print(f"  PASS  {name}")
    else: FAIL += 1; print(f"  FAIL  {name}")

# --- Axe 1 : parsing fast-track (sans LLM) ---
p = IntentParser()
ok("fast-track Accueil -> navigate", p.parse("Accueil").action == "navigate")
ok("fast-track Performance -> page", p.parse("perf").target_page == "Performance")
ok("fast-track reset", p.parse("reset les filtres").action == "reset")
ok("fast-track assistant", p.parse("assistant").target_page == "Assistant Q&A")
ok("vide -> unknown", p.parse("").action == "unknown")

# --- Axe 1 : routage pur sur AppState ---
s = AppState.default()
s, msg = command_router.route(Intent(action="navigate", target_page="Régions"), s)
ok("router navigate change page", s.current_page == "Régions")
s, msg = command_router.route(Intent(action="filter", parameters={"region": "Nord"}), s)
ok("router filter region", s.filters.region == "Nord")
ok("router region-only sur Régions reste sur Régions", s.current_page == "Régions")
s2 = AppState.default()  # depuis Vue Globale
s2, _ = command_router.route(Intent(action="filter", parameters={"categorie": "Sport"}), s2)
ok("router filter depuis Vue Globale -> Performance", s2.current_page == "Performance")
s, msg = command_router.route(Intent(action="filter", parameters={"region": "Normandie"}), s)
ok("router rejette region invalide", s.filters.region == "Nord")  # inchange
s, msg = command_router.route(Intent(action="reset"), s)
ok("router reset", s.filters.region is None)

# --- Axe 3 : moteur de requete sur vraies donnees ---
df = repo.load_sales()
r = qe.execute(QuerySpec(metric="ca", agg="sum", group_by="region", year=2025, sort="desc", limit=1), df)
ok("qa top region 2025 = IdF", r.ok and r.rows and r.rows[0]["region"] == "Île-de-France")
r2 = qe.execute(QuerySpec(metric="ca", region="Normandie"), df)
ok("qa rejette region invalide", not r2.ok)
r3 = qe.execute(QuerySpec(metric="salaires", agg="sum"), df)
ok("qa rejette metrique non whitelistee", not r3.ok)

print(f"\n{PASS} passes, {FAIL} echecs")
sys.exit(1 if FAIL else 0)
