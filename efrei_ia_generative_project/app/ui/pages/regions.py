# Page Régions (portee dans ui/pages lors du refactor modulaire).
import pandas as pd
import plotly.express as px
import streamlit as st


def render(df_all: pd.DataFrame, df_filtered: pd.DataFrame) -> None:
    st.title("Régions")
    start = st.session_state.filter_date_start.strftime("%d/%m/%Y")
    end = st.session_state.filter_date_end.strftime("%d/%m/%Y")
    cat_label = st.session_state.filter_categorie or "toutes catégories"
    st.caption(f"{start} → {end} · {cat_label}")

    if df_filtered.empty:
        st.warning("Aucune donnée pour les filtres sélectionnés.")
        return

    reg_agg = (
        df_filtered.groupby("region")
        .agg(
            ca=("ca", "sum"),
            transactions=("transactions", "sum"),
            marge_pct=("marge_pct", "mean"),
        )
        .reset_index()
        .sort_values("ca", ascending=False)
    )
    reg_agg["marge_pct_pct"] = reg_agg["marge_pct"] * 100

    col_left, col_right = st.columns(2)

    with col_left:
        fig_bar = px.bar(
            reg_agg.sort_values("ca"),
            x="ca",
            y="region",
            orientation="h",
            title="CA par région",
            labels={"ca": "CA (€)", "region": ""},
            color="ca",
            color_continuous_scale="Blues",
            text_auto=".2s",
        )
        fig_bar.update_layout(
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            coloraxis_showscale=False,
        )
        st.plotly_chart(fig_bar, use_container_width=True)

    with col_right:
        fig_pie = px.pie(
            reg_agg,
            values="ca",
            names="region",
            title="Part de marché par région",
            color_discrete_sequence=px.colors.qualitative.Bold,
            hole=0.4,
        )
        fig_pie.update_layout(paper_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig_pie, use_container_width=True)

    treemap_data = (
        df_filtered.groupby(["region", "categorie"])["ca"].sum().reset_index()
    )
    fig_tree = px.treemap(
        treemap_data,
        path=["region", "categorie"],
        values="ca",
        title="Répartition CA — Région × Catégorie",
        color="ca",
        color_continuous_scale="Blues",
    )
    fig_tree.update_layout(paper_bgcolor="rgba(0,0,0,0)")
    st.plotly_chart(fig_tree, use_container_width=True)

    st.markdown("---")
    st.subheader("Comparatif régions")

    reg_monthly = (
        df_filtered.groupby(
            [df_filtered["date"].dt.to_period("M").dt.to_timestamp(), "region"]
        )["ca"]
        .sum()
        .reset_index()
        .rename(columns={"date": "mois"})
    )
    fig_lines = px.line(
        reg_monthly,
        x="mois",
        y="ca",
        color="region",
        title="Évolution mensuelle du CA par région",
        labels={"ca": "CA (€)", "mois": "", "region": "Région"},
        color_discrete_sequence=px.colors.qualitative.Bold,
    )
    fig_lines.update_layout(
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        hovermode="x unified",
    )
    st.plotly_chart(fig_lines, use_container_width=True)

    st.markdown("---")
    st.subheader("Tableau récapitulatif")
    display = reg_agg[["region", "ca", "transactions", "marge_pct_pct"]].copy()
    display.columns = ["Région", "CA (€)", "Transactions", "Marge moy. (%)"]
    display["CA (€)"] = display["CA (€)"].map("{:,.0f}".format)
    display["Transactions"] = display["Transactions"].map("{:,}".format)
    display["Marge moy. (%)"] = display["Marge moy. (%)"].map("{:.1f}".format)
    st.dataframe(display, hide_index=True, use_container_width=True)
