"""
Pipeline d'evaluation RetailVision BI — methodo « Mesurer l'immesurable » (SCIAM).

3 etapes pour chaque brique :  SIMULER les inputs  ->  GENERER les outputs  ->  EVALUER.
2 axes : qualite de l'output (metriques) + qualite operationnelle (latence p50/p95).
3 familles de scenarios : ideal / realistic / adverse, chacune avec son seuil d'acceptance.
Metriques principales (bloquantes) vs secondaires (traquees). Gate de regression + code retour CI.

Usage :
    python app/eval/runner.py --brick all --model gemma3:4b --judge-model gemma3:4b
    python app/eval/runner.py --brick intent                 # brique seule
    python app/eval/runner.py --brick narration --dry         # harness sans Ollama (mock)
    python app/eval/runner.py --align app/eval/human_labels.csv
"""
from __future__ import annotations
import argparse, json, sys, time, statistics
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))          # rend 'stt' importable comme dans l'app
import metrics as M
import judges as J

DATASETS = HERE / "datasets"
REPORTS = HERE / "reports"; REPORTS.mkdir(exist_ok=True)

# Seuils d'acceptance (taux de PASS requis par famille) — etape 3 de la feuille de route.
THRESHOLDS = {
    "intent":    {"ideal": 0.95, "realistic": 0.80, "adverse": 1.00},
    "narration": {"ideal": 1.00, "realistic": 0.80, "adverse": 1.00},
    "stt":       {"ideal": 0.90, "realistic": 0.70, "adverse": 1.00},
    "qa":        {"ideal": 1.00, "realistic": 0.80, "adverse": 1.00},
}
WER_PASS = {"ideal": 0.10, "realistic": 0.35, "adverse": 1.01}  # WER max tolere par famille


# --------------------------------------------------------------------------- #
# GENERATION (etape 2) — adaptateurs vers le systeme reel, avec repli mock (--dry)
# --------------------------------------------------------------------------- #
def gen_intent(text, dry):
    from features.voice_navigation.service import VoiceNavigationService
    intent = VoiceNavigationService().parse(text)
    got = {"action": intent.action, "target_page": intent.target_page}
    got.update(intent.parameters or {})
    return got

def gen_narration(kpis, dry):
    if dry:
        d = kpis
        return (f"Le chiffre d'affaires 2025 atteint {d['ca_2025']/1e6:.1f} M€ "
                f"({d['ca_delta_pct']:+.1f}% vs 2024). La region {d['top_region'].split('.')[0]} "
                f"et la categorie {d['top_categorie']} restent en tete, avec une marge de {d['marge_2025']:.1f}%.")
    from features.insights_narration.service import NarrationService
    return NarrationService().generate(kpis)

def gen_stt(audio_path, dry):
    if dry or not audio_path.exists():
        return None  # skip
    from core.stt.engine import transcribe
    return transcribe(str(audio_path))


def gen_qa(case, dry, df):
    from core.domain.models import QuerySpec
    from features.analytics_qa import query_engine as qe
    if dry:  # sans LLM : on teste le MOTEUR a partir de la spec attendue
        es = case.get("expected_spec")
        if es is None:
            return {"ok": True, "valid": False, "rows": []}
        res = qe.execute(QuerySpec(**es), df)
        return {"ok": res.ok, "valid": True, "answer": res.answer, "rows": res.rows, "error": res.error}
    from features.analytics_qa.service import AnalyticsQAService
    res = AnalyticsQAService().answer(case["question"], df)
    return {"ok": res.ok, "valid": getattr(res.spec, "valid", False) if res.spec else False,
            "answer": res.answer, "rows": res.rows, "error": res.error,
            "spec": res.spec.__dict__ if res.spec else None}


def eval_qa_case(case, out):
    if case["scenario"] == "adverse":  # doit etre rejete (hors perimetre / entite invalide)
        primary_pass = (not out.get("valid")) or (not out.get("ok"))
        return {"primary_pass": bool(primary_pass), "metrics": out}
    top = (out.get("rows") or [{}])[0]
    exp_top = case.get("expected_top")
    top_ok = exp_top is None or any(str(exp_top) == str(v) for v in top.values())
    primary_pass = out.get("ok") and out.get("valid") and top_ok
    return {"primary_pass": bool(primary_pass), "metrics": {**out, "top_ok": top_ok}}


# --------------------------------------------------------------------------- #
# EVALUATION (etape 3) par brique
# --------------------------------------------------------------------------- #
def eval_intent_case(case, got):
    s = M.intent_scores(case["expected"], got)
    primary_pass = (s["valid_json"] and s["action_match"] and s["page_ok"]
                    and s["field_ok"] and s["no_hallucination"] and s["recall"] == 1.0)
    return {"primary_pass": bool(primary_pass), "metrics": s,
            "secondary": {"f1": s["f1"], "precision": s["precision"]}}

def eval_narration_case(case, text, judge):
    figs = M.figures_faithful(text, case.get("facts_figures_allowed", []))
    incl = M.contains_all(text, case.get("facts_must_include", []))
    forb = M.contains_none(text, case.get("forbidden_substrings", []))
    kpis = case["kpis"]
    faith = judge.faithfulness(
        facts=[
            f"CA 2025 : {kpis['ca_2025']/1e6:.1f} M€",
            f"Variation CA : {kpis['ca_delta_pct']:+.1f}%",
            f"Variation transactions : {kpis['tx_delta_pct']:+.1f}%",
            f"Marge 2025 : {kpis['marge_2025']:.1f}%",
            f"Variation marge : {kpis['marge_delta_pts']:+.2f} pts",
            f"Variation panier moyen : {kpis['panier_delta_pct']:+.1f}%",
            f"Région leader : {kpis['top_region']}",
            f"Catégorie leader : {kpis['top_categorie']}",
        ],
        generated=text)
    nb = M.sentence_count(text)
    cons = judge.constraints(text, case.get("criteria", {}))
    primary_pass = figs["ok"] and incl["ok"] and forb["ok"] and faith["pass"]
    secondary_pass = cons["pass"] and nb <= case.get("criteria", {}).get("max_sentences", 4)
    return {"primary_pass": bool(primary_pass), "secondary_pass": bool(secondary_pass),
            "metrics": {"figures": figs, "must_include": incl, "forbidden": forb,
                        "judge_faithfulness": faith, "judge_constraints": cons, "sentences": nb}}

def eval_stt_case(case, hyp):
    if hyp is None:
        return {"skipped": True}
    w = M.wer(case["reference"], hyp); c = M.cer(case["reference"], hyp)
    primary_pass = w <= WER_PASS[case["scenario"]]
    return {"primary_pass": bool(primary_pass), "metrics": {"wer": round(w, 3), "cer": round(c, 3), "hyp": hyp}}


# --------------------------------------------------------------------------- #
# ORCHESTRATION
# --------------------------------------------------------------------------- #
def run_brick(brick, model, judge_model, dry):
    data = json.loads((DATASETS / f"{brick}_dataset.json").read_text(encoding="utf-8"))
    judge = J.get_judge(judge_model, dry) if brick == "narration" else None
    df_qa = None
    if brick == "qa":
        from core.data import repository as repo
        df_qa = repo.load_sales()
    results, latencies = [], []

    for case in data["cases"]:
        t0 = time.perf_counter()
        if brick == "intent":
            out = gen_intent(case["input"], dry); ev = eval_intent_case(case, out)
        elif brick == "narration":
            out = gen_narration(case["kpis"], dry); ev = eval_narration_case(case, out, judge)
        elif brick == "stt":
            out = gen_stt(DATASETS / case["audio"], dry); ev = eval_stt_case(case, out)
        else:
            out = gen_qa(case, dry, df_qa); ev = eval_qa_case(case, out)
        lat = (time.perf_counter() - t0) * 1000
        if not ev.get("skipped"):
            latencies.append(lat)
        results.append({"id": case["id"], "scenario": case["scenario"],
                        "primary": case.get("primary", True), "latency_ms": round(lat, 1),
                        "output": out, **ev})

    # agregation par famille de scenario
    fams = {}
    for sc in ("ideal", "realistic", "adverse"):
        rs = [r for r in results if r["scenario"] == sc and not r.get("skipped")]
        if not rs:
            continue
        passed = sum(r.get("primary_pass", False) for r in rs)
        rate = passed / len(rs)
        thr = THRESHOLDS[brick][sc]
        fams[sc] = {"passed": passed, "total": len(rs), "rate": round(rate, 3),
                    "threshold": thr, "go": rate >= thr}

    op = {}
    if latencies:
        op = {"p50_ms": round(statistics.median(latencies), 1),
              "p95_ms": round(sorted(latencies)[max(0, int(len(latencies) * 0.95) - 1)], 1),
              "max_ms": round(max(latencies), 1), "n": len(latencies)}
    skipped = sum(1 for r in results if r.get("skipped"))
    if fams:
        go = all(f["go"] for f in fams.values()); status = "GO" if go else "NO-GO"
    else:
        go = None; status = "SKIPPED"

    return {"brick": brick, "model": model, "judge_model": judge_model if brick == "narration" else None,
            "dry": dry, "timestamp": datetime.now().isoformat(),
            "scenarios": fams, "operational": op, "skipped": skipped, "go": go, "status": status, "cases": results}


def write_reports(reports: list[dict]):
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    jpath = REPORTS / f"eval_{ts}.json"
    jpath.write_text(json.dumps(reports, ensure_ascii=False, indent=2), encoding="utf-8")
    (REPORTS / "last_run.json").write_text(json.dumps(reports, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = [f"# Rapport d'evaluation — RetailVision BI", f"_Genere le {datetime.now():%Y-%m-%d %H:%M}_", ""]
    for r in reports:
        verdict = {"GO": "✅ GO", "NO-GO": "❌ NO-GO", "SKIPPED": "⏭️ SKIPPED"}[r["status"]]
        lines += [f"## Brique : {r['brick']}  → {verdict}",
                  f"Modele : `{r['model']}`" + (f" · juge : `{r['judge_model']}`" if r['judge_model'] else "")
                  + (f" · cas ignores (audio manquant) : {r['skipped']}" if r['skipped'] else ""), ""]
        lines += ["| Scenario | Pass | Total | Taux | Seuil | Statut |", "|---|---|---|---|---|---|"]
        for sc, f in r["scenarios"].items():
            lines.append(f"| {sc} | {f['passed']} | {f['total']} | {f['rate']:.0%} | {f['threshold']:.0%} | "
                         f"{'✅' if f['go'] else '❌'} |")
        if r["operational"]:
            o = r["operational"]
            lines += ["", f"**Qualite operationnelle** — latence p50 {o['p50_ms']} ms · p95 {o['p95_ms']} ms · max {o['max_ms']} ms (n={o['n']})"]
        fails = [c["id"] for c in r["cases"] if not c.get("primary_pass") and not c.get("skipped")]
        if fails:
            lines += ["", f"**Cas en echec :** {', '.join(fails)}"]
        lines.append("")
    mpath = REPORTS / f"eval_{ts}.md"
    mpath.write_text("\n".join(lines), encoding="utf-8")
    return jpath, mpath


def check_regression(current: list[dict]):
    prev_path = REPORTS / "last_run.json"
    # last_run.json vient d'etre ecrase ; on lit l'avant-dernier via les fichiers horodates
    snaps = sorted(REPORTS.glob("eval_*.json"))
    if len(snaps) < 2:
        return []
    prev = json.loads(snaps[-2].read_text(encoding="utf-8"))
    prev_go = {p["brick"]: p["go"] for p in prev}
    notes = []
    for c in current:
        was = prev_go.get(c["brick"])
        if was is True and c["go"] is False:
            notes.append(f"⚠️ REGRESSION sur '{c['brick']}' : GO -> NO-GO depuis le run precedent.")
    return notes


def align_with_human(csv_path: str):
    """Verifie l'alignement metrique<->humain (csv: id,human_pass). Compare au dernier run."""
    import csv
    last = json.loads((REPORTS / "last_run.json").read_text(encoding="utf-8"))
    machine = {c["id"]: c.get("primary_pass") for r in last for c in r["cases"]}
    agree = total = 0
    rows = []
    with open(csv_path, encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            hid = row["id"]; hp = row["human_pass"].strip().lower() in ("1", "true", "vrai", "oui")
            mp = machine.get(hid)
            if mp is None:
                continue
            total += 1; agree += int(hp == mp)
            rows.append((hid, hp, mp, hp == mp))
    rate = agree / total if total else 0.0
    print(f"\nAlignement metrique<->humain : {agree}/{total} = {rate:.0%}")
    for hid, hp, mp, ok in rows:
        print(f"  {'✓' if ok else '✗'} {hid}: humain={hp} machine={mp}")
    return rate


def main():
    ap = argparse.ArgumentParser(description="Pipeline d'evaluation RetailVision BI")
    ap.add_argument("--brick", choices=["intent", "narration", "stt", "qa", "all"], default="all")
    ap.add_argument("--model", default="gemma3:4b")
    ap.add_argument("--judge-model", default="gemma3:4b")
    ap.add_argument("--dry", action="store_true", help="harness sans Ollama (juge mock, narration template)")
    ap.add_argument("--align", metavar="CSV", help="verifie l'alignement avec des labels humains et sort")
    args = ap.parse_args()

    if args.align:
        align_with_human(args.align); return

    bricks = ["intent", "narration", "stt", "qa"] if args.brick == "all" else [args.brick]
    reports = [run_brick(b, args.model, args.judge_model, args.dry) for b in bricks]
    jpath, mpath = write_reports(reports)
    for note in check_regression(reports):
        print(note)

    print(f"\n{'='*60}\n  RESULTAT")
    for r in reports:
        print(f"  {r['brick']:<10} {r['status']:<8}"
              + (f"  (op p95={r['operational'].get('p95_ms')}ms)" if r['operational'] else ""))
    print(f"  Rapports : {mpath.name} / {jpath.name}\n{'='*60}")
    sys.exit(1 if any(r["go"] is False for r in reports) else 0)  # gate CI (SKIPPED non bloquant)


if __name__ == "__main__":
    main()
