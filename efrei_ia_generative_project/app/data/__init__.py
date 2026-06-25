from pathlib import Path
import pandas as pd
import streamlit as st

DATA_PATH = Path(__file__).parent / "sales.csv"

REGIONS = ["Nord", "Sud", "Est", "Ouest", "Île-de-France"]
CATEGORIES = ["Électronique", "Vêtements", "Alimentation", "Maison", "Sport"]


@st.cache_data
def load_sales() -> pd.DataFrame:
    df = pd.read_csv(DATA_PATH, parse_dates=["date"])
    df["marge"] = df["ca"] * df["marge_pct"]
    df["panier_moyen"] = df["ca"] / df["transactions"]
    return df
