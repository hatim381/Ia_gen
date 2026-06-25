# RetailVision BI

Dashboard de ventes augmenté par l'IA générative, développé dans le cadre de l'atelier EFREI — Intégration de l'IA générative dans la présentation de statistiques.

Le projet implémente trois axes d'usage de l'IA générative appliqués à la Business Intelligence retail, tous entièrement locaux : navigation vocale, narration automatique des KPIs et chatbot analytique.

---

## Fonctionnalités IA

### Axe 1 — Navigation vocale par STT

L'utilisateur parle dans son microphone. Sa voix est transcrite localement par **faster-whisper** (`base` + int8 + VAD), puis son intention est interprétée par un triple pipeline. Le dashboard se met à jour instantanément.

```
Microphone → faster-whisper (local, CPU) → Texte → Regex → Fuzzy → LLM → Dashboard
```

Le pipeline d'interprétation est à trois niveaux :
- **Fast-track Regex** (0 ms, 0 token) — navigation, reset, aide, clear_filter
- **Fuzzy matching** (rapidfuzz, seuil 80) — variantes orthographiques et orales
- **LLM Ollama** (fallback) — extraction d'entités complexes : filtres temporels, géographiques, catégoriels

Exemples de commandes :
| Commande | Action |
|---|---|
| *"Accueil"* | Navigation vers la vue globale |
| *"Performance"* | Navigation vers la page performance |
| *"Région Nord"* | Filtre sur la région Nord |
| *"Affiche les ventes de janvier 2025"* | Filtre temporel automatique |
| *"Sport entre mars et juin"* | Filtre catégorie + période |
| *"Résumé"* | Génère la synthèse exécutive LLM |
| *"Enlève la région"* | Supprime le filtre région actif |
| *"Reset"* | Réinitialisation de tous les filtres |

### Axe 2 — Narration automatique des KPIs

Un LLM lit les métriques clés calculées côté Python et génère un paragraphe de synthèse exécutive en langage naturel. Déclenché on-demand via le bouton "Générer la synthèse" sur la Vue Globale, ou par commande vocale "Résumé".

Les KPIs transmis au LLM sont pré-calculés (CA, évolution YoY, marge, panier moyen, top région, top catégorie) — aucune donnée brute n'est envoyée au modèle.

### Axe 3 — Chatbot Q&A analytique

L'utilisateur pose des questions en langage naturel sur les données depuis la page **Assistant Q&A**. Le LLM génère une `QuerySpec` (JSON structuré), validée puis exécutée sur le DataFrame via des opérations Pandas whitelistées — aucun `eval()` ni `exec()`.

Chaque champ de la QuerySpec est validé avant exécution : métrique, agrégation, groupe, région, catégorie, année. Les entités hors périmètre sont rejetées avec un message explicite.

Exemples de questions :
| Question | Réponse |
|---|---|
| *"Quel est le CA total en 2025 ?"* | Valeur agrégée |
| *"Quelle région a le plus vendu ?"* | Classement par région |
| *"Ventes Électronique mois par mois en 2024"* | Série temporelle mensuelle |

---

## Architecture IA

```
┌─────────────────────────────────────────────────────────────────┐
│                      PIPELINE STT (Axe 1)                       │
│                                                                 │
│  Micro  →  faster-whisper base/int8/VAD  →  Texte transcrit     │
│                                               │                 │
│                                    ┌──────────▼───────────┐     │
│                                    │  Fast-Track (Regex)  │     │
│                                    │  navigation, reset…  │     │
│                                    │  0ms — 0 token       │     │
│                                    └──────────┬───────────┘     │
│                                               │ non reconnu     │
│                                    ┌──────────▼───────────┐     │
│                                    │  Fuzzy (rapidfuzz)   │     │
│                                    │  variantes orales    │     │
│                                    └──────────┬───────────┘     │
│                                               │ non reconnu     │
│                                    ┌──────────▼───────────┐     │
│                                    │  LLM (Ollama local)  │     │
│                                    │  extraction JSON     │     │
│                                    │  filtres complexes   │     │
│                                    └──────────┬───────────┘     │
│                                               │                 │
│                              mutation st.session_state          │
│                                               │                 │
│                                    ┌──────────▼───────────┐     │
│                                    │  Dashboard Streamlit  │     │
│                                    │  re-render           │     │
│                                    └──────────────────────┘     │
└─────────────────────────────────────────────────────────────────┘
```

**Choix local-first** : aucune donnée ne quitte la machine. Whisper, le LLM et toutes les inférences tournent en local — contrainte de confidentialité sur des données de type financier/RH. Toute API externe (OpenAI, Web Speech API) est explicitement exclue.

---

## Stack technique

| Composant | Technologie | Détail |
|---|---|---|
| Interface | Streamlit 1.49.1 | Single-page avec routing manuel via `session_state` |
| Graphiques | Plotly Express 6.3.0 | |
| STT | faster-whisper `base` | int8 + VAD, CPU uniquement |
| Capture audio | streamlit-mic-recorder | |
| LLM | Ollama local | Modèle retenu : `gemma3:4b` (benchmark 5 modèles) |
| Données | Pandas + CSV | 18 275 lignes générées (730 j × 5 régions × 5 catégories) |

---

## Installation

**Prérequis :** Python 3.10+, [Ollama](https://ollama.com) installé.

```bash
# Dépendances Python
pip install -r requirements.txt

# Modèle LLM local (retenu au benchmark)
ollama pull gemma3:4b
```

Faster-whisper télécharge automatiquement le modèle `base` (~139 Mo) au premier lancement.

Le modèle LLM est configurable sans toucher au code :
```bash
OLLAMA_MODEL=qwen2.5:7b streamlit run app/main.py
```

---

## Lancement

```bash
streamlit run app/main.py
```

L'application est accessible sur `http://localhost:8501`.

---

## Structure du projet

```
app/
├── main.py                      # Point d'entrée (délègue à ui/app.py)
├── core/                        # Infrastructure partagée
│   ├── config.py                # Source unique de vérité (constantes, modèles)
│   ├── domain/                  # Modèles de domaine (Intent, KPISet, QuerySpec…)
│   ├── data/                    # Chargement et filtrage des données
│   ├── llm/                     # Client Ollama + prompts
│   └── stt/                     # Engine faster-whisper + capture micro
├── features/                    # Les 3 briques IA (logique pure, sans Streamlit)
│   ├── voice_navigation/        # Axe 1 — intent parser triple pipeline
│   ├── insights_narration/      # Axe 2 — narration LLM des KPIs
│   └── analytics_qa/            # Axe 3 — Q&A analytique via QuerySpec
├── ui/                          # Couche Streamlit
│   ├── app.py                   # Orchestration sidebar + routing
│   ├── pages/                   # Vue Globale, Performance, Régions, Assistant Q&A
│   └── components/              # Voice widget réutilisable
├── eval/                        # Pipeline d'évaluation (méthodologie SCIAM)
│   ├── runner.py                # CLI — génère rapports JSON+Markdown, gate CI
│   ├── metrics.py               # WER/CER, exact-match, F1, anti-hallucination
│   ├── judges.py                # LLM-as-a-judge (pass/fail ciblé)
│   └── datasets/                # Scénarios ideal / realistic / adverse
├── data/
│   ├── generate_data.py         # Génère sales.csv (seed 42, saisonnalité réaliste)
│   └── sales.csv
└── tools/
    └── benchmark.py             # Benchmark CLI multi-modèles
```

---

## Évaluation

Le projet inclut un pipeline d'évaluation complet basé sur la méthodologie *"Mesurer l'immesuarable"* (SCIAM) :

```bash
# Évaluer toutes les briques
python app/eval/runner.py --brick all --model gemma3:4b --judge-model gemma3:4b

# Évaluer une brique seule
python app/eval/runner.py --brick intent

# Harness sans Ollama (mock LLM)
python app/eval/runner.py --brick narration --dry

# Tests déterministes unitaires
python app/eval/test_metrics.py
```

4 familles de métriques : déterministe (WER/CER, exact-match, F1 entités, anti-hallucination), sémantique, LLM-as-judge, humaine.
3 familles de scénarios : `ideal / realistic / adverse`, chacune avec son seuil d'acceptance.
Le runner retourne un code ≠ 0 si NO-GO (utilisable en CI).
