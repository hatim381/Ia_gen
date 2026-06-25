import numpy as np
import pandas as pd
from pathlib import Path

SEED = 42
np.random.seed(SEED)

REGIONS = ["Nord", "Sud", "Est", "Ouest", "Île-de-France"]
CATEGORIES = ["Électronique", "Vêtements", "Alimentation", "Maison", "Sport"]

CA_BASE = {
    "Nord": 18_000,
    "Sud": 22_000,
    "Est": 15_000,
    "Ouest": 16_000,
    "Île-de-France": 35_000,
}

CA_CATEGORY_WEIGHT = {
    "Électronique": 1.4,
    "Vêtements": 1.0,
    "Alimentation": 0.8,
    "Maison": 0.9,
    "Sport": 0.7,
}

MARGE_BASE = {
    "Électronique": 0.22,
    "Vêtements": 0.45,
    "Alimentation": 0.18,
    "Maison": 0.35,
    "Sport": 0.38,
}


def seasonal_multiplier(date: pd.Timestamp) -> float:
    month = date.month
    if month == 12:
        return 1.4
    if month in (7, 8):
        return 1.15
    if month in (1, 2):
        return 0.80
    return 1.0


def build_rows() -> list[dict]:
    rows = []
    dates = pd.date_range("2024-01-01", "2025-12-31", freq="D")

    for date in dates:
        season = seasonal_multiplier(date)
        dow_factor = 0.75 if date.dayofweek >= 5 else 1.0

        for region in REGIONS:
            for category in CATEGORIES:
                base = CA_BASE[region] * CA_CATEGORY_WEIGHT[category]
                noise = np.random.normal(1.0, 0.08)
                ca = base * season * dow_factor * noise / len(CATEGORIES)
                ca = max(ca, 0)

                transactions = int(ca / np.random.uniform(45, 85))
                marge_pct = MARGE_BASE[category] + np.random.normal(0, 0.02)
                marge_pct = round(float(np.clip(marge_pct, 0.05, 0.65)), 4)

                rows.append(
                    {
                        "date": date.date(),
                        "region": region,
                        "categorie": category,
                        "transactions": max(transactions, 1),
                        "ca": round(float(ca), 2),
                        "marge_pct": marge_pct,
                    }
                )
    return rows


def main() -> None:
    rows = build_rows()
    df = pd.DataFrame(rows)
    output_path = Path(__file__).parent / "sales.csv"
    df.to_csv(output_path, index=False)
    print(f"Generated {len(df):,} rows → {output_path}")
    print(df.head())
    print(f"\nCA total : {df['ca'].sum():,.0f} €")


if __name__ == "__main__":
    main()
