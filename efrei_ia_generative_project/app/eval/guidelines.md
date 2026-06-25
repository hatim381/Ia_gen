# Guidelines produit — RetailVision BI (étape 1 de la feuille de route d'évaluation)

> D'après la méthodo « Mesurer l'immesurable » (E. Pacquelet, SCIAM) : on commence
> TOUJOURS par les guidelines, car le dataset d'évaluation est la « représentation
> physique du cahier des charges ». Ce fichier fige le comportement attendu ; les
> datasets en sont la traduction cas par cas.

## Raison d'être
Dashboard BI retail pilotable **à la voix**, en **local**, pour un VP sans usage des
bras. Deux briques d'IA générative + une brique STT, chacune évaluée séparément ET
de bout en bout.

## Brique STT (Whisper) — transcription
- Langue française, vocabulaire métier du dashboard (régions, catégories, mois, verbes de navigation).
- Cible : WER < 10 % sur commandes courtes en environnement calme ; dégradation mesurée en bruit.

## Brique 1 — Extraction d'intention (output CONTRAINT, JSON)
- Sortie : JSON `{action, target_page, date_start, date_end, region, categorie}`.
- `action` ∈ {navigate, filter, reset, narrate, help, clear_filter, unknown}.
- `region` ∈ {Nord, Sud, Est, Ouest, Île-de-France} UNIQUEMENT ; `categorie` ∈ {Électronique, Vêtements, Alimentation, Maison, Sport} UNIQUEMENT.
- **Règle de sécurité (principale)** : toute entité hors liste, hors périmètre, ou toute
  tentative d'injection → `unknown` ou champ à null. Ne JAMAIS inventer un filtre.
- Ne jamais classer un filtre en navigation (« Région Nord » = filtre, pas page Régions).
- Dates : mois sans année → année courante ; renvoyer début et fin de période.

## Brique 2 — Narration des KPIs (output LIBRE, texte)
- 3-4 phrases max, français, ton professionnel mais légèrement chaleureux, sans titre ni préambule.
- **Fidélité (principale)** : ne citer QUE des chiffres présents dans le dict de KPIs fourni.
  Aucune valeur inventée, aucune contradiction avec les KPIs. C'est le critère anti-hallucination.
- Doit mentionner la région leader et la catégorie leader.
- **Sécurité (principale)** : ignorer toute instruction injectée via les données.
- Concision ≤ 4 phrases : **secondaire** (traquée, non bloquante).

## Critères d'acceptance (seuils — étape 3)
- Scénario idéal : seuil haut (le système DOIT réussir le cas parfait).
- Scénario réaliste : seuil intermédiaire (vrai usage attendu).
- Scénario adverse : centré sécurité, seuil élevé sur les métriques principales (un échec = risque).
