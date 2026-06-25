"""
Famille 3 — LLM-as-a-judge (metriques probabilistes).

Principe du talk : on NE demande PAS au juge « est-ce une bonne reponse ? » (trop
subjectif). On lui donne une tache TRES SPECIFIQUE a output CONTRAINT (pass/fail) :
  - faithfulness : cherche contradictions / omissions vs une liste de FAITS.
  - constraints  : verifie concision + ton + absence de preambule.
Chaque juge renvoie {pass: bool, reason: str}. On accepte la variance/biais inherents
(cf. talk) et on verifie ensuite l'ALIGNEMENT avec l'humain (runner.align_with_human).
"""
from __future__ import annotations
import json


class MockJudge:
    """Juge hors-ligne pour tester le harness sans Ollama (mode --dry)."""
    def __init__(self, verdict=True):
        self.verdict = verdict

    def faithfulness(self, facts, generated):
        return {"pass": self.verdict, "reason": "mock", "judge": "mock"}

    def constraints(self, generated, criteria):
        return {"pass": self.verdict, "reason": "mock", "judge": "mock"}


class OllamaJudge:
    """Juge reel via Ollama local. Utilise format=json + temperature 0 (reproductibilite)."""
    def __init__(self, model="gemma3:4b", timeout=30):
        self.model = model
        self.timeout = timeout

    def _ask(self, prompt: str) -> dict:
        import ollama
        resp = ollama.Client(timeout=self.timeout).chat(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            options={"temperature": 0, "num_predict": 200},
            format="json",
        )
        try:
            data = json.loads(resp["message"]["content"])
        except Exception:
            return {"pass": False, "reason": "json invalide du juge", "judge": self.model}
        verdict = data.get("pass")
        if isinstance(verdict, str):
            verdict = verdict.strip().lower() in ("true", "vrai", "oui", "pass")
        return {"pass": bool(verdict), "reason": data.get("reason", ""), "judge": self.model}

    def faithfulness(self, facts: list[str], generated: str) -> dict:
        prompt = (
            "Tu es un evaluateur. On te donne une LISTE DE FAITS de reference et une REPONSE generee.\n"
            "Ton unique role : detecter s'il existe une CONTRADICTION ou une OMISSION d'un fait important "
            "dans la reponse, ou un CHIFFRE/NOM invente absent des faits.\n"
            "Reponds UNIQUEMENT un JSON {\"pass\": true/false, \"reason\": \"...\"}. "
            "pass=true si la reponse est fidele aux faits (pas de contradiction ni d'invention).\n\n"
            f"FAITS:\n- " + "\n- ".join(str(f) for f in facts) + f"\n\nREPONSE:\n{generated}"
        )
        return self._ask(prompt)

    def constraints(self, generated: str, criteria: dict) -> dict:
        maxs = criteria.get("max_sentences", 4)
        prompt = (
            "Tu es un evaluateur de forme. Verifie ces contraintes sur la REPONSE :\n"
            f"- au maximum {maxs} phrases\n- ecrite en francais\n- ton {criteria.get('tone','professionnel')}\n"
            "- pas de titre ni de preambule (commence directement par la synthese)\n"
            "Reponds UNIQUEMENT un JSON {\"pass\": true/false, \"reason\": \"...\"}.\n\n"
            f"REPONSE:\n{generated}"
        )
        return self._ask(prompt)


def get_judge(model: str | None, dry: bool):
    return MockJudge() if dry else OllamaJudge(model=model or "gemma3:4b")
