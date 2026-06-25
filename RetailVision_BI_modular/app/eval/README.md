# Pipeline d'évaluation — RetailVision BI

Implémentation directe de la méthodologie **« Mesurer l'immesurable : comment évaluer
les systèmes à base d'IA générative ? »** (E. Pacquelet, SCIAM), appliquée à nos 3 briques IA.

## Pourquoi c'est nécessaire
On ne contrôle ni les inputs (commandes vocales libres) ni les outputs (LLM créatif).
On transforme donc une évaluation **qualitative et manuelle** en une mesure
**quantitative, automatisée et complète** — lançable à tout moment, sans mobiliser les équipes.

## Les 3 étapes (toujours les mêmes)
1. **Simuler les inputs** — depuis un *dataset d'évaluation* (le cœur : input + output attendu).
2. **Générer les outputs** — on rejoue le système réel (`stt.intent_parser`, `stt.narrator`, `stt.transcriber`).
3. **Évaluer** — par familles de métriques, contre le dataset.

## Les 3 familles de scénarios (`datasets/*.json`)
- **idéal** — inputs parfaits (seuil d'acceptance haut).
- **réaliste** — mots-clés, fautes, langage oral, contexte partiel.
- **adverse** — injection de prompt, hors-périmètre, entités invalides (centré sécurité).

## Les 2 axes
- **Qualité de l'output** — les métriques ci-dessous.
- **Qualité opérationnelle** — latence p50/p95/max (un bon output trop lent = mauvais produit).

## Les 4 familles de métriques (toutes = proxys de l'humain)
| Famille | Où | Usage |
|---|---|---|
| Déterministe | `metrics.py` | WER/CER (STT), exact-match + F1 entités (intent), présence chiffres/chaînes (narration) |
| Sémantique | `metrics.py` | similarité de sens (optionnelle, `sentence-transformers`) |
| LLM-as-a-judge | `judges.py` | tâches **ciblées pass/fail** : contradictions/omissions, concision/ton |
| Humaine | `runner.py --align` | alignement labels humains ↔ métriques |

**Output contraint vs libre** : l'extraction d'intention (JSON) se juge en déterministe ;
la narration (texte libre) exige le juge LLM ciblé + checks déterministes anti-hallucination.

**Principales vs secondaires** : une métrique *principale* en échec bloque le GO
(ex : injection non rejetée, chiffre halluciné). Les *secondaires* (concision, ton) sont traquées sans bloquer.

## Lancer
```bash
pip install -r requirements.txt          # ajoute jiwer
ollama pull gemma3:4b                     # pour les appels réels

python app/eval/runner.py --brick all --model gemma3:4b --judge-model gemma3:4b
python app/eval/runner.py --brick intent          # une brique
python app/eval/runner.py --brick narration --dry # harness sans Ollama (juge mock)
python app/eval/test_metrics.py                   # self-test déterministe
python app/eval/runner.py --align app/eval/human_labels.csv   # alignement humain
```
Le runner écrit un rapport **JSON + Markdown** dans `reports/`, calcule la **latence**,
détecte les **régressions** entre runs et renvoie un **code retour CI** (≠0 si NO-GO).

## STT
Déposez vos enregistrements `.wav` dans `datasets/audio/` (noms dans `stt_dataset.json`).
Sans audio, les cas STT sont marqués `SKIPPED` (non bloquant).

## Feuille de route (ordre de travail)
guidelines (`guidelines.md`) → dataset → métriques + seuils → pipeline → alignement humain → prod.
Le dataset est **vivant** : la prod réinjecte les cas non anticipés et les régressions corrigées.
