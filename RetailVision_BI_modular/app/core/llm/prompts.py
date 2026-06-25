"""Templates de prompts centralises (un seul endroit a maintenir)."""
from core import config


def intent_extraction(text: str, year: int) -> str:
    return f"""Tu es un extracteur d'intentions pour un dashboard retail.
Extrais les informations depuis la commande vocale et retourne UNIQUEMENT un JSON.

Champs : action ("filter" si filtrage, "unknown" sinon), date_start (YYYY-MM-DD|null),
date_end (YYYY-MM-DD|null), region (parmi {config.REGIONS}|null), categorie (parmi {config.CATEGORIES}|null).
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
    return f"""Tu traduis une question en langage naturel en une SPEC de requete JSON pour un dataframe
de ventes retail (colonnes: date, region, categorie, transactions, ca, marge_pct).
Retourne UNIQUEMENT un JSON :
{{"metric": "ca|transactions|marge_pct", "agg": "sum|mean|max|min",
  "group_by": "region|categorie|mois|null", "region": "{config.REGIONS}|null",
  "categorie": "{config.CATEGORIES}|null", "year": 2024|2025|null,
  "sort": "asc|desc", "limit": entier|null, "valid": true|false}}
valid=false si la question est hors perimetre. Ne jamais ecrire de code, seulement la spec.

Question : "{question}" """
