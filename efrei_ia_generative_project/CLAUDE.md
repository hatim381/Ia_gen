# CLAUDE.md — Contexte projet RetailVision BI

## But du projet

Atelier EFREI — Intégration de l'IA Générative dans la présentation de statistiques et dashboards.
**Deadline : 3 juillet 2026.**

Compétences évaluées :
- C5.1 : Identifier et argumenter les cas d'usage de l'IA générative
- C5.2 : Développer une solution basée sur un foundation model / LLM
- C5.3 : Évaluer la qualité des résultats générés

Minimum obligatoire imposé par le sujet : un système STT permettant la navigation vocale dans le dashboard (cas d'usage du VP sans usage des bras).

---

## Stack et environnement

| Composant | Technologie | Version |
|---|---|---|
| Dashboard | Streamlit | 1.49.1 |
| Graphiques | Plotly Express | 6.3.0 |
| Données | Pandas | 2.x |
| STT | faster-whisper (local) | 1.0+ |
| Modèle STT | Whisper `base` + int8 + VAD | — |
| Capture audio | streamlit-mic-recorder | 0.0.7+ |
| LLM | Ollama | 0.14.0 |
| Modèle LLM | configurable via `OLLAMA_MODEL` dans `intent_parser.py` | — |
| Modèle retenu (benchmark) | gemma3:4b | 3.3 GB |
| Modèles installés | gemma3:4b, mistral, llama3.1, qwen2.5:7b, phi3.5 | — |

---

## Ligne directrice adoptée

**Local-first absolu** — aucune donnée ne quitte la machine. Justification : données retail simulant des données RH/financières sensibles. Toute API externe (OpenAI, Anthropic, Web Speech API) est explicitement exclue.

**Single-page Streamlit avec routing manuel** — le multipage natif Streamlit ne permet pas de changer de page programmatiquement depuis un callback externe (le STT). Toute la navigation passe par `st.session_state.current_page` muté par le pipeline vocal, suivi d'un `st.rerun()`.

**Double pipeline d'interprétation** — les commandes simples (navigation, reset, clear_filter) passent par un fast-track Regex (0ms, 0 token). Seules les commandes complexes (filtres temporels, géographiques, catégoriels) sont envoyées au LLM. Réduit la latence perçue et la pression mémoire.

---

## Ce qui a été fait et pourquoi

### Données (`app/data/`)
- `generate_data.py` génère 18 275 lignes (730 jours × 5 régions × 5 catégories) avec seed fixe 42.
- Saisonnalité réaliste : ×1.4 décembre, ×1.15 juillet-août, ×0.8 janvier-février, ×0.75 weekend.
- CA de base différencié par région (Île-de-France = 35k/j, Est = 15k/j) et par catégorie.
- Colonnes : `date`, `region`, `categorie`, `transactions`, `ca`, `marge_pct` + deux dérivées calculées au chargement (`marge`, `panier_moyen`).

### Dashboard (`app/main.py` + `app/pages/`)
- `main.py` orchestre : init session_state → load data → sidebar → filtrage → routing page.
- 3 pages : Vue Globale (KPIs YoY + narration LLM), Performance (time series filtrable), Régions (treemap + comparatif).
- Les filtres (date, région, catégorie) sont stockés dans `st.session_state` et appliqués en amont avant le rendu de chaque page — le STT peut donc les muter sans toucher au code des pages.
- Vue Globale affiche toujours les données globales (non filtrées) et signale les filtres actifs via une bannière.

### STT (`app/stt/`)

**`transcriber.py`** : faster-whisper `base` + int8 + VAD.
- `vad_filter=True` : ne traite que les segments contenant de la parole, évite de passer 30s de mel-spectrogramme au modèle pour une commande de 3s.
- `beam_size=1` + `condition_on_previous_text=False` + `temperature=0` : décodage glouton optimisé pour des commandes courtes à vocabulaire contrôlé.
- Fichier WAV temporaire supprimé dans `finally`.

**`intent_parser.py`** : fast-track Regex puis fallback Ollama.
- 9 règles fast-track : navigation (3), reset, résumé/synthèse, aide, clear_filter région/catégorie/date.
- `target_page` absent du schéma LLM : la navigation est une décision Python, pas sémantique. Le laisser au LLM causait des erreurs de classification (mistral T5, phi3.5 T4 au benchmark).
- Validation des entités LLM avant écriture : `region` vérifiée dans `REGIONS`, dates wrappées dans `try/except`.
- Navigation context-aware après filtre : reste sur Régions si filtre région seul + page courante == Régions.
- `num_predict=150` : coupe la génération Ollama dès le JSON complet (~80-120 tokens).
- `timeout=30` via `ollama.Client` : évite le blocage indéfini si Ollama swappe.
- `format="json"` : grammar sampling, garantit un JSON valide même sur des modèles qui ignorent les instructions de format dans le prompt (Gemma3).
- `OLLAMA_MODEL` : constante en tête de fichier, change le modèle sans toucher au reste du code.

**`narrator.py`** : axe 2 (narration LLM). Reçoit un dict de KPIs, génère un paragraphe de synthèse exécutive via Ollama. Déclenché par bouton "🤖 Générer la synthèse" sur Vue Globale ou commande vocale "Résumé".

**`benchmark.py`** : script de benchmark comparatif. Teste N modèles sur les 7 scénarios de `analyse_ia.md`, mesure précision d'extraction et latence. Résultats accumulés dans `benchmark_results.json`. Prend les modèles en argument (`python3 benchmark.py mistral qwen2.5:7b`).

### Bugs corrigés
- **Plotly 6 / add_vline** : `x="2025-01-01"` (string) lève une `TypeError`. Corrigé par `x=pd.Timestamp(...).timestamp() * 1000` (ms Unix).
- **Image externe sidebar** : `st.image(url)` bloquait sans internet. Supprimée.
- **Gemma3 system prompt** : le modèle ignorait le system prompt et répondait en langage naturel. Résolu par `format="json"` + prompt dans le message user uniquement.
- **Ollama hang** : sans timeout, un appel LLM sur RAM saturée (swap plein) bloquait indéfiniment. Résolu par `ollama.Client(timeout=30)`.

---

## Décisions techniques et leurs raisons

| Décision | Raison |
|---|---|
| `faster-whisper` au lieu de `openai-whisper` | 4-8x plus rapide sur CPU via CTranslate2 + quantification int8. Même qualité de transcription. |
| `vad_filter=True` | Whisper traite toujours 30s de mel-spectrogramme en interne, même pour 3s de parole. VAD identifie les segments parlés et ne soumet que ceux-ci. Run 2 benchmark : 114ms vs 5295ms sans VAD sur même audio. |
| `beam_size=1` | Décodage glouton suffisant pour des commandes courtes à vocabulaire contrôlé. Le beam search améliore la WER sur du texte libre mais n'apporte rien ici. Gain ~15-30% de vitesse. |
| `format="json"` Ollama | Gemma3:4b ignore les instructions de format dans le prompt. `format="json"` (grammar sampling CTranslate2) garantit un JSON syntaxiquement valide en sortie, indépendamment du modèle. |
| Double pipeline Regex/LLM | Les commandes de navigation sont détectables en 0ms par regex. Envoyer "Accueil" à un LLM est un gaspillage de 10s et de RAM. Le LLM n'est sollicité que pour l'extraction d'entités complexes. |
| `target_page` retiré du schéma LLM | La navigation est une décision applicative Python, pas sémantique. Laisser le LLM la décider causait des erreurs de classification (mistral T5 : "Région Nord" → navigate, phi3.5 T4 : "Affiche les ventes" → navigate). |
| `num_predict=150` | Le JSON attendu fait ~80-120 tokens. Sans limite, certains modèles (phi3.5 T7) insèrent du texte en langage naturel dans les champs JSON. 150 coupe proprement après le JSON fermant. |
| `timeout=30` Ollama | Sans timeout, un Ollama sous pression mémoire (swap saturé) peut bloquer indéfiniment le thread Streamlit. 30s est suffisant pour les modèles 4-7B sur cette machine hors swap. |
| `gemma3:4b` retenu (benchmark) | Benchmark 5 modèles sur 7 scénarios : seuls gemma3:4b et qwen2.5:7b atteignent 7/7. gemma3:4b est 2x plus rapide à chaud (~7-10s vs ~15s). `OLLAMA_MODEL` est une constante modifiable en ligne 13 d'`intent_parser.py`. |
| Validation entités LLM | Un LLM peut retourner `region: "Normandie"` (hors liste) ou une date invalide. Sans validation, le filtre s'applique silencieusement et le dashboard affiche zéro lignes sans message d'erreur. |
| Navigation context-aware | Rester sur Régions après un filtre "Région Nord" si l'utilisateur y est déjà. La page Régions est conçue pour les comparatifs régionaux filtrés — la forcer à quitter vers Performance serait contre-intuitif. |
| Narration LLM (axe 2) | Même infrastructure Ollama, prompt ciblé sur les KPIs calculés côté Python. Évite d'envoyer des données brutes au modèle. Déclenché on-demand (bouton ou commande vocale "Résumé") pour ne pas bloquer le rendu. |
