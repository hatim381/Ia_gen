import pandas as pd
import plotly.express as px
import streamlit as st


def render(df_all: pd.DataFrame, df_filtered: pd.DataFrame) -> None:
    st.title("Performance")

    region_label = st.session_state.filter_region or "toutes régions"
    cat_label = st.session_state.filter_categorie or "toutes catégories"
    start = st.session_state.filter_date_start.strftime("%d/%m/%Y")
    end = st.session_state.filter_date_end.strftime("%d/%m/%Y")
    st.caption(f"{start} → {end} · {region_label} · {cat_label}")

    if df_filtered.empty:
        st.warning("Aucune donnée pour les filtres sélectionnés.")
        return

    ca_total = df_filtered["ca"].sum()
    tx_total = df_filtered["transactions"].sum()
    marge_moy = df_filtered["marge_pct"].mean() * 100
    panier_moy = df_filtered["panier_moyen"].mean()

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("CA total", f"{ca_total/1e6:.2f} M€")
    c2.metric("Transactions", f"{tx_total:,.0f}")
    c3.metric("Marge moy.", f"{marge_moy:.1f}%")
    c4.metric("Panier moyen", f"{panier_moy:.1f} €")

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
