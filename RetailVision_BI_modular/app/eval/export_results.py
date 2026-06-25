"""
Exporte les rapports d'évaluation en deux fichiers :
  - eval_summary.csv   : une ligne par (run, brique) — vue synthétique
  - eval_details.csv   : une ligne par cas — vue détaillée

Usage :
    python app/eval/export_results.py                    # exporte tous les runs
    python app/eval/export_results.py --last             # exporte uniquement le dernier run
    python app/eval/export_results.py --out mon_dossier  # dossier de sortie personnalisé
"""
from __future__ import annotations
import argparse
import csv
import json
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPORTS = HERE / "reports"


def load_reports(last_only: bool) -> list[dict]:
    if last_only:
        path = REPORTS / "last_run.json"
        if not path.exists():
            raise FileNotFoundError("Aucun run trouvé. Lancez d'abord runner.py.")
        return json.loads(path.read_text(encoding="utf-8"))

    runs = []
    for p in sorted(REPORTS.glob("eval_*.json")):
        try:
            runs.extend(json.loads(p.read_text(encoding="utf-8")))
        except Exception:
            pass
    if not runs:
        raise FileNotFoundError("Aucun rapport trouvé dans reports/.")
    return runs


def write_summary(reports: list[dict], out_dir: Path) -> Path:
    path = out_dir / "eval_summary.csv"
    fields = [
        "timestamp", "brick", "model", "judge_model", "dry", "status",
        "ideal_pass", "ideal_total", "ideal_rate", "ideal_threshold", "ideal_go",
        "realistic_pass", "realistic_total", "realistic_rate", "realistic_threshold", "realistic_go",
        "adverse_pass", "adverse_total", "adverse_rate", "adverse_threshold", "adverse_go",
        "latency_p50_ms", "latency_p95_ms", "latency_max_ms", "skipped_cases",
    ]
    with path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        for r in reports:
            sc = r.get("scenarios", {})
            op = r.get("operational", {})
            row = {
                "timestamp": r.get("timestamp", ""),
                "brick": r.get("brick", ""),
                "model": r.get("model", ""),
                "judge_model": r.get("judge_model") or "",
                "dry": r.get("dry", False),
                "status": r.get("status", ""),
                "skipped_cases": r.get("skipped", 0),
                "latency_p50_ms": op.get("p50_ms", ""),
                "latency_p95_ms": op.get("p95_ms", ""),
                "latency_max_ms": op.get("max_ms", ""),
            }
            for fam in ("ideal", "realistic", "adverse"):
                f = sc.get(fam, {})
                row[f"{fam}_pass"] = f.get("passed", "")
                row[f"{fam}_total"] = f.get("total", "")
                row[f"{fam}_rate"] = f"{f['rate']:.1%}" if "rate" in f else ""
                row[f"{fam}_threshold"] = f"{f['threshold']:.0%}" if "threshold" in f else ""
                row[f"{fam}_go"] = f.get("go", "")
            w.writerow(row)
    return path


def write_details(reports: list[dict], out_dir: Path) -> Path:
    path = out_dir / "eval_details.csv"
    fields = [
        "timestamp", "brick", "model", "case_id", "scenario", "primary",
        "primary_pass", "latency_ms", "pipeline",
        # intent
        "action_match", "f1", "precision", "recall", "no_hallucination",
        # narration
        "figures_ok", "must_include_ok", "forbidden_ok", "judge_faithfulness", "judge_constraints", "sentences",
        # stt
        "wer", "cer",
        # qa
        "qa_ok", "qa_valid",
        # commun
        "output_summary", "error",
    ]
    with path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        for r in reports:
            ts = r.get("timestamp", "")
            brick = r.get("brick", "")
            model = r.get("model", "")
            for c in r.get("cases", []):
                m = c.get("metrics", {})
                out = c.get("output") or {}
                row: dict = {
                    "timestamp": ts,
                    "brick": brick,
                    "model": model,
                    "case_id": c.get("id", ""),
                    "scenario": c.get("scenario", ""),
                    "primary": c.get("primary", True),
                    "primary_pass": c.get("primary_pass", ""),
                    "latency_ms": c.get("latency_ms", ""),
                    "pipeline": out.get("pipeline", "") if isinstance(out, dict) else "",
                    "error": out.get("error", "") if isinstance(out, dict) else "",
                }
                if brick == "intent":
                    row["action_match"] = m.get("action_match", "")
                    row["f1"] = m.get("f1", "")
                    row["precision"] = m.get("precision", "")
                    row["recall"] = m.get("recall", "")
                    row["no_hallucination"] = m.get("no_hallucination", "")
                    row["output_summary"] = f"action={out.get('action')} region={out.get('region')} cat={out.get('categorie')}"
                elif brick == "narration":
                    row["figures_ok"] = m.get("figures", {}).get("ok", "")
                    row["must_include_ok"] = m.get("must_include", {}).get("ok", "")
                    row["forbidden_ok"] = m.get("forbidden", {}).get("ok", "")
                    row["judge_faithfulness"] = m.get("judge_faithfulness", {}).get("pass", "")
                    row["judge_constraints"] = m.get("judge_constraints", {}).get("pass", "")
                    row["sentences"] = m.get("sentences", "")
                    text = out if isinstance(out, str) else ""
                    row["output_summary"] = text[:120].replace("\n", " ") if text else ""
                elif brick == "stt":
                    row["wer"] = m.get("wer", "")
                    row["cer"] = m.get("cer", "")
                    row["output_summary"] = str(out)[:120] if out else ""
                elif brick == "qa":
                    row["qa_ok"] = out.get("ok", "") if isinstance(out, dict) else ""
                    row["qa_valid"] = out.get("valid", "") if isinstance(out, dict) else ""
                    row["output_summary"] = str(out.get("answer", ""))[:120] if isinstance(out, dict) else ""
                w.writerow(row)
    return path


def main():
    ap = argparse.ArgumentParser(description="Export des rapports d'évaluation en CSV")
    ap.add_argument("--last", action="store_true", help="Exporte uniquement le dernier run")
    ap.add_argument("--out", default=str(REPORTS), help="Dossier de sortie (défaut : reports/)")
    args = ap.parse_args()

    reports = load_reports(args.last)
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    s = write_summary(reports, out_dir)
    d = write_details(reports, out_dir)

    print(f"Synthèse  : {s}")
    print(f"Détails   : {d}")
    print(f"Runs exportés : {len(set(r.get('timestamp','') for r in reports))}")
    print(f"Cas exportés  : {sum(len(r.get('cases', [])) for r in reports)}")


if __name__ == "__main__":
    main()
