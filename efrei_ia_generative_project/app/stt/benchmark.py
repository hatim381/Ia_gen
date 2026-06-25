"""
Benchmark comparatif des modèles LLM pour l'extraction d'intentions.

Usage :
    # Un seul modèle
    python benchmark.py mistral

    # Plusieurs modèles d'un coup
    python benchmark.py mistral qwen2.5:7b phi3.5

    # Baseline déjà installé
    python benchmark.py gemma3:4b

Les résultats sont ajoutés dans benchmark_results.json (dans le même dossier).
À la fin, affiche un tableau récapitulatif de tous les runs accumulés.
"""

import argparse
import json
import sys
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path

import ollama

RESULTS_FILE = Path(__file__).parent / "benchmark_results.json"

REGIONS = ["Nord", "Sud", "Est", "Ouest", "Île-de-France"]
CATEGORIES = ["Électronique", "Vêtements", "Alimentation", "Maison", "Sport"]

# Les 7 scénarios de analyse_ia.md
# expected = None signifie qu'on vérifie juste l'absence de crash (T7)
SCENARIOS: list[dict] = [
    {
        "id": "T1",
        "command": "Accueil",
        "pipeline": "fast_track",
        "expected": {"action": "navigate", "target_page": "Vue Globale"},
        "note": "Navigation fast-track",
    },
    {
        "id": "T2",
        "command": "Régions",
        "pipeline": "fast_track",
        "expected": {"action": "navigate", "target_page": "Régions"},
        "note": "Navigation fast-track",
    },
    {
        "id": "T3",
        "command": "Reset les filtres",
        "pipeline": "fast_track",
        "expected": {"action": "reset"},
        "note": "Reset fast-track",
    },
    {
        "id": "T4",
        "command": "Affiche les ventes de janvier 2025",
        "pipeline": "llm",
        "expected": {
            "action": "filter",
            "date_start": "2025-01-01",
            "date_end": "2025-01-31",
        },
        "note": "Filtre date mensuel",
    },
    {
        "id": "T5",
        "command": "Région Nord",
        "pipeline": "llm",
        "expected": {"action": "filter", "region": "Nord"},
        "note": "Filtre région",
    },
    {
        "id": "T6",
        "command": "Catégorie Sport entre mars et juin 2024",
        "pipeline": "llm",
        "expected": {
            "action": "filter",
            "categorie": "Sport",
            "date_start": "2024-03-01",
            "date_end": "2024-06-30",
        },
        "note": "Filtre multi-critères",
    },
    {
        "id": "T7",
        "command": "Météo demain",
        "pipeline": "llm",
        "expected": {"action": "unknown"},
        "note": "Hors périmètre — pas de crash",
    },
]


@dataclass
class ScenarioResult:
    scenario_id: str
    command: str
    pipeline: str
    passed: bool
    latency_ms: float
    raw_output: dict = field(default_factory=dict)
    error: str = ""
    entities_correct: int = 0
    entities_expected: int = 0


def _call_llm(model: str, command: str) -> tuple[dict, float]:
    """Appelle _ollama_parse depuis intent_parser — même prompt que l'app réelle."""
    sys.path.insert(0, str(Path(__file__).parent.parent))
    import importlib
    import stt.intent_parser as ip_module
    # Force le modèle passé en argument, indépendamment de OLLAMA_MODEL
    original_model = ip_module.OLLAMA_MODEL
    ip_module.OLLAMA_MODEL = model
    try:
        t0 = time.perf_counter()
        intent = ip_module._ollama_parse(command)
        latency_ms = (time.perf_counter() - t0) * 1000
    finally:
        ip_module.OLLAMA_MODEL = original_model

    output = {
        "action": intent.action,
        "target_page": intent.target_page,
        **(intent.parameters or {}),
    }
    return output, latency_ms


def _check_entities(output: dict, expected: dict) -> tuple[int, int]:
    """Retourne (entités_correctes, entités_attendues) sur les champs filtrables."""
    filterable = ["action", "target_page", "date_start", "date_end", "region", "categorie"]
    correct = 0
    total = 0
    for key in filterable:
        if key not in expected:
            continue
        total += 1
        if str(output.get(key, "")).lower() == str(expected[key]).lower():
            correct += 1
    return correct, total


def run_scenario(scenario: dict, model: str) -> ScenarioResult:
    """Exécute un scénario et retourne le résultat."""
    sid = scenario["id"]
    command = scenario["command"]
    pipeline = scenario["pipeline"]
    expected = scenario["expected"]

    # Les fast-track (T1, T2, T3) ne passent pas par le LLM — on les rejoue
    # via le regex du pipeline réel et on mesure la latence regex uniquement.
    if pipeline == "fast_track":
        sys.path.insert(0, str(Path(__file__).parent.parent))
        from stt.intent_parser import _fast_track

        t0 = time.perf_counter()
        intent = _fast_track(command)
        latency_ms = (time.perf_counter() - t0) * 1000

        if intent is None:
            return ScenarioResult(
                scenario_id=sid,
                command=command,
                pipeline=pipeline,
                passed=False,
                latency_ms=latency_ms,
                error="fast_track returned None",
            )

        output = {"action": intent.action, "target_page": intent.target_page}
        correct, total = _check_entities(output, expected)
        passed = correct == total

        return ScenarioResult(
            scenario_id=sid,
            command=command,
            pipeline=pipeline,
            passed=passed,
            latency_ms=latency_ms,
            raw_output=output,
            entities_correct=correct,
            entities_expected=total,
        )

    # Scénarios LLM
    try:
        output, latency_ms = _call_llm(model, command)
    except Exception as exc:
        return ScenarioResult(
            scenario_id=sid,
            command=command,
            pipeline=pipeline,
            passed=False,
            latency_ms=0,
            error=str(exc),
        )

    correct, total = _check_entities(output, expected)

    # T7 : pas de crash + action=unknown suffit
    if sid == "T7":
        passed = output.get("action") == "unknown"
    else:
        passed = correct == total

    return ScenarioResult(
        scenario_id=sid,
        command=command,
        pipeline=pipeline,
        passed=passed,
        latency_ms=latency_ms,
        raw_output=output,
        entities_correct=correct,
        entities_expected=total,
    )


def benchmark_model(model: str) -> dict:
    """Exécute tous les scénarios pour un modèle, retourne un dict de résultats."""
    print(f"\n{'='*60}")
    print(f"  Modèle : {model}")
    print(f"{'='*60}")

    results = []
    for scenario in SCENARIOS:
        sid = scenario["id"]
        print(f"  {sid} — {scenario['command'][:45]:<45}", end=" ", flush=True)
        result = run_scenario(scenario, model)
        status = "✅" if result.passed else "❌"
        print(f"{status}  {result.latency_ms:>7.1f} ms")
        results.append(asdict(result))

    llm_results = [r for r in results if r["pipeline"] == "llm"]
    total_passed = sum(r["passed"] for r in results)
    llm_passed = sum(r["passed"] for r in llm_results)
    llm_latencies = [r["latency_ms"] for r in llm_results if r["latency_ms"] > 0]
    avg_latency = sum(llm_latencies) / len(llm_latencies) if llm_latencies else 0

    summary = {
        "model": model,
        "timestamp": datetime.now().isoformat(),
        "score_total": f"{total_passed}/{len(SCENARIOS)}",
        "score_llm": f"{llm_passed}/{len(llm_results)}",
        "avg_latency_llm_ms": round(avg_latency, 1),
        "scenarios": results,
    }

    print(f"\n  Score global  : {summary['score_total']}")
    print(f"  Score LLM     : {summary['score_llm']}")
    print(f"  Latence moy.  : {avg_latency:.0f} ms")

    return summary


def load_existing_results() -> list[dict]:
    if RESULTS_FILE.exists():
        return json.loads(RESULTS_FILE.read_text(encoding="utf-8"))
    return []


def save_results(all_results: list[dict]) -> None:
    RESULTS_FILE.write_text(
        json.dumps(all_results, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def print_summary_table(all_results: list[dict]) -> None:
    print(f"\n{'='*60}")
    print("  RÉCAPITULATIF GLOBAL")
    print(f"{'='*60}")
    header = f"  {'Modèle':<20} {'Score':<8} {'LLM':<8} {'Latence moy.':<14} {'Date'}"
    print(header)
    print(f"  {'-'*56}")
    for r in all_results:
        date = r["timestamp"][:10]
        print(
            f"  {r['model']:<20} {r['score_total']:<8} {r['score_llm']:<8}"
            f" {r['avg_latency_llm_ms']:>8.0f} ms    {date}"
        )
    print(f"\n  Résultats complets : {RESULTS_FILE}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Benchmark LLM pour RetailVision BI")
    parser.add_argument(
        "models",
        nargs="+",
        help="Nom(s) du/des modèle(s) Ollama à tester (ex: mistral qwen2.5:7b)",
    )
    args = parser.parse_args()

    all_results = load_existing_results()
    already_run = {r["model"] for r in all_results}

    for model in args.models:
        if model in already_run:
            print(f"\n[INFO] {model} déjà présent dans les résultats — on l'écrase.")
            all_results = [r for r in all_results if r["model"] != model]

        try:
            summary = benchmark_model(model)
            all_results.append(summary)
            save_results(all_results)
            print(f"\n  [Sauvegardé dans {RESULTS_FILE.name}]")
        except Exception as exc:
            print(f"\n  [ERREUR] {model} : {exc}")
            print("  Vérifiez qu'Ollama tourne et que le modèle est installé.")

    print_summary_table(all_results)


if __name__ == "__main__":
    main()
