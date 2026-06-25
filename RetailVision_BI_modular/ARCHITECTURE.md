# Architecture — RetailVision BI (modulaire, faiblement couplée)

## Principe
Trois couches, dépendances **dans un seul sens** : `ui → features → core`.
`core` et `features` n'importent **jamais** Streamlit → ils sont testables sans UI ni serveur.
Chaque axe IA est un module `features/` isolé exposant une **façade `service`** ; l'UI ne parle qu'aux façades.

```
app/
├── core/                      # infra partagée, ZÉRO Streamlit
│   ├── config.py              # constantes + modèles + seuils (source unique)
│   ├── llm/client.py          # client Ollama UNIQUE (avant : dupliqué 3×)
│   ├── llm/prompts.py         # tous les prompts
│   ├── stt/engine.py          # transcription Whisper (pure)
│   ├── stt/microphone.py      # capture + VAD (séparée du moteur)
│   ├── data/repository.py     # chargement + filtres + KPIs (source de vérité)
│   └── domain/{models,state}.py  # Intent, KPISet, QuerySpec, Effect, AppState
├── features/                  # les 3 axes, dépendent de core uniquement
│   ├── voice_navigation/      # AXE 1 : intent_parser + command_router + service
│   ├── insights_narration/    # AXE 2 : narrator + service
│   └── analytics_qa/          # AXE 3 : generator + query_engine + service
├── ui/                        # Streamlit : app + state adapter + components + pages
├── eval/                      # pipeline d'évaluation (4 briques) — méthodo SCIAM
├── tools/benchmark.py         # benchmark LLM à lancer sur le PC
├── tests/                     # tests unitaires (logique pure)
└── data/                      # generate_data.py + sales.csv
```

## Découplages clés (vs l'ancien code)
| Avant (couplé) | Après (découplé) |
|---|---|
| `intent_parser`/`narrator` importaient Streamlit et mutaient `st.session_state` | features pures ; `command_router` renvoie un `AppState`, l'UI seule écrit l'état |
| logique Ollama dupliquée (intent, narrator, benchmark) | un seul `core/llm/client.py` |
| constantes éparpillées (REGIONS, OLLAMA_MODEL, prompt Whisper) | `core/config.py` unique |
| capture micro + Whisper mélangés dans `listener.py` | `core/stt/microphone.py` (capture) ⟂ `core/stt/engine.py` (Whisper) |
| 2 axes seulement, ajouter le 3e = invasif | nouvel axe = 1 dossier `features/` + 1 page + 1 ligne de routing |

## Ajouter un axe (exemple)
1. `features/<axe>/service.py` exposant une façade.
2. une page `ui/pages/<axe>.py`.
3. enregistrer la page dans `core/config.PAGES` + le routing de `ui/app.py`.
Aucune autre couche n'est touchée.

## Sécurité de l'axe 3 (text-to-query)
Le LLM ne génère **jamais de code**. Il produit une `QuerySpec` (champs whitelistés),
validée (`query_engine.validate`) puis exécutée par des opérations pandas contrôlées.
Toute métrique/région/catégorie hors liste est rejetée.

## Lancer
```bash
pip install -r requirements.txt
ollama pull gemma3:4b
streamlit run app/main.py                 # l'app
python app/tests/test_features.py         # tests features (sans Ollama)
python app/eval/runner.py --brick all --dry   # pipeline d'éval (harness)
python app/tools/benchmark.py             # benchmark sur ton PC
```
