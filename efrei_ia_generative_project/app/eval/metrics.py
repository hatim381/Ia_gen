"""
Metriques d'evaluation — 4 familles (cf. talk SCIAM « Mesurer l'immesurable ») :
  1. Deterministe : WER/CER, exact-match, F1 entites, presence de chaine/chiffre.
  2. Semantique   : similarite de sens (optionnelle, lourde ; volontairement minoritaire).
  3. Probabiliste : LLM-as-a-judge -> voir judges.py.
  4. Humaine      : chargement de labels humains + calcul d'alignement -> voir runner.py.

Toutes ces metriques sont des PROXYS de l'evaluation humaine. Chacune verifie UN aspect ;
on les agrege (principales = bloquantes, secondaires = traquees).
"""
from __future__ import annotations
import re
import unicodedata


# ----------------------------------------------------------------------------- #
# 1. DETERMINISTE
# ----------------------------------------------------------------------------- #

def _norm(s: str) -> str:
    """Minuscule, sans accents, espaces normalises — pour comparaisons robustes."""
    s = unicodedata.normalize("NFD", str(s))
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return re.sub(r"\s+", " ", s.lower()).strip()


def wer(reference: str, hypothesis: str) -> float:
    """Word Error Rate. Utilise jiwer si dispo, sinon repli Levenshtein sur mots."""
    try:
        import jiwer
        if not reference.strip():
            return 0.0 if not hypothesis.strip() else 1.0
        return float(jiwer.wer(reference, hypothesis))
    except ImportError:
        return _levenshtein_rate(reference.split(), hypothesis.split())


def cer(reference: str, hypothesis: str) -> float:
    """Character Error Rate."""
    try:
        import jiwer
        if not reference.strip():
            return 0.0 if not hypothesis.strip() else 1.0
        return float(jiwer.cer(reference, hypothesis))
    except ImportError:
        return _levenshtein_rate(list(reference), list(hypothesis))


def _levenshtein_rate(ref: list, hyp: list) -> float:
    n, m = len(ref), len(hyp)
    if n == 0:
        return 0.0 if m == 0 else 1.0
    prev = list(range(m + 1))
    for i in range(1, n + 1):
        cur = [i] + [0] * m
        for j in range(1, m + 1):
            cost = 0 if ref[i - 1] == hyp[j - 1] else 1
            cur[j] = min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + cost)
        prev = cur
    return prev[m] / n


def exact_match(expected, got) -> bool:
    return _norm(expected) == _norm(got)


def intent_scores(expected: dict, got: dict) -> dict:
    """
    Compare un JSON d'intention attendu vs genere. Output CONTRAINT.
    Retourne action_match, valid_json, precision/rappel/F1 sur les entites NON NULLES attendues,
    et le detail par champ.
    """
    ENT = ["date_start", "date_end", "region", "categorie"]
    got = got or {}
    detail = {}

    # action : gere les attentes speciales du dataset adverse
    exp_action = expected.get("action", "unknown")
    got_action = got.get("action", "unknown")
    if exp_action == "unknown_or_no_region":
        action_match = True  # on ne juge que l'absence d'entite inventee (cf. region ci-dessous)
    else:
        action_match = _norm(exp_action) == _norm(got_action)
    detail["action"] = {"expected": exp_action, "got": got_action, "ok": action_match}

    # target_page si attendu
    page_ok = True
    if "target_page" in expected:
        page_ok = _norm(expected.get("target_page")) == _norm(got.get("target_page"))
        detail["target_page"] = {"expected": expected.get("target_page"),
                                 "got": got.get("target_page"), "ok": page_ok}

    # clear_filter field
    field_ok = True
    if "field" in expected:
        field_ok = _norm(expected.get("field")) == _norm((got.get("parameters") or {}).get("field", got.get("field", "")))
        detail["field"] = {"expected": expected.get("field"), "ok": field_ok}

    # entites : precision/rappel sur les champs attendus non nuls
    tp = fp = fn = 0
    for k in ENT:
        exp_v = expected.get(k)
        got_v = got.get(k)
        if exp_v not in (None, "", "null"):
            ok = _norm(exp_v) == _norm(got_v)
            detail[k] = {"expected": exp_v, "got": got_v, "ok": ok}
            tp += int(ok)
            fn += int(not ok)
        elif got_v not in (None, "", "null"):
            # entite inventee alors qu'on n'attendait rien -> faux positif (hallucination)
            detail[k] = {"expected": None, "got": got_v, "ok": False, "hallucinated": True}
            fp += 1

    precision = tp / (tp + fp) if (tp + fp) else 1.0
    recall = tp / (tp + fn) if (tp + fn) else 1.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 1.0
    no_hallucination = fp == 0

    return {
        "action_match": action_match,
        "page_ok": page_ok,
        "field_ok": field_ok,
        "valid_json": isinstance(got, dict),
        "precision": round(precision, 3),
        "recall": round(recall, 3),
        "f1": round(f1, 3),
        "no_hallucination": no_hallucination,
        "detail": detail,
    }


_NUM_RE = re.compile(r"-?\d+(?:[.,]\d+)?")

def extract_numbers(text: str) -> list[float]:
    out = []
    for m in _NUM_RE.findall(text or ""):
        try:
            out.append(round(float(m.replace(",", ".")), 1))
        except ValueError:
            pass
    return out


def figures_faithful(text: str, allowed: list[float], tol: float = 0.15) -> dict:
    """
    Check deterministe anti-hallucination : tout chiffre cite dans le texte doit
    correspondre (a tolerance pres) a une valeur autorisee issue des KPIs.
    """
    cited = [c for c in extract_numbers(text) if not (c == int(c) and 1900 <= c <= 2100)]
    allowed_abs = [abs(a) for a in allowed]
    unexplained = []
    for c in cited:
        if not any(abs(abs(c) - a) <= max(tol, a * tol) for a in allowed_abs):
            unexplained.append(c)
    return {"cited": cited, "unexplained": unexplained, "ok": len(unexplained) == 0}


def contains_all(text: str, substrings: list[str]) -> dict:
    miss = [s for s in substrings if _norm(s) not in _norm(text)]
    return {"ok": not miss, "missing": miss}


def contains_none(text: str, forbidden: list[str]) -> dict:
    hit = [s for s in (forbidden or []) if _norm(s) in _norm(text)]
    return {"ok": not hit, "found": hit}


def sentence_count(text: str) -> int:
    return len([s for s in re.split(r"[.!?]+", text or "") if s.strip()])


# ----------------------------------------------------------------------------- #
# 2. SEMANTIQUE (optionnelle — le talk la dit « old school », a utiliser avec prudence)
# ----------------------------------------------------------------------------- #

def semantic_similarity(a: str, b: str):
    """Cosine sur embeddings sentence-transformers si installe, sinon None."""
    try:
        from sentence_transformers import SentenceTransformer, util
    except ImportError:
        return None
    model = _get_st_model()
    if model is None:
        return None
    emb = model.encode([a, b])
    return float(util.cos_sim(emb[0], emb[1]))


_ST_MODEL = None
def _get_st_model():
    global _ST_MODEL
    if _ST_MODEL is None:
        try:
            from sentence_transformers import SentenceTransformer
            _ST_MODEL = SentenceTransformer("sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")
        except Exception:
            _ST_MODEL = None
    return _ST_MODEL
