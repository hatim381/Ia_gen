# Audit strict — RetailVision BI

**Repository:** `bill-padonou/efrei_ia_generative_project` (commit `fe1b54b`, "First Commit")
**Spécification de référence:** `Atelier IA EFREI.pdf` (présente dans le repo, 3 pages)
**Méthode:** lecture intégrale du code source cloné. Aucune fonctionnalité n'est créditée sans preuve dans le code. Toute affirmation importante cite un fichier + une fonction/ligne, ou porte la mention « NO EVIDENCE FOUND IN CODEBASE ».
**Date de l'audit:** 25 juin 2026

---

## # Executive Summary

RetailVision BI est un dashboard de Business Intelligence retail écrit en **Streamlit/Python**, augmenté d'un pipeline de navigation vocale **entièrement local** (faster-whisper + Ollama). Le projet est réel, exécutable et cohérent dans son intention. Le livrable obligatoire imposé par le sujet — *un système STT local permettant à un utilisateur sans usage des bras de naviguer dans le dashboard par la voix* — **existe réellement dans le code** (`app/stt/listener.py`, `app/stt/intent_parser.py`).

Deux axes d'IA générative sur trois sont réellement implémentés (navigation vocale + narration LLM des KPIs). Le troisième (chatbot Q&A text-to-query) est uniquement décrit, jamais codé.

Le problème le plus grave n'est pas fonctionnel mais **d'intégrité d'évaluation (C5.3)** : le rapport `docs/analyse_ia.md` affirme que `gemma3:4b` obtient **7/7** scénarios à **~7,6 s** et qu'il est « retenu » — mais le fichier de résultats réellement commité (`app/stt/benchmark_results.json`) montre que **gemma3:4b obtient 6/7 (3/4 LLM) à ~15,4 s**, qu'**aucun modèle n'atteint 7/7**, et que le modèle effectivement câblé en production (`OLLAMA_MODEL = "mistral"`) y obtient **4/7 (1/4 LLM)** avec des appels qui saturent le timeout de 30 s. Les chiffres documentés ne sont pas soutenus par les données livrées.

**Verdict synthétique : le minimum obligatoire du sujet est satisfait. Le projet passe, avec réserves sérieuses sur l'honnêteté de l'évaluation et sur la configuration livrée.**

---

## # Repository Architecture Map

```
efrei_ia_generative_project/
├── app/
│   ├── main.py                 # Orchestration : session_state → data → sidebar → filtres → routing
│   ├── data/
│   │   ├── __init__.py         # load_sales() (cache), REGIONS, CATEGORIES
│   │   ├── generate_data.py    # Génération CSV synthétique (seed 42)
│   │   └── sales.csv           # 18 275 lignes (18 276 avec header)
│   ├── pages/
│   │   ├── vue_globale.py       # KPIs YoY + narration LLM (axe 2)
│   │   ├── performance.py       # Séries temporelles filtrées
│   │   └── regions.py           # Treemap + comparatif régional
│   └── stt/
│       ├── listener.py          # ★ Capture micro live (sounddevice) + VAD + Whisper  [PATH RÉEL]
│       ├── transcriber.py       # transcribe_audio() — DÉFINI MAIS JAMAIS APPELÉ (dead code)
│       ├── intent_parser.py     # Triple pipeline Regex → Fuzzy → Ollama
│       ├── narrator.py          # Narration exécutive via Ollama (axe 2)
│       ├── benchmark.py          # Script de benchmark des modèles LLM
│       └── benchmark_results.json # Résultats réels commités (contredisent le rapport)
├── docs/analyse_ia.md           # Rapport C5.1/C5.2/C5.3
├── CLAUDE.md / README.md        # Documentation
├── requirements.txt
├── .streamlit/config.toml
└── Atelier IA EFREI.pdf         # Sujet (spécification)
```

**Flux d'exécution réel (vérifié)** : `main.py:main()` → `init_session_state()` → `data.load_sales()` → `render_sidebar()` → `apply_filters()` → routing vers `pages/*.render()`. La voix est branchée dans `render_sidebar()` via `render_voice_component()`, qui instancie `MicListener` (`app/stt/listener.py`) et appelle `parse_intent()` puis `apply_intent()` (`app/stt/intent_parser.py`).

Pas de frontend séparé, pas de backend API, pas de base de données, pas de Docker/infra. L'« architecture » est un monolithe Streamlit single-page à routing manuel via `st.session_state.current_page`. **Docker / CI / déploiement : NO EVIDENCE FOUND IN CODEBASE.**

---

## # Technology Stack

| Composant | Technologie | Preuve |
|---|---|---|
| Interface | Streamlit | `app/main.py:8` `import streamlit as st` |
| Graphiques | Plotly Express | `app/pages/*.py` `import plotly.express as px` |
| Données | Pandas + CSV (18 275 lignes) | `app/data/__init__.py:load_sales()`, `sales.csv` |
| STT | faster-whisper `base`, int8, CPU | `app/stt/listener.py:62` `WhisperModel("base", device="cpu", compute_type="int8")` |
| VAD capture | webrtcvad (agressivité 2) | `app/stt/listener.py:67` `webrtcvad.Vad(2)` |
| Capture micro | **sounddevice** (RawInputStream) | `app/stt/listener.py:107,119` |
| LLM | Ollama (client local) | `app/stt/intent_parser.py:124` `ollama.Client(timeout=30).chat(...)` |
| Modèle LLM **en production** | **`mistral`** | `app/stt/intent_parser.py:13` `OLLAMA_MODEL = "mistral"` |
| Fuzzy matching | rapidfuzz | `app/stt/intent_parser.py:` `from rapidfuzz import fuzz, process` |
| Polling UI | streamlit-autorefresh | `app/main.py:render_voice_component()` |

**Incohérence stack #1 :** README.md (l.80) et CLAUDE.md (l.26) déclarent la capture audio via **`streamlit-mic-recorder`**. Ce paquet n'est **ni dans `requirements.txt` ni importé nulle part** (`grep` : seules deux mentions, toutes deux dans la doc). La capture réelle se fait côté serveur via `sounddevice.RawInputStream`. → la doc décrit une techno qui n'est pas celle du code.

**Incohérence stack #2 :** CLAUDE.md (l.25) annonce le STT via `faster-whisper` mais aussi un module `transcriber.py` utilisant l'API `transcribe_audio(bytes)` ; ce chemin n'est jamais exécuté (voir section STT).

---

## # AI Features Actually Implemented

### Axe 1 — Navigation vocale par STT ✅ (réellement implémenté)
- Capture micro continue en thread background : `app/stt/listener.py:MicListener._listen_loop()` (sounddevice RawInputStream 16 kHz mono int16, segmentation par VAD webrtcvad).
- Transcription locale : `app/stt/listener.py:MicListener._transcribe()` → `_get_whisper_model()` (faster-whisper `base` int8 CPU).
- Interprétation d'intention : `app/stt/intent_parser.py:parse_intent()` — triple pipeline Regex (`_fast_track`) → Fuzzy (`_fuzzy_track`) → LLM (`_ollama_parse`).
- Application sur l'état : `app/stt/intent_parser.py:apply_intent()` mute `st.session_state` (page courante, filtres date/région/catégorie, reset, clear_filter, narrate, help).
- Branchement UI : `app/main.py:render_voice_component()` (boutons Démarrer/Arrêter, dépile la `transcript_queue`, déclenche `parse_intent`/`apply_intent`).

### Axe 2 — Narration automatique des KPIs ✅ (réellement implémenté)
- `app/stt/narrator.py:generate_narrative(kpis)` envoie les KPIs calculés côté Python à Ollama et retourne un paragraphe.
- Câblé dans l'UI : `app/pages/vue_globale.py:_render_narrative()` — bouton « 🤖 Générer la synthèse » **et** déclenchement vocal via `st.session_state.stt_narrate` (commande « Résumé »/« Synthèse », règle fast-track `intent_parser.py` action `narrate`).
- **Note :** README.md classe cet axe comme « (prévu) » alors qu'il est bel et bien codé et branché. Ici la doc **sous-estime** le code — l'inverse du reste de l'audit.

### Génération de données (support, non-IA)
- `app/data/generate_data.py` : 18 275 lignes synthétiques, seed 42, saisonnalité paramétrée. Déterministe et reproductible. Ce n'est pas de l'IA générative (génération procédurale numpy).

---

## # AI Features Claimed but Not Implemented

| Fonctionnalité revendiquée | Où revendiquée | État réel |
|---|---|---|
| **Axe 3 — Chatbot Q&A analytique (text-to-query Pandas)** | README.md, `docs/analyse_ia.md` §C5.1 Axe 3 | **NON IMPLÉMENTÉ.** Aucune fonction de génération/exécution de requête Pandas. `grep` : aucun `eval`, aucun sandbox, aucun module Q&A. **NO EVIDENCE FOUND IN CODEBASE.** |
| **TTS / loop voix-out (narration lue à voix haute)** | `docs/analyse_ia.md` §C5.1 (« convergence ») | NON IMPLÉMENTÉ. Aucune lib TTS, aucun appel synthèse vocale. **NO EVIDENCE FOUND IN CODEBASE.** |
| **Capture audio via `streamlit-mic-recorder`** | README.md, CLAUDE.md (tableau stack) | NON UTILISÉ. Paquet absent de `requirements.txt` et non importé. Capture réelle via `sounddevice`. |
| **Modèle LLM retenu = `gemma3:4b`** | CLAUDE.md, `docs/analyse_ia.md` §C5.3 | Le code livré utilise `OLLAMA_MODEL = "mistral"` (`intent_parser.py:13`). Le modèle « retenu » documenté n'est pas celui exécuté. |
| **`transcriber.py` (chemin de transcription)** | CLAUDE.md §STT décrit `transcriber.py` | DEAD CODE. `transcribe_audio()` n'est appelé par aucun module (`grep` confirme). Le chemin vivant est `listener.py`. |

---

## # Speech-to-Text Analysis (CRITICAL SECTION)

**Le STT existe et est local — c'est confirmé.** Détails et limites :

**1. Le STT est-il réellement implémenté ?** ✅ Oui.
`app/stt/listener.py` capture le micro (`sd.RawInputStream`, l.119), segmente par VAD (`webrtcvad.Vad(2)`, l.67 ; clôture d'un segment après `SILENCE_FRAMES = 20` ≈ 600 ms de silence), et transcrit via faster-whisper (`_get_whisper_model()` → `WhisperModel("base", device="cpu", compute_type="int8")`, l.62). Décodage optimisé pour commandes courtes : `language="fr"`, `vad_filter=True`, `beam_size=1`, `condition_on_previous_text=False`, `temperature=0` (l.77-83).

**2. Le STT est-il local ?** ✅ Oui, sans ambiguïté.
faster-whisper télécharge et exécute le modèle `base` en local CPU. Aucune API externe d'audio. La confidentialité revendiquée (« aucune donnée ne quitte la machine ») est **vraie dans le code** : aucun appel réseau sortant pour l'audio ou le texte hormis Ollama (`localhost`). Conforme à l'exigence « usage au moins local » du sujet.

**3. La navigation vocale est-elle fonctionnelle ?** ⚠️ Partiellement.
Une fois l'écoute démarrée, la boucle VAD pousse les transcriptions dans `transcript_queue`, dépilée toutes les 500 ms par `st_autorefresh` (`render_voice_component`), puis `parse_intent`/`apply_intent` changent de page et appliquent les filtres. Le mécanisme est complet et cohérent. **MAIS** : pour **démarrer** (et arrêter) l'écoute, il faut **cliquer** le bouton « 🎤 Démarrer l'écoute » (`app/main.py:render_voice_component`). Il n'existe ni wake-word, ni démarrage automatique, ni activation au clavier seul. → Le point d'entrée n'est pas « mains libres ».

**4. Architecture de capture — limite majeure de déploiement.** ⚠️
La capture utilise `sounddevice.RawInputStream`, qui lit le micro **de la machine qui exécute le serveur Streamlit**, pas celui du navigateur client. En local mono-utilisateur (le cas du VP sur son poste), cela fonctionne. En déploiement web/distant/headless (pas de périphérique audio serveur), **la voix ne capte rien**. Le `.streamlit/config.toml` est d'ailleurs en `headless = true`. Donc les revendications B2C « kiosques / mobile / web » de `analyse_ia.md` ne sont pas réalisables avec cette architecture sans réécriture (il faudrait un composant navigateur type WebRTC / `streamlit-mic-recorder` — précisément le paquet annoncé mais non utilisé).

**5. Pipeline d'interprétation — solide.** ✅
`intent_parser.py` valide les entités LLM avant écriture : `region` doit appartenir à `REGIONS`, `categorie` à `CATEGORIES`, dates wrappées en `try/except`. `format="json"` force un JSON valide. Timeout 30 s et `num_predict=150` bornent les dérives. Le fast-track regex (9 règles) et le fuzzy (`rapidfuzz`, seuil 80) évitent d'appeler le LLM pour la navigation simple.

**6. Qualité STT mesurée ?** ❌
Le WER est **défini** comme métrique cible (<10 %) dans `analyse_ia.md` mais **jamais mesuré** : aucun jeu audio de test, aucun calcul de WER dans `benchmark.py` (qui ne teste que l'extraction LLM à partir de texte déjà transcrit). La brique STT n'est donc pas évaluée empiriquement.

**Conclusion STT :** présent, local, fonctionnel une fois activé — mais activation non mains-libres, capture côté serveur (bloque tout déploiement distant), et qualité de transcription non mesurée.

---

## # Accessibility Analysis

Le sujet est explicite : le VP a **perdu l'usage de ses bras** et doit naviguer **par la voix**. C'est le cœur de l'évaluation accessibilité.

- ✅ Une fois l'écoute lancée, navigation et filtrage se font intégralement à la voix (changement de page, filtres date/région/catégorie, reset, synthèse). C'est réellement utilisable sans souris pendant la session.
- ⚠️ **Faille pour le persona exact** : démarrer et arrêter l'écoute exige un **clic** (`render_voice_component`). Un utilisateur sans usage des bras ne peut pas initier la session seul — il dépend d'un tiers ou d'un dispositif d'entrée alternatif non fourni. Aucun wake-word, aucun auto-start.
- ❌ Aucune prise en charge clavier-only documentée, aucun attribut ARIA/lecteur d'écran, aucune mention RGAA/WCAG **dans le code** (la conformité WCAG 2.1 AA est citée dans `analyse_ia.md` mais c'est une affirmation, pas une implémentation : **NO EVIDENCE FOUND IN CODEBASE**).
- ⚠️ Les KPI cards sont rendues en HTML brut via `unsafe_allow_html=True` (`vue_globale.py:_kpi_card`), hors du modèle accessible natif de Streamlit — neutre à négatif pour les lecteurs d'écran.

**Bilan accessibilité :** l'intention est juste et la navigation vocale réelle, mais le « voice-only » bute sur l'activation manuelle — précisément l'étape qu'un utilisateur sans bras ne peut pas franchir seul.

---

## # Security / Performance / Scalability

**Sécurité** — globalement faible surface de risque (local-first) :
- ✅ Pas de secret, pas de clé API, pas d'appel externe (hors `localhost` Ollama). Le local-first est réel.
- ✅ Validation d'entités LLM contre allowlist avant mutation d'état (`intent_parser.apply_intent`) → empêche l'injection de filtres arbitraires.
- ⚠️ `unsafe_allow_html=True` avec interpolation f-string de la sortie LLM (`vue_globale.py:_render_narrative` injecte `st.session_state.narrative_text` dans le HTML). Risque XSS théorique faible (mono-utilisateur, sortie LLM locale) mais réel : une narration contenant `<script>` serait rendue. Pas d'échappement.
- ✅ Le danger classique du text-to-query (`eval` Pandas) **n'existe pas** puisque l'axe 3 n'est pas implémenté.

**Performance** — c'est le point faible mesuré :
- ❌ Latence LLM réelle (`benchmark_results.json`) : **10–30 s** par commande complexe, beaucoup d'appels saturant le timeout 30 s. La cible affichée (`analyse_ia.md`) est « <5 s commandes complexes ». **Cible non atteinte.**
- ✅ Fast-track regex/fuzzy : <1 ms pour la navigation (confirmé par les latences T1-T3 du JSON, ~0,01–0,3 ms).
- ✅ `@st.cache_resource` / `@st.cache_data` pour Whisper et le CSV (chargement unique).

**Scalabilité** :
- ⚠️ Modèle mono-utilisateur par conception : `MicListener` singleton process-wide (`@st.cache_resource`), modèle Whisper en global module-level avec lock. Plusieurs sessions simultanées partageraient le même micro serveur → collision. Acceptable pour un outil de poste local, inadapté à un service multi-tenant.
- ⚠️ Capture côté serveur (cf. STT §4) interdit le scaling web standard.

---

## # Compliance Matrix

| Requirement (source: Atelier IA EFREI.pdf) | Expected | Implemented | Evidence | Status |
|---|---|---|---|---|
| Identifier 3 axes d'IA générative (B2B/B2C) | 3 axes argumentés + convergence | 3 axes décrits, B2B/B2C, tableau de convergence | `docs/analyse_ia.md` §C5.1 | ✅ |
| Axes implémentés | ≥1 (le STT) obligatoire | 2/3 codés (STT nav + narration) ; Q&A absent | `app/stt/*`, `pages/vue_globale.py:_render_narrative` | ✅ (minimum dépassé) |
| **STT intégré à l'application** | Obligatoire | Oui, capture+VAD+Whisper+intent | `app/stt/listener.py`, `intent_parser.py` | ✅ |
| **STT local** | « au moins local » | faster-whisper base int8 CPU, 0 API audio | `listener.py:62` | ✅ |
| **Navigation dashboard par la voix** | Obligatoire (VP sans bras) | Oui une fois l'écoute lancée | `apply_intent()`, `render_voice_component()` | ⚠️ (activation au clic) |
| Argumenter Local vs API | C5.2 | Tableau comparatif détaillé | `docs/analyse_ia.md` §C5.2 | ✅ |
| Choix de modèles argumenté | C5.1/C5.2 | Argumenté (STT base, LLM) | `analyse_ia.md`, `CLAUDE.md` | ⚠️ (modèle « retenu » ≠ modèle en prod) |
| Scénarios de test | C5.3 | 7 scénarios + script benchmark | `benchmark.py:SCENARIOS`, `analyse_ia.md` §C5.3 | ✅ |
| Métriques adaptées | C5.3 (WER, précision, latence) | Définies ; WER jamais mesuré | `analyse_ia.md` §C5.3 | ⚠️ |
| Résultats analysés honnêtement | C5.3 | Rapport contredit les données commitées | `analyse_ia.md` vs `benchmark_results.json` | ❌ |
| Accessibilité universelle (persona sans bras) | C5.2 | Voix OK ; démarrage non mains-libres | `render_voice_component()` | ⚠️ |
| Livrable : PDF/présentation + rapport écrit | À remettre | Rapport = `analyse_ia.md` ; pas de PDF/slides commités | `docs/` | ⚠️ |
| Q&A analytique (axe 3) | Optionnel (décrit) | Non codé | — | ❌ |
| TTS / loop voix-out | Optionnel (décrit) | Non codé | — | ❌ |
| Docker / déploiement / CI | Non exigé | Absent | — | ❌ (hors exigence) |

---

## # C5.1 — Pertinence des cas d'usage

**Score : 8,5 / 10**

**Justification :** `docs/analyse_ia.md` traite C5.1 avec sérieux : trois axes clairement définis (STT, narration, Q&A), grille de pertinence B2B/B2C par axe, tableau de convergence (infra Ollama partagée, l'axe 1 comme interface d'entrée des axes 2/3), et — point souvent négligé — une section « cas moins pertinents » justifiée (génération d'images hors-sujet pour de la BI, TTS comme techno de restitution non générative, RAG catalogue hors périmètre). Cela répond précisément à la consigne du sujet (« les cas pertinents *et les moins pertinents, et pourquoi* »).

**Preuves :** `docs/analyse_ia.md` §C5.1 (axes 1-3, tableaux B2B/B2C, tableau de convergence, « Cas moins pertinents »).

**Éléments manquants :** la « collaboration des parties prenantes » / « concertation IT » (citée dans C5.1/C5.2 du sujet) reste superficielle — pas de trace de questions posées aux parties prenantes ni d'arbitrage IT documenté (le sujet invite pourtant explicitement à « poser des questions et noter les réponses »). Convergence bien posée mais non démontrée par du code pour les axes 2/3.

---

## # C5.2 — Choix techniques d'implémentation

**Score : 7 / 10**

**Justification :** l'ingénierie est réelle et réfléchie. Choix local-first argumenté (confidentialité, coût, RGPD, offline) avec tableau Local vs API. STT optimisé (faster-whisper int8, VAD, greedy decoding, prompt de biais vocabulaire). Triple pipeline Regex→Fuzzy→LLM pour minimiser latence et charge. Validation des entités LLM avant mutation d'état. Narration (axe 2) réutilisant la même infra Ollama. CLAUDE.md documente honnêtement plusieurs bugs corrigés (Plotly add_vline, hang Ollama, system prompt Gemma).

**Preuves :** `app/stt/listener.py` (capture+VAD+Whisper), `app/stt/intent_parser.py` (`_fast_track`, `_fuzzy_track`, `_ollama_parse` avec `format="json"`, timeout, validation), `app/stt/narrator.py`, `docs/analyse_ia.md` §C5.2.

**Éléments manquants / défauts :**
- **Le modèle livré (`OLLAMA_MODEL = "mistral"`, `intent_parser.py:13`) est le plus mauvais des cinq testés** dans `benchmark_results.json` (4/7, 1/4 LLM, appels à 30 s). La doc dit « retenu : gemma3:4b » — le code et la doc divergent. C'est un défaut de configuration livrée, pas seulement de doc.
- **Capture côté serveur** (`sounddevice`) : bloque tout déploiement distant et contredit les revendications B2C web/mobile/kiosque.
- **Dead code** : `transcriber.py:transcribe_audio()` jamais appelé ; duplication du `WHISPER_PROMPT` entre `transcriber.py` et `listener.py`.
- **Dérive de dépendances** : `streamlit-mic-recorder` annoncé mais ni installé ni utilisé.
- Aucune gestion de l'accessibilité de démarrage (cf. persona).

---

## # C5.3 — Méthodologie d'évaluation

**Score : 5,5 / 10**

**Justification :** la *méthode* est correctement posée — 7 scénarios reproductibles (`benchmark.py:SCENARIOS`), trois métriques définies avec cibles (WER <10 %, précision extraction >85 %, latence <5 s / <200 ms), script de benchmark réel qui rejoue le pipeline de production (`_call_llm` réimporte `intent_parser._ollama_parse`) et persiste les résultats. C'est au-dessus de la moyenne pour un exercice de 4 jours.

**MAIS la restitution des résultats n'est pas fidèle aux données livrées — défaut grave :**

| Affirmation `analyse_ia.md` | Donnée réelle `benchmark_results.json` |
|---|---|
| gemma3:4b → **7/7**, **4/4 LLM**, **~7,6 s** warm, « Retenu » | gemma3:4b → **6/7**, **3/4 LLM**, **15 418,9 ms** moy. ; **T4 échoue** (`action=unknown`) |
| mistral → 6/7 (T5 échoue) | mistral → **4/7**, **1/4 LLM** ; T4, T5, T6 échouent (≈30 s, timeout) |
| qwen2.5:7b → 7/7 | qwen2.5:7b → **4/7**, 1/4 LLM |
| phi3.5 → 6/7 | phi3.5 → **5/7**, 2/4 LLM |
| llama3.1 → 5/7 | llama3.1 → **4/7**, 1/4 LLM |
| « Score actuel : 7/7 scénarios corrects » | **Aucun modèle n'atteint 7/7** dans les données commitées |
| Cible latence <5 s tenue | Latences LLM réelles 10–30 s, multiples timeouts |

**Preuves :** comparer `docs/analyse_ia.md` §C5.3 (tableau « benchmark exécuté le 2026-06-24 ») à `app/stt/benchmark_results.json` (mêmes modèles, mêmes scénarios, chiffres opposés ; timestamps 2026-06-24T18:xx).

**Éléments manquants :** WER jamais calculé (pas de jeu audio, `benchmark.py` ne teste que l'extraction texte→JSON, pas la transcription). Latence T4 ~100 s qualifiée de « cold start » dans la doc mais le JSON montre 30 216 ms (timeout), pas un cold start dépilé. Pas d'analyse de variance ni de répétitions.

> Le score n'est pas plus bas car la *charpente* méthodologique (scénarios, métriques, script reproductible, résultats commités) est réellement présente — c'est sa restitution qui est trompeuse, et l'honnêteté est explicitement un attendu de C5.3.

---

## # Critical Findings

1. **[Intégrité — majeur]** Le rapport d'évaluation (`analyse_ia.md`) revendique des scores (gemma3:4b 7/7 @ ~7,6 s) que le fichier de résultats commité (`benchmark_results.json`) contredit directement (6/7 @ 15,4 s, aucun modèle 7/7). C5.3 affirme une performance non soutenue par les données livrées.
2. **[Config livrée — majeur]** Le modèle réellement câblé est `mistral` (`intent_parser.py:13`), classé **dernier** dans le propre benchmark du projet (4/7, 1/4 LLM, timeouts 30 s) — alors que la doc annonce `gemma3:4b` « retenu ». L'app livrée tournerait sur la pire configuration mesurée.
3. **[Accessibilité — significatif]** « Voice-only » non tenu à l'activation : démarrer/arrêter l'écoute exige un **clic** (`render_voice_component`), infranchissable seul pour l'utilisateur sans usage des bras, qui est le persona central du sujet.
4. **[Déploiement — significatif]** Capture micro **côté serveur** (`sounddevice.RawInputStream`) : fonctionne en local mono-poste mais rend impossible tout déploiement web/distant/headless, contredisant les revendications B2C (kiosque, mobile, web).
5. **[Périmètre]** 2 axes IA sur 3 implémentés ; l'axe 3 (Q&A text-to-query) est uniquement décrit — **NO EVIDENCE FOUND IN CODEBASE**. (Le sujet n'exigeait qu'un axe implémenté, donc non-bloquant.)
6. **[Qualité STT non mesurée]** WER défini comme métrique mais jamais calculé ; la brique de transcription n'est pas évaluée empiriquement.
7. **[Dette/cohérence]** `transcriber.py` est du dead code ; `streamlit-mic-recorder` documenté mais absent du code ; duplication du prompt Whisper.
8. **[Livrable formel]** Le sujet demande « un PDF / une présentation » + rapport écrit. Le rapport existe (`analyse_ia.md`) mais aucun PDF/slides de rendu n'est commité (seul le sujet est présent).

---

## # Final Verdict (/20)

| Compétence | Pondération | Score | Pondéré |
|---|---|---|---|
| C5.1 — Pertinence des cas d'usage | /6 | 8,5/10 | 5,1 |
| C5.2 — Choix techniques | /7 | 7/10 | 4,9 |
| C5.3 — Méthodologie d'évaluation | /7 | 5,5/10 | 3,85 |
| **Total** | **/20** | | **≈ 13,5 / 20** |

**Note finale : 13,5 / 20 — Mention « passable, avec réserves sérieuses ».**

Le socle obligatoire (STT local + navigation vocale) est réellement livré et fonctionne ; C5.1 est solide ; l'ingénierie de C5.2 est réelle. Les retenues portent sur : la non-fidélité du rapport d'évaluation aux données commitées (C5.3), le modèle de production incohérent avec les conclusions du benchmark, l'activation non mains-libres pour le persona cible, et la capture serveur qui plafonne le déploiement.

---

## # Question finale — Le projet satisfait-il les exigences de l'atelier EFREI ?

**Réponse, strictement sur preuves : OUI pour le minimum imposé, avec réserves.**

Le sujet (`Atelier IA EFREI.pdf`, p.2) exige *a minima* **un seul** axe implémenté : « un système de STT intégré à l'application, pour un usage au moins local […] permettre de naviguer dans le dashboard par la voix ». Ce livrable obligatoire **existe réellement dans le code** (`app/stt/listener.py` + `intent_parser.py` + branchement `main.py`), est **local** (faster-whisper CPU, zéro API audio) et permet **la navigation vocale** (changement de page + filtres). Les trois compétences C5.1/C5.2/C5.3 sont chacune traitées dans `docs/analyse_ia.md`.

**Donc le projet passe le seuil obligatoire du sujet.** Mais il échoue à plusieurs attendus qualitatifs vérifiables :
- C5.3 n'est **pas honnête** : les résultats annoncés contredisent les données livrées.
- Le persona central (VP sans usage des bras) ne peut **pas démarrer** la session seul (clic obligatoire).
- L'application livrée pointe vers le modèle LLM le plus faible de son propre benchmark.

Si la grille exigeait — comme le formule la consigne d'audit — **trois axes réellement implémentés**, alors le projet **échouerait sur ce critère précis** : seuls deux le sont. Mais selon la spécification primaire (le PDF), qui n'impose qu'un axe, **le projet est recevable**.
