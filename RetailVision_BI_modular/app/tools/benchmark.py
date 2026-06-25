"""
Benchmark LLM RetailVision BI — À LANCER SUR TON PC (Ollama requis).

Mesure, sur TES modeles et la capacite reelle de ton poste :
  - exactitude d'extraction d'intention (via le pipeline reel features/voice_navigation),
  - latence a froid (cold start) vs a chaud (warm),
  - usage memoire approximatif (taille du modele rapportee par Ollama).

Usage :
    python app/tools/benchmark.py                      # set recommande, installe ce qui manque
    python app/tools/benchmark.py --models gemma3:4b qwen2.5:7b
    python app/tools/benchmark.py --installed           # uniquement les modeles deja presents
    python app/tools/benchmark.py --no-pull             # ne rien telecharger

Resultats accumules dans app/eval/reports/benchmark_pc.json + tableau recap.
"""
from __future__ import annotations
import argparse, json, subprocess, sys, time
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))   # rend core/features importables

from core.llm.client import LLMClient
from features.voice_navigation.intent_parser import IntentParser

RESULTS = HERE.parent / "eval" / "reports" / "benchmark_pc.json"
RECOMMENDED = ["gemma3:4b", "qwen2.5:7b", "llama3.1", "phi3.5", "mistral"]

# Scenarios LLM (les fast-track sont exclus : ils ne touchent pas le modele)
SCENARIOS = [
    {"id": "T-date",  "cmd": "Affiche les ventes de janvier 2025",
     "expect": {"action": "filter", "date_start": "2025-01-01", "date_end": "2025-01-31"}},
    {"id": "T-region","cmd": "Région Nord",
     "expect": {"action": "filter", "region": "Nord"}},
    {"id": "T-multi", "cmd": "Catégorie Sport entre mars et juin 2024",
     "expect": {"action": "filter", "categorie": "Sport", "date_start": "2024-03-01", "date_end": "2024-06-30"}},
    {"id": "T-oos",   "cmd": "Météo demain",
     "expect": {"action": "unknown"}},
]


def ollama_list() -> list[str]:
    try:
        out = subprocess.run(["ollama", "list"], capture_output=True, text=True, timeout=30).stdout
        return [ln.split()[0] for ln in out.splitlines()[1:] if ln.strip()]
    except Exception as exc:
        print(f"[!] 'ollama list' indisponible : {exc}"); return []


def ollama_size(model: str) -> str:
    try:
        out = subprocess.run(["ollama", "list"], capture_output=True, text=True, timeout=30).stdout
        for ln in out.splitlines():
            if ln.split() and ln.split()[0] == model:
                return " ".join(ln.split()[2:4])
    except Exception:
        pass
    return "?"


def ensure_model(model: str, allow_pull: bool, installed: list[str]) -> bool:
    if model in installed:
        return True
    if not allow_pull:
        print(f"[skip] {model} non installe (--no-pull)"); return False
    print(f"[pull] telechargement de {model} … (peut etre long)")
    code = subprocess.call(["ollama", "pull", model])
    return code == 0


def check(expect: dict, got: dict) -> bool:
    for k, v in expect.items():
        if str(got.get(k)).lower() != str(v).lower():
            return False
    return True


def bench_model(model: str) -> dict:
    print(f"\n{'='*56}\n  Modele : {model}  ({ollama_size(model)})\n{'='*56}")
    parser = IntentParser(LLMClient(model=model))
    rows, cold = [], None
    passed = 0
    for i, sc in enumerate(SCENARIOS):
        t0 = time.perf_counter()
        intent = parser.parse(sc["cmd"])
        lat = (time.perf_counter() - t0) * 1000
        got = {"action": intent.action, **(intent.parameters or {})}
        ok = check(sc["expect"], got)
        passed += ok
        if i == 0:
            cold = lat
        rows.append({"id": sc["id"], "ok": ok, "latency_ms": round(lat, 1), "pipeline": intent.pipeline})
        print(f"  {sc['id']:<10} {'✅' if ok else '❌'}  {lat:>8.0f} ms")
    warm = [r["latency_ms"] for r in rows[1:]]
    summary = {
        "model": model, "size": ollama_size(model), "timestamp": datetime.now().isoformat(),
        "score": f"{passed}/{len(SCENARIOS)}",
        "cold_start_ms": round(cold or 0, 1),
        "warm_avg_ms": round(sum(warm) / len(warm), 1) if warm else 0,
        "scenarios": rows,
    }
    print(f"  -> score {summary['score']} · cold {summary['cold_start_ms']:.0f} ms · warm moy {summary['warm_avg_ms']:.0f} ms")
    return summary


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--models", nargs="+", default=RECOMMENDED)
    ap.add_argument("--installed", action="store_true", help="uniquement les modeles deja installes")
    ap.add_argument("--no-pull", action="store_true", help="ne rien telecharger")
    args = ap.parse_args()

    installed = ollama_list()
    print(f"Modeles installes : {installed or '(aucun / ollama indisponible)'}")
    targets = installed if args.installed else args.models

    results = json.loads(RESULTS.read_text()) if RESULTS.exists() else []
    results = [r for r in results if r["model"] not in targets]  # ecrase les reruns
    for m in targets:
        if not ensure_model(m, allow_pull=not args.no_pull, installed=installed):
            continue
        try:
            results.append(bench_model(m))
            RESULTS.write_text(json.dumps(results, ensure_ascii=False, indent=2))
        except Exception as exc:
            print(f"[ERREUR] {m} : {exc}")

    print(f"\n{'='*56}\n  RECAP ({RESULTS.name})\n{'='*56}")
    print(f"  {'Modele':<16}{'Score':<7}{'Cold':<10}{'Warm moy':<10}{'Taille'}")
    for r in sorted(results, key=lambda x: x["warm_avg_ms"]):
        print(f"  {r['model']:<16}{r['score']:<7}{r['cold_start_ms']:>6.0f} ms  {r['warm_avg_ms']:>6.0f} ms  {r['size']}")
    print("\n  Conseil : retenir le modele au meilleur score, puis la latence warm la plus basse.")
    print("  Mets a jour OLLAMA_MODEL dans app/core/config.py avec le gagnant.")


if __name__ == "__main__":
    main()
