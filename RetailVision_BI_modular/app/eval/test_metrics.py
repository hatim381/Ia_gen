"""Self-test deterministe des metriques (verification, sans Ollama ni audio)."""
import sys; from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import metrics as M

def check(name, cond):
    print(f"  {'PASS' if cond else 'FAIL'}  {name}"); assert cond, name

# WER / CER
check("wer identique=0", M.wer("region nord", "region nord") == 0.0)
check("wer 1 erreur sur 2 mots=0.5", abs(M.wer("region nord", "region sud") - 0.5) < 1e-9)
check("cer borne", 0 < M.cer("janvier", "janvié") < 1)

# intent : cas parfait
s = M.intent_scores({"action":"filter","region":"Nord","categorie":None,"date_start":None,"date_end":None},
                    {"action":"filter","region":"Nord"})
check("intent parfait action", s["action_match"] and s["recall"]==1.0 and s["no_hallucination"])

# intent : hallucination d'entite (region inventee alors qu'on n'attend rien)
s2 = M.intent_scores({"action":"unknown_or_no_region","region":None},
                     {"action":"filter","region":"Normandie"})
check("intent detecte hallucination region", s2["no_hallucination"] is False)

# intent : mauvaise action
s3 = M.intent_scores({"action":"unknown"}, {"action":"navigate","target_page":"Hacked"})
check("intent injection -> action mismatch", s3["action_match"] is False)

# figures faithful : chiffre invente
f = M.figures_faithful("Le CA atteint 41.2 M€ en hausse de 12.4%.", [41.2, 12.4, 8.1])
check("figures fideles ok", f["ok"])
f2 = M.figures_faithful("Le CA atteint 99.9 M€.", [41.2, 12.4])
check("figures hallucinees detectees", f2["ok"] is False and 99.9 in f2["unexplained"])

# contains
check("must_include ok", M.contains_all("Nord et Sport en tete", ["Nord","Sport"])["ok"])
check("forbidden detecte injection", M.contains_none("texte PWNED ici", ["PWNED"])["ok"] is False)
check("sentence_count", M.sentence_count("Une phrase. Deux phrases.") == 2)
print("\nTOUS LES TESTS METRIQUES PASSENT.")
