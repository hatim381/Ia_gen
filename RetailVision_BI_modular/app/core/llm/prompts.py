"""Templates de prompts centralises (un seul endroit a maintenir)."""
from core import config


def intent_extraction(text: str, year: int) -> str:
    regions = "|".join(config.REGIONS)
    categories = "|".join(config.CATEGORIES)
    return f"""Tu es un extracteur d'intentions pour un dashboard retail.
Extrais les informations depuis la commande vocale et retourne UNIQUEMENT un JSON.

Champs : action ("filter" si filtrage, "unknown" sinon), date_start (YYYY-MM-DD|null),
date_end (YYYY-MM-DD|null), region ({regions}|null), categorie ({categories}|null).
Regles : mois sans annee -> {year}. Filtre detecte -> action="filter". Hors perimetre -> "unknown" et champs null.
Ne jamais inventer une region/categorie hors liste.

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


def query_spec(question: str) -> str:
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

Question : "{question}"
"""
