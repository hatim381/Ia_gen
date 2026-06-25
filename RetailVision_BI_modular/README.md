# RetailVision BI

Dashboard de ventes augmenté par l'IA générative, développé dans le cadre de l'atelier EFREI — Intégration de l'IA générative dans la présentation de statistiques.

Le projet explore trois axes d'usage de l'IA générative appliqués à la Business Intelligence retail. Son axe central est la **navigation vocale** : un utilisateur peut piloter entièrement le dashboard par la voix, sans souris ni clavier, grâce à un pipeline STT entièrement local.

---

## Fonctionnalités IA

### Axe 1 — Navigation vocale par STT (implémenté)

L'utilisateur parle dans son microphone. Sa voix est transcrite localement par **Whisper**, puis son intention est interprétée par un **LLM local via Ollama**. Le dashboard se met à jour instantanément.

```
Microphone → Whisper (local) → Texte → Regex / LLM → Dashboard
```

Exemples de commandes :
| Commande | Action |
|---|---|
| *"Accueil"* | Navigation vers la vue globale |
| *"Performance"* | Navigation vers la page performance |
| *"Région Nord"* | Filtre sur la région Nord |
| *"Affiche les ventes de janvier 2025"* | Filtre temporel automatique |
| *"Sport entre mars et juin"* | Filtre catégorie + période |
| *"Reset"* | Réinitialisation de tous les filtres |

### Axe 2 — Narration automatique des KPIs (prévu)

Un LLM lit les métriques clés du dashboard et génère automatiquement un résumé en langage naturel — résumé exécutif pour les décideurs, ou explication simplifiée pour les utilisateurs non-initiés.

### Axe 3 — Chatbot Q&A analytique (prévu)

L'utilisateur pose des questions en langage naturel sur les données. Le LLM génère la requête Pandas correspondante, l'exécute et retourne la réponse directement dans l'interface.

---

## Architecture IA

```
┌─────────────────────────────────────────────────────────────────┐
│                        PIPELINE STT                             │
│                                                                 │
│  Micro  →  Whisper base (local, CPU)  →  Texte transcrit        │
│                                               │                 │
│                                    ┌──────────▼───────────┐     │
│                                    │   Fast-Track (Regex) │     │
│                                    │   commandes simples  │     │
│                                    │   0ms — 0 token      │     │
│                                    └──────────┬───────────┘     │
│                                               │ non reconnu     │
│                                    ┌──────────▼───────────┐     │
│                                    │   LLM (Ollama local) │     │
│                                    │   extraction JSON    │     │
│                                    │   filtres complexes  │     │
│                                    └──────────┬───────────┘     │
│                                               │                 │
│                              mutation st.session_state          │
│                                               │                 │
│                                    ┌──────────▼───────────┐     │
│                                    │   Dashboard Streamlit │     │
│                                    │   re-render          │     │
│                                    └──────────────────────┘     │
└─────────────────────────────────────────────────────────────────┘
```

**Choix local-first** : aucune donnée ne quitte la machine. Whisper et le LLM tournent en local via Ollama — contrainte de confidentialité sur des données de type financier/RH.

---

## Stack technique

| Composant | Technologie |
|---|---|
| Interface | Streamlit |
| Graphiques | Plotly Express |
| STT | OpenAI Whisper `base` (local) |
| LLM | Ollama — Mistral 7B / Llama 3.1 8B |
| Capture audio | streamlit-mic-recorder |
| Données | Pandas + CSV (18 275 lignes générées) |

---

## Installation

**Prérequis :** Python 3.10+, [Ollama](https://ollama.com) installé.

```bash
# Dépendances Python
pip install -r requirements.txt

# Modèles IA locaux
ollama pull mistral      # LLM d'interprétation des commandes vocales
```

Whisper télécharge automatiquement le modèle `base` (~139 Mo) au premier lancement.

---

## Lancement

```bash
streamlit run app/main.py
```

L'application est accessible sur `http://localhost:8501`.

---

## Structure du projet

```
├── app/
│   ├── main.py              # Point d'entrée et orchestration
│   ├── pages/               # Vue Globale, Performance, Régions
│   ├── stt/                 # Pipeline Whisper + interprétation LLM
│   └── data/                # Données retail fictives (2024–2025)
├── docs/
│   └── analyse_ia.md        # Analyse des choix IA et évaluation (C5.1/C5.2/C5.3)
├── requirements.txt
└── CLAUDE.md                # Contexte technique du projet
```
