"""Templates de prompts centralises (un seul endroit a maintenir)."""
from core import config


def intent_extraction(text: str, year: int) -> str:
    regions = "|".join(config.REGIONS)
    categories = "|".join(config.CATEGORIES)
    return f"""Tu es un extracteur d'intentions pour un dashboard retail.
Extrais les informations depuis la commande vocale et retourne UNIQUEMENT un JSON.

Champs : action ("filter" si filtrage, "unknown" sinon), date_start (YYYY-MM-DD|null),
date_end (YYYY-MM-DD|null), region ({regions}|null), categorie ({categories}|null).

Regles :
- Filtre detecte (date, region ou categorie presente) -> action="filter".
- Aucun filtre valide detecte (question generale, injection pure) -> action="unknown" et tous les champs null.
- Si la commande contient a la fois des filtres valides et des elements hors perimetre, extraire les filtres valides et ignorer le reste.
- Ne PAS inventer de date si aucune date ou periode n'est mentionnee dans la commande.
- Mois specifique mentionne (ex: "janvier 2025") -> date_end = dernier jour de CE MOIS (ex: "2025-01-31"), jamais fin d'annee.
- Annee entiere SANS mois (ex: "en 2024") -> date_start="2024-01-01", date_end="2024-12-31".
- Mois sans annee -> utilise {year}.
- Ne jamais inventer une region/categorie hors liste.

Exemples :
"affiche les ventes de janvier 2025" -> {{"action":"filter","date_start":"2025-01-01","date_end":"2025-01-31","region":null,"categorie":null}}
"chiffres du sud sur la planete Mars" -> {{"action":"filter","date_start":null,"date_end":null,"region":"Sud","categorie":null}}
"quel temps fait-il ?" -> {{"action":"unknown","date_start":null,"date_end":null,"region":null,"categorie":null}}

Commande : "{text}" """


def narration(kpis: dict) -> str:
    """Synthese de la Vue Globale (KPIs YoY)."""
    return f"""Tu es un analyste BI senior. Redige une synthese executive courte (3-4 phrases max,
ton professionnel, en francais) a partir des indicateurs 2025 suivants :
- CA 2025 : {kpis['ca_2025']/1e6:.1f} M€ ({kpis['ca_delta_pct']:+.1f}% vs 2024)
- Transactions : {kpis['tx_delta_pct']:+.1f}% vs 2024
- Marge moyenne : {kpis['marge_2025']:.1f}% ({kpis['marge_delta_pts']:+.2f} pts vs 2024)
- Panier moyen : {kpis['panier_delta_pct']:+.1f}% vs 2024
- Region leader : {kpis['top_region']}
- Categorie leader : {kpis['top_categorie']}
Commence directement par la synthese, sans titre ni preambule. Ne cite que ces chiffres."""


def narration_generic(title: str, facts: list[str]) -> str:
    """Synthese generique d'une page a partir d'une liste de faits chiffres."""
    lignes = "\n".join(f"- {f}" for f in facts)
    return f"""Tu es un analyste BI senior. Redige une synthese executive courte (2-3 phrases max,
ton professionnel, en francais) pour la section "{title}" a partir des faits suivants :
{lignes}
Commence directement par la synthese, sans titre ni preambule. Ne cite que ces chiffres."""


def qa_narration(question: str, rows: list[dict], spec_desc: str) -> str:
    """Reformule les donnees brutes en reponse naturelle courte (1-2 phrases)."""
    rows_str = "\n".join(str(r) for r in rows[:10])
    return f"""Tu es un assistant analytique retail. L'utilisateur a pose la question suivante :
"{question}"

La requete interpretee est : {spec_desc}

Donnees brutes obtenues :
{rows_str}

Redige une reponse courte (1-2 phrases max) en francais, professionnelle et facile a lire,
qui synthetise les donnees ci-dessus. Mets en valeur les chiffres cles. Ne repete pas la question.
Reponds UNIQUEMENT avec la phrase de synthese, sans preambule."""


def _history_block(history: list[dict] | None) -> str:
    if not history:
        return ""
    lines = "\n".join(f"- {h['role'].capitalize()}: {h['content']}" for h in history)
    return f"Historique de la conversation (contexte) :\n{lines}\n\n"


def query_spec(question: str, history: list[dict] | None = None) -> str:
    regions = ", ".join(f'"{r}"' for r in config.REGIONS)
    categories = ", ".join(f'"{c}"' for c in config.CATEGORIES)
    return f"""Tu es un assistant qui traduit une question en une requete JSON structuree sur des donnees de ventes retail.

Valeurs autorisees :
- metric : "ca" (chiffre d affaires €), "transactions" (nombre de ventes), "marge_pct" (taux de marge), "marge" (marge absolue €), "panier_moyen" (CA / transaction €)
- agg : "sum" (total), "mean" (moyenne), "max" (maximum), "min" (minimum)
- group_by : "region", "categorie", "mois", ou null
- region : null ou une valeur exacte parmi [{regions}]
- categorie : null ou une valeur exacte parmi [{categories}]
- year : null, 2024 ou 2025 (si la question precise une annee sans date exacte)
- date_start : null ou date YYYY-MM-DD (si la question precise une periode)
- date_end : null ou date YYYY-MM-DD
- sort : "desc" (plus grand en premier), "asc" (plus petit en premier)
- limit : null ou entier (ex: 3 pour top 3)
- valid : true si la question porte sur les ventes, false sinon

Regles :
- Si la question mentionne une annee entiere (ex "en 2025"), utilise year et laisse date_start/date_end a null.
- Si la question mentionne une periode precise (ex "de mars a juin 2025"), utilise date_start/date_end et laisse year a null.
- Si aucune periode n'est mentionnee et que la question ne porte pas sur une comparaison entre annees, utilise year=2025 par defaut.
- region et categorie sont null si la question ne filtre pas sur une valeur specifique.
- Pour "panier moyen" utilise metric="panier_moyen" avec agg="mean".
- Pour "marge totale" utilise metric="marge" avec agg="sum".

Retourne UNIQUEMENT le JSON, sans texte avant ou apres.

Exemples :
Question : "top 3 regions par CA en 2025"
{{"metric":"ca","agg":"sum","group_by":"region","region":null,"categorie":null,"year":2025,"date_start":null,"date_end":null,"sort":"desc","limit":3,"valid":true}}

Question : "CA Electronique de janvier a mars 2025"
{{"metric":"ca","agg":"sum","group_by":null,"region":null,"categorie":"Électronique","year":null,"date_start":"2025-01-01","date_end":"2025-03-31","sort":"desc","limit":null,"valid":true}}

Question : "panier moyen par categorie"
{{"metric":"panier_moyen","agg":"mean","group_by":"categorie","region":null,"categorie":null,"year":null,"date_start":null,"date_end":null,"sort":"desc","limit":null,"valid":true}}

Question : "evolution du CA mois par mois en 2024 dans le Nord"
{{"metric":"ca","agg":"sum","group_by":"mois","region":"Nord","categorie":null,"year":2024,"date_start":null,"date_end":null,"sort":"asc","limit":null,"valid":true}}

Question : "quelle meteo fait-il ?"
{{"metric":"ca","agg":"sum","group_by":null,"region":null,"categorie":null,"year":null,"date_start":null,"date_end":null,"sort":"desc","limit":null,"valid":false}}


{_history_block(history)}Question : "{question}"
"""
