import pandas as pd
import plotly.express as px
import streamlit as st


def _kpi_card(col, label: str, value: str, delta: str, delta_positive: bool) -> None:
    color = "#2ECC71" if delta_positive else "#E74C3C"
    col.markdown(
        f"""
        <div style="background:#1E1E2E;border-radius:12px;padding:20px 24px;border-left:4px solid {color}">
            <p style="color:#888;font-size:13px;margin:0">{label}</p>
            <p style="font-size:28px;font-weight:700;margin:4px 0">{value}</p>
            <p style="color:{color};font-size:13px;margin:0">{delta}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _filter_banner() -> None:
    """Affiche une bannière si des filtres non-défaut sont actifs."""
    default_start = pd.Timestamp("2024-01-01")
    default_end = pd.Timestamp("2025-12-31")
    active = []
    if st.session_state.get("filter_region"):
        active.append(f"Région **{st.session_state.filter_region}**")
    if st.session_state.get("filter_categorie"):
        active.append(f"Catégorie **{st.session_state.filter_categorie}**")
    start = st.session_state.get("filter_date_start", default_start)
    end = st.session_state.get("filter_date_end", default_end)
    if start != default_start or end != default_end:
        active.append(f"{start.strftime('%d/%m/%Y')} → {end.strftime('%d/%m/%Y')}")
    if active:
        st.info(
            "Filtres actifs : " + " · ".join(active)
            + "  \n→ Cette page affiche toujours la vue globale. Allez sur **Performance** pour les données filtrées."
        )


def _render_narrative(kpis: dict) -> None:
    """Section narration LLM : bouton + affichage du paragraphe de synthèse."""
    from stt.narrator import generate_narrative
    from stt.intent_parser import OLLAMA_MODEL

    auto_trigger = st.session_state.get("stt_narrate", False)
    if auto_trigger:
        st.session_state.stt_narrate = False

    col_btn, _ = st.columns([2, 5])
    generate = col_btn.button("🤖 Générer la synthèse", use_container_width=True)

    if generate or auto_trigger:
        with st.spinner("Génération de la synthèse en cours…"):
            try:
                narrative = generate_narrative(kpis)
                st.session_state.narrative_text = narrative
            except Exception as exc:
                st.session_state.narrative_text = ""
                st.warning(f"Erreur narration : {exc}")

    if st.session_state.get("narrative_text"):
        st.markdown(
            f"""<div style="background:#1E1E2E;border-radius:12px;padding:16px 24px;border-left:4px solid #4F8BF9;margin-bottom:8px">
<p style="color:#888;font-size:12px;margin:0 0 8px 0">Synthèse générée par {OLLAMA_MODEL}</p>
<p style="margin:0;line-height:1.6">{st.session_state.narrative_text}</p>
</div>""",
            unsafe_allow_html=True,
        )


def render(df_all: pd.DataFrame, df_filtered: pd.DataFrame) -> None:
    st.title("Vue Globale")
    st.caption("Données retail — toutes régions et catégories confondues (2024–2025)")

    _filter_banner()

    year_2024 = df_all[df_all["date"].dt.year == 2024]
    year_2025 = df_all[df_all["date"].dt.year == 2025]

    ca_2024 = year_2024["ca"].sum()
    ca_2025 = year_2025["ca"].sum()
    ca_delta = (ca_2025 - ca_2024) / ca_2024 * 100

    tx_2024 = year_2024["transactions"].sum()
    tx_2025 = year_2025["transactions"].sum()
    tx_delta = (tx_2025 - tx_2024) / tx_2024 * 100

    marge_2024 = year_2024["marge_pct"].mean() * 100
    marge_2025 = year_2025["marge_pct"].mean() * 100
    marge_delta = marge_2025 - marge_2024

    panier_2024 = year_2024["panier_moyen"].mean()
    panier_2025 = year_2025["panier_moyen"].mean()
    panier_delta = (panier_2025 - panier_2024) / panier_2024 * 100

    top_region = year_2025.groupby("region")["ca"].sum().idxmax()
    top_categorie = year_2025.groupby("categorie")["ca"].sum().idxmax()

    st.markdown("### KPIs 2025 vs 2024")
    c1, c2, c3, c4 = st.columns(4)
    _kpi_card(c1, "CA 2025", f"{ca_2025/1e6:.1f} M€", f"{ca_delta:+.1f}% vs 2024", ca_delta >= 0)
    _kpi_card(c2, "Transactions", f"{tx_2025:,.0f}", f"{tx_delta:+.1f}% vs 2024", tx_delta >= 0)
    _kpi_card(c3, "Marge moy.", f"{marge_2025:.1f}%", f"{marge_delta:+.2f} pts vs 2024", marge_delta >= 0)
    _kpi_card(c4, "Panier moyen", f"{panier_2025:.1f} €", f"{panier_delta:+.1f}% vs 2024", panier_delta >= 0)

    st.markdown("<br>", unsafe_allow_html=True)

    kpis = {
        "ca_2025": ca_2025,
        "ca_delta_pct": ca_delta,
        "tx_delta_pct": tx_delta,
        "marge_2025": marge_2025,
        "marge_delta_pts": marge_delta,
        "panier_delta_pct": panier_delta,
        "top_region": top_region,
        "top_categorie": top_categorie,
    }
    _render_narrative(kpis)

    monthly = (
        df_all.groupby([df_all["date"].dt.to_period("M").dt.to_timestamp(), "date"])
        .agg(ca=("ca", "sum"))
        .reset_index(level=1, drop=True)
        .groupby(level=0)
        .sum()
        .reset_index()
        .rename(columns={"date": "mois"})
    )

    fig_line = px.line(
        monthly,
        x="mois",
        y="ca",
        title="Chiffre d'Affaires mensuel (2024–2025)",
        labels={"mois": "", "ca": "CA (€)"},
        color_discrete_sequence=["#4F8BF9"],
    )
    fig_line.update_layout(
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        yaxis=dict(tickformat=",.0f"),
        hovermode="x unified",
    )
    # Plotly 6.x exige un timestamp en ms pour add_vline sur axe datetime
    fig_line.add_vline(
        x=pd.Timestamp("2025-01-01").timestamp() * 1000,
        line_dash="dash",
        line_color="#888",
        annotation_text="2025",
        annotation_position="top right",
    )
    st.plotly_chart(fig_line, use_container_width=True)

    col_left, col_right = st.columns(2)

    with col_left:
        cat_perf = (
            df_all.groupby("categorie")["ca"]
            .sum()
            .sort_values(ascending=True)
            .reset_index()
        )
        fig_cat = px.bar(
            cat_perf,
            x="ca",
            y="categorie",
            orientation="h",
            title="CA par catégorie (total)",
            labels={"ca": "CA (€)", "categorie": ""},
            color="ca",
            color_continuous_scale="Blues",
        )
        fig_cat.update_layout(
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            coloraxis_showscale=False,
        )
        st.plotly_chart(fig_cat, use_container_width=True)

    with col_right:
        reg_perf = (
            df_all.groupby("region")["ca"]
            .sum()
            .sort_values(ascending=True)
            .reset_index()
        )
        fig_reg = px.bar(
            reg_perf,
            x="ca",
            y="region",
            orientation="h",
            title="CA par région (total)",
            labels={"ca": "CA (€)", "region": ""},
            color="ca",
            color_continuous_scale="Teal",
        )
        fig_reg.update_layout(
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            coloraxis_showscale=False,
        )
        st.plotly_chart(fig_reg, use_container_width=True)
