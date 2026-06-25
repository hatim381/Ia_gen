"""Génère une synthèse exécutive des KPIs en langage naturel via Ollama."""
from stt.intent_parser import OLLAMA_MODEL


def generate_narrative(kpis: dict) -> str:
    """Retourne un paragraphe de synthèse exécutive (3-4 phrases) à partir des KPIs calculés."""
    import ollama

    prompt = f"""Tu es un analyste BI senior. Rédige une synthèse exécutive courte (3-4 phrases maximum, ton professionnel, en français) à partir des indicateurs 2025 suivants :

- CA 2025 : {kpis['ca_2025'] / 1e6:.1f} M€ ({kpis['ca_delta_pct']:+.1f}% vs 2024)
- Transactions : {kpis['tx_delta_pct']:+.1f}% vs 2024
- Marge moyenne : {kpis['marge_2025']:.1f}% ({kpis['marge_delta_pts']:+.2f} points vs 2024)
- Panier moyen : {kpis['panier_delta_pct']:+.1f}% vs 2024
- Région leader : {kpis['top_region']}
- Catégorie leader : {kpis['top_categorie']}

Commence directement par la synthèse, sans titre ni préambule."""

    response = ollama.chat(
        model=OLLAMA_MODEL,
        messages=[{"role": "user", "content": prompt}],
        options={"temperature": 0.4},
    )
    return response["message"]["content"].strip()
