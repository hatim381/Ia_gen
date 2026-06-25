# Analyse IA — RetailVision BI

Réponses aux attentes C5.1 / C5.2 / C5.3 du module IA Générative EFREI.
Auteur : Bill Laurel Padonou — Juin 2026

---

## C5.1 — Identification des cas d'usage

### Les 3 axes retenus

#### Axe 1 — Navigation vocale par STT (implémenté)

**Problème adressé :** un utilisateur en situation de handicap moteur (ou simplement en mode mains libres) ne peut pas interagir avec un dashboard classique via souris/clavier.

**Solution :** pipeline STT qui transcrit la voix de l'utilisateur, interprète son intention (changement de page, application de filtre) et mute l'état du dashboard en conséquence.

| Angle | Pertinence |
|---|---|
| B2B | Forte — accessibilité légale, usage terrain (tablettes en entrepôt, réunions sans souris) |
| B2C | Forte — applications de suivi personnel, kiosques interactifs, mobile mains occupées |

#### Axe 2 — Narration automatique des KPIs

**Problème adressé :** les dirigeants lisent rarement les graphiques en détail. Ils ont besoin d'un résumé exécutif immédiat.

**Solution :** un LLM reçoit les métriques clés calculées côté Python (CA, tendances, anomalies) et génère automatiquement un paragraphe de synthèse affiché en tête de dashboard.

Exemple de sortie :
> *"Ce trimestre, le CA Nord progresse de +18% vs N-1, porté par l'Électronique. Point d'attention : la marge Sport est en recul de 3 points depuis février."*

| Angle | Pertinence |
|---|---|
| B2B | Très forte — génération de slides exécutifs, rapports hebdomadaires automatisés |
| B2C | Moyenne — utile si le dashboard est accessible à des clients non-initiés à la BI |

**Convergence avec l'axe 1 :** la narration peut être lue à voix haute (TTS) pour former un loop complet voix-in / voix-out.

#### Axe 3 — Chatbot Q&A analytique (Text-to-Query)

**Problème adressé :** un décideur veut répondre à une question ad hoc ("Quelle région performe le mieux sur les 6 derniers mois ?") sans dépendre d'un analyste.

**Solution :** le LLM traduit une question en langage naturel en une requête Pandas, l'exécute en sandbox sur le DataFrame local, et retourne le résultat.

| Angle | Pertinence |
|---|---|
| B2B | Très forte — démocratise l'accès aux données pour les non-techniciens |
| B2C | Forte — un client grand public peut interroger ses propres données (budget, fitness, santé) |

**Convergence avec les axes 1 et 2 :** la question peut être posée à la voix (axe 1), et la réponse peut être narrée (axe 2).

---

### Tableau de convergence des 3 axes

| | Axe 1 — STT | Axe 2 — Narration | Axe 3 — Q&A |
|---|---|---|---|
| B2B | ✅ | ✅✅ | ✅✅ |
| B2C | ✅ | ✅ | ✅ |
| Infra partagée | Ollama/Whisper | Ollama (même instance) | Ollama (même instance) |
| Implémenté | Oui | Non | Non |

Les 3 axes partagent la même infrastructure Ollama locale. L'axe 1 peut servir d'interface d'entrée pour les axes 2 et 3.

---

### Cas moins pertinents

**Génération d'images (DALL-E, Stable Diffusion)**
Hors sujet pour un dashboard BI. Les graphiques sont générés par code (Plotly), pas par un modèle de diffusion. Aucune valeur ajoutée, coût computationnel très élevé.

**Text-to-Speech (TTS)**
Pertinent en complément de l'axe 2 (narration lue à voix haute) mais insuffisant seul comme axe IA générative : c'est une technologie de restitution, pas de génération de contenu analytique.

**Recommandations produits (RAG sur catalogue)**
Pertinent en B2C e-commerce mais hors périmètre d'un dashboard de statistiques internes. Nécessiterait un corpus produit externe non disponible dans ce projet.

---

## C5.2 — Décisions d'implémentation

### Local vs API — choix tranché

Le sujet impose "local au minimum". Au-delà de cette contrainte formelle, le choix local est justifié par la nature des données :

| Critère | Local (retenu) | API externe |
|---|---|---|
| Confidentialité | Données ne quittent pas la machine | Audio/texte envoyés à un tiers |
| Coût | 0 à l'usage | Pay-per-token / pay-per-minute |
| Disponibilité | Fonctionne sans internet | Dépend du réseau |
| Latence | ~1-5s selon le modèle | ~0.5-2s (mais ajout latence réseau) |
| Conformité RGPD | Totale | Dépend du contrat avec le provider |

Envoyer de l'audio à l'API OpenAI Whisper, ou du texte contenant des données de ventes à GPT-4, est un non-go sur des données de type financier/RH — même simulées dans ce projet.

---

### Choix du modèle STT : Whisper `base`

OpenAI Whisper est disponible en plusieurs tailles. Le choix de `base` résulte d'un compromis :

| Modèle | Taille | WER français | Latence CPU | Retenu |
|---|---|---|---|---|
| tiny | 39 Mo | ~12% | < 0.5s | Non — qualité insuffisante |
| base | 139 Mo | ~7% | ~1s | **Oui** |
| small | 244 Mo | ~5% | ~3s | Non — latence trop élevée sans GPU |
| medium | 769 Mo | ~4% | ~8s | Non — inacceptable en temps réel |

`base` offre une transcription en français de qualité suffisante (WER ~7%) avec une latence sous la seconde sur CPU, sans nécessiter de GPU.

**Langue forcée à `fr`** : sans forçage, Whisper détecte automatiquement la langue sur les 30 premières secondes d'audio. Sur des commandes courtes (< 3 secondes), la détection automatique est peu fiable et ralentit la transcription.

---

### Choix du LLM : Mistral 7B Instruct (cible)

Le LLM est utilisé pour une tâche très ciblée : extraire des entités structurées (dates, régions, catégories) depuis une phrase courte en français et les retourner en JSON.

**Candidats évalués :**

| Modèle | Taille | Qualité extraction JSON | Français | Latence CPU | Verdict |
|---|---|---|---|---|---|
| Mistral 7B Instruct | 4.1 Go | Excellente | Natif (entreprise française) | ~3-4s | Retenu |
| Llama 3.1 8B Instruct | 4.7 Go | Très bonne | Très bon | ~4-5s | Comparatif |
| Qwen2.5 7B Instruct | 4.7 Go | Excellente | Très bon | ~3-4s | Comparatif |
| Phi-3.5 Mini | 2.2 Go | Bonne | Bon | ~1.5s | Comparatif vitesse |
| Gemma3 4B | 3.3 Go | Moyenne* | Correct | ~2s | Baseline |

*Gemma3:4b a nécessité le paramètre `format="json"` d'Ollama (grammar sampling) pour produire du JSON valide — il ignore les instructions de format dans le prompt.

**Mistral est privilégié** pour deux raisons : il est d'origine française (meilleure modélisation des tournures de phrase françaises) et son suivi d'instructions structurées est supérieur à Gemma sans trick supplémentaire.

> Note : le benchmark comparatif est en cours. Le modèle retenu dans le code sera mis à jour après mesures.

---

### Architecture double pipeline

Toutes les commandes ne nécessitent pas un LLM. Un "reset" ou un "accueil" est une chaîne de caractères reconnaissable par expression régulière en 0 milliseconde.

```
Commande vocale transcrite
        │
        ▼
┌────────────────────────────┐
│  Fast-Track (Regex)        │  ← commandes simples (5 patterns)
│  0ms — 0 token consommé    │    "accueil", "reset", "performance"...
└─────────────┬──────────────┘
              │ non reconnu
              ▼
┌────────────────────────────┐
│  LLM Ollama (Mistral 7B)   │  ← commandes complexes
│  extraction JSON structuré │    filtres date/région/catégorie
│  ~3-5s                     │
└────────────────────────────┘
```

**Avantage :** les commandes les plus fréquentes (navigation entre pages) sont instantanées. Le LLM n'est sollicité que pour les requêtes qui en ont réellement besoin.

---

### Potentiel B2C du STT

**Opportunités identifiées :**

- **Accessibilité PMR** : cas du VP sans usage des bras (cas d'usage initial du sujet). La navigation vocale rend le dashboard utilisable par des personnes avec handicap moteur, conformément aux obligations d'accessibilité numérique (RGAA, WCAG 2.1 AA).
- **Usage mobile mains libres** : un commercial en déplacement peut interroger son dashboard sans poser sa tablette.
- **Kiosques interactifs** : bornes en magasin ou en entrepôt permettant aux employés terrain d'interroger les stocks/ventes sans clavier.
- **Interfaces embarquées** : véhicules, lignes de production où les mains sont occupées.

**Limites à documenter honnêtement :**

- **Multilinguisme** : Whisper supporte ~99 langues mais la qualité baisse significativement sur les accents régionaux forts ou les mélanges de langues (ex : "Show me les ventes de Nord"). Le forçage à `fr` peut mal gérer les commandes mixtes.
- **Bruit ambiant** : Whisper `base` est sensible aux bruits de fond sans Voice Activity Detection (VAD) préalable. Un open-space ou un entrepôt bruyant dégradent la WER.
- **Adoption utilisateur** : parler à son écran reste une friction comportementale pour beaucoup d'utilisateurs dans un contexte professionnel public.
- **Vie privée** : les utilisateurs grand public sont réticents à activer le microphone en permanence. La solution "push-to-talk" (bouton à maintenir) est préférable à la détection continue.

---

## C5.3 — Évaluation de la qualité

### Scénarios de test

| # | Commande vocale | Pipeline attendu | Action attendue | Résultat |
|---|---|---|---|---|
| T1 | "Accueil" | Fast-Track | navigate → Vue Globale | ✅ |
| T2 | "Régions" | Fast-Track | navigate → Régions | ✅ |
| T3 | "Reset les filtres" | Fast-Track | clear tous les filtres | ✅ |
| T4 | "Affiche les ventes de janvier 2025" | LLM | filter date [01/01/2025 – 31/01/2025] | ✅ |
| T5 | "Région Nord" | LLM | filter region = Nord | ✅ |
| T6 | "Catégorie Sport entre mars et juin 2024" | LLM | filter categ = Sport + date [03/2024 – 06/2024] | ✅ |
| T7 | "Météo demain" | LLM | action = unknown, pas de crash | ✅ |

**Score actuel (gemma3:4b avec format=json) : 7/7 scénarios corrects.**

---

### Métriques définies

**WER (Word Error Rate) — brique STT**
Mesure le taux d'erreur de transcription. Cible : < 10% sur des commandes courtes en français dans un environnement calme.
`WER = (substitutions + insertions + suppressions) / nb_mots_référence`

**Précision d'extraction — brique LLM**
Proportion d'entités correctement extraites sur les scénarios de type `filter`.
Cible : > 85%.
`Précision = entités_correctes / entités_attendues`

**Latence end-to-end**
Temps écoulé entre la fin de la prise de parole et la mise à jour du dashboard.
Cible : < 5s pour les commandes complexes, < 200ms pour les commandes fast-track.

---

### Comparatif des modèles LLM (benchmark exécuté le 2026-06-24)

Benchmark réalisé sur les 7 scénarios définis ci-dessus, sur CPU (i5-9300H, 8 threads, sans GPU).
Tous les modèles ont été testés avec le paramètre `format="json"` d'Ollama (grammar sampling).

La latence T4 (~100s pour tous les modèles) correspond au cold start : chargement du modèle en RAM au premier appel. Elle est exclue de la colonne "Latence warm" qui reflète la latence réelle en usage (modèle déjà chargé, T5+T6+T7).

| Modèle | Score global | Score LLM | Latence warm moy. | Échec(s) | Verdict |
|---|---|---|---|---|---|
| gemma3:4b | 7/7 | 4/4 | ~7.6s | — | **Retenu** |
| qwen2.5:7b | 7/7 | 4/4 | ~15.9s | — | Précis mais 2× plus lent |
| phi3.5 | 6/7 | 3/4 | ~14.3s | T4 : action="navigate" au lieu de "filter" | Éliminé |
| mistral | 6/7 | 3/4 | ~13.5s | T5 : "Région Nord" → navigation au lieu de filtre | Éliminé |
| llama3.1 | 5/7 | 2/4 | ~15.5s | T4 : date_end manquant ; T5 : même erreur que mistral | Éliminé |

**Analyse des échecs :**

- **phi3.5 — T4** : "Affiche les ventes de janvier 2025" classé comme `navigate` au lieu de `filter`. Le modèle confond "afficher" avec une navigation de page plutôt qu'un filtrage de données.
- **mistral — T5** : "Région Nord" interprété comme `navigate → Régions` au lieu de `filter region=Nord`. Le modèle ambiguïse le mot "Région" comme référence à la page plutôt qu'à un filtre géographique — paradoxal pour un modèle français.
- **llama3.1 — T4 + T5** : cumulatif des deux erreurs ci-dessus. Suivi d'instructions structurées insuffisant pour les cas ambigus.
- **phi3.5 — T7 (passé mais dégradé)** : le champ `date_end` contient du texte en langage naturel au lieu de null — fuite de contenu hors du JSON, révélatrice d'un respect partiel du schéma même avec `format="json"`.

**Modèle retenu : gemma3:4b**

gemma3:4b obtient le score parfait (7/7) avec la latence warm la plus basse (~7.6s). qwen2.5:7b atteint le même score mais est deux fois plus lent à chaud (~15.9s), sans avantage de précision. Le paramètre `format="json"` requis par gemma3:4b est déjà implémenté dans le code et constitue un contournement stable, pas une limitation.

Le modèle en production dans `intent_parser.py` reste donc `gemma3:4b`.
