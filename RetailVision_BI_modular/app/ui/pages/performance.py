# Page Performance (portee dans ui/pages lors du refactor modulaire).
import pandas as pd
import plotly.express as px
import streamlit as st

from core.data import repository as repo
from ui.components import narration_block


def _kpi_card(col, label, icon, value):
    col.markdown(
        f"""<div style="background:linear-gradient(135deg,#1E1E2E 0%,#252540 100%);border-radius:14px;padding:18px 22px;border-left:4px solid #4F8BF9;box-shadow:0 4px 20px rgba(0,0,0,0.25);margin-bottom:4px">
<div style="display:flex;align-items:center;gap:8px;margin-bottom:8px">
  <span style="font-size:18px;line-height:1">{icon}</span>
  <p style="color:#9CA3AF;font-size:10px;margin:0;text-transform:uppercase;letter-spacing:1px;font-weight:700">{label}</p>
</div>
<p style="font-size:24px;font-weight:800;margin:0;letter-spacing:-0.5px">{value}</p>
</div>""",
        unsafe_allow_html=True,
    )


def render(df_all: pd.DataFrame, df_filtered: pd.DataFrame) -> None:
    st.title("Performance")

    region_label = st.session_state.filter_region or "toutes régions"
    cat_label = st.session_state.filter_categorie or "toutes catégories"
    start = st.session_state.filter_date_start.strftime("%d/%m/%Y")
    end = st.session_state.filter_date_end.strftime("%d/%m/%Y")
    st.caption(f"📅 {start} → {end}  ·  📍 {region_label}  ·  🏷️ {cat_label}")

    narration_block.render("Performance", repo.performance_facts(df_filtered), key="performance")

    if df_filtered.empty:
        st.warning("Aucune donnée pour les filtres sélectionnés.", icon="⚠️")
        return

    ca_total = df_filtered["ca"].sum()
    tx_total = df_filtered["transactions"].sum()
    marge_moy = df_filtered["marge_pct"].mean() * 100
    panier_moy = df_filtered["panier_moyen"].mean()

    c1, c2, c3, c4 = st.columns(4)
    _kpi_card(c1, "CA total", "💰", f"{ca_total/1e6:.2f} M€")
    _kpi_card(c2, "Transactions", "📦", f"{tx_total:,.0f}")
    _kpi_card(c3, "Marge moy.", "📊", f"{marge_moy:.1f}%")
    _kpi_card(c4, "Panier moyen", "🛒", f"{panier_moy:.2f} €")

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("---")

    daily = df_filtered.groupby("date").agg(ca=("ca", "sum")).reset_index()
    fig_daily = px.line(
        daily,
        x="date",
        y="ca",
        title="CA journalier",
        labels={"date": "", "ca": "CA (€)"},
        color_discrete_sequence=["#4F8BF9"],
    )
    fig_daily.update_layout(
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        hovermode="x unified",
    )
    st.plotly_chart(fig_daily, use_container_width=True)

    col_left, col_right = st.columns(2)

    with col_left:
        top_cat = (
            df_filtered.groupby("categorie")["ca"]
            .sum()
            .sort_values(ascending=False)
            .head(5)
            .reset_index()
        )
        fig_top = px.bar(
            top_cat,
            x="categorie",
            y="ca",
            title="Top 5 catégories (CA)",
            labels={"ca": "CA (€)", "categorie": ""},
            color="categorie",
            color_discrete_sequence=px.colors.qualitative.Bold,
        )
        fig_top.update_layout(
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            showlegend=False,
        )
        st.plotly_chart(fig_top, use_container_width=True)

    with col_right:
        monthly_cat = (
            df_filtered.groupby(
                [df_filtered["date"].dt.to_period("M").dt.to_timestamp(), "categorie"]
            )["ca"]
            .sum()
            .reset_index()
            .rename(columns={"date": "mois"})
        )
        fig_stacked = px.bar(
            monthly_cat,
            x="mois",
            y="ca",
            color="categorie",
            title="CA mensuel par catégorie",
            labels={"ca": "CA (€)", "mois": "", "categorie": "Catégorie"},
            color_discrete_sequence=px.colors.qualitative.Bold,
        )
        fig_stacked.update_layout(
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            barmode="stack",
        )
        st.plotly_chart(fig_stacked, use_container_width=True)

    st.markdown("---")
    st.subheader("Marge par catégorie")
    marge_cat = (
        df_filtered.groupby("categorie")["marge_pct"]
        .mean()
        .mul(100)
        .reset_index()
        .rename(columns={"marge_pct": "marge_pct_pct"})
        .sort_values("marge_pct_pct", ascending=False)
    )
    fig_marge = px.bar(
        marge_cat,
        x="categorie",
        y="marge_pct_pct",
        labels={"marge_pct_pct": "Marge (%)", "categorie": ""},
        color="marge_pct_pct",
        color_continuous_scale="RdYlGn",
        range_color=[0, 60],
    )
    fig_marge.update_layout(
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        coloraxis_showscale=False,
    )
    st.plotly_chart(fig_marge, use_container_width=True)
