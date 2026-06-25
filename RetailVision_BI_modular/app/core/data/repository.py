"""Acces aux donnees + calcul des KPIs. Source de verite partagee par tous les axes."""
from __future__ import annotations
from functools import lru_cache
from pathlib import Path
import pandas as pd

from core import config
from core.domain.models import KPISet
from core.domain.state import Filters

_DEFAULT_CSV = Path(__file__).resolve().parents[2] / "data" / "sales.csv"


@lru_cache(maxsize=1)
def load_sales() -> pd.DataFrame:
    path = Path(config.DATA_PATH) if config.DATA_PATH else _DEFAULT_CSV
    df = pd.read_csv(path, parse_dates=["date"])
    df["marge"] = df["ca"] * df["marge_pct"]
    df["panier_moyen"] = df["ca"] / df["transactions"]
    return df


def apply_filters(df: pd.DataFrame, f: Filters) -> pd.DataFrame:
    mask = (df["date"] >= f.date_start) & (df["date"] <= f.date_end)
    if f.region:
        mask &= df["region"] == f.region
    if f.categorie:
        mask &= df["categorie"] == f.categorie
    return df[mask]


def compute_kpis(df: pd.DataFrame) -> KPISet:
    y24 = df[df["date"].dt.year == 2024]
    y25 = df[df["date"].dt.year == 2025]
    def delta(a, b):
        return (b - a) / a * 100 if a else 0.0
    ca24, ca25 = y24["ca"].sum(), y25["ca"].sum()
    m24 = y24["marge_pct"].mean() * 100
    m25 = y25["marge_pct"].mean() * 100
    p24, p25 = y24["panier_moyen"].mean(), y25["panier_moyen"].mean()
    return KPISet(
        ca_2025=ca25, ca_delta_pct=delta(ca24, ca25),
        tx_delta_pct=delta(y24["transactions"].sum(), y25["transactions"].sum()),
        marge_2025=m25, marge_delta_pts=m25 - m24,
        panier_delta_pct=delta(p24, p25),
        top_region=y25.groupby("region")["ca"].sum().idxmax() if not y25.empty else "",
        top_categorie=y25.groupby("categorie")["ca"].sum().idxmax() if not y25.empty else "",
    )


def performance_facts(df_filtered: "pd.DataFrame") -> list[str]:
    """Faits chiffres de la page Performance (sur donnees filtrees)."""
    if df_filtered.empty:
        return ["Aucune donnee pour les filtres selectionnes."]
    ca = df_filtered["ca"].sum()
    tx = df_filtered["transactions"].sum()
    marge = df_filtered["marge_pct"].mean() * 100
    top_cat = df_filtered.groupby("categorie")["ca"].sum().idxmax()
    return [
        f"CA total filtre : {ca/1e6:.2f} M€",
        f"Transactions : {tx:,.0f}",
        f"Marge moyenne : {marge:.1f}%",
        f"Categorie en tete : {top_cat}",
    ]


def regions_facts(df_filtered: "pd.DataFrame") -> list[str]:
    """Faits chiffres de la page Regions (sur donnees filtrees)."""
    if df_filtered.empty:
        return ["Aucune donnee pour les filtres selectionnes."]
    par_region = df_filtered.groupby("region")["ca"].sum().sort_values(ascending=False)
    total = par_region.sum()
    top = par_region.index[0]
    part = par_region.iloc[0] / total * 100 if total else 0
    top_cat = df_filtered.groupby("categorie")["ca"].sum().idxmax()
    return [
        f"Region leader : {top} ({part:.0f}% du CA)",
        f"Nombre de regions actives : {par_region.shape[0]}",
        f"Categorie dominante : {top_cat}",
        f"CA total : {total/1e6:.2f} M€",
    ]
