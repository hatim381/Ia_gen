"""Page Vue Globale — KPIs YoY (via repository) + narration LLM (via service Axe 2)."""
from __future__ import annotations
import pandas as pd
import plotly.express as px
import streamlit as st

from core.data import repository as repo


@st.cache_resource
def _narration_service():
    from features.insights_narration.service import NarrationService
    return NarrationService()


def _kpi_card(col, label, value, delta, positive):
    color = "#2ECC71" if positive else "#E74C3C"
    col.markdown(f"""<div style="background:#1E1E2E;border-radius:12px;padding:20px 24px;border-left:4px solid {color}">
<p style="color:#888;font-size:13px;margin:0">{label}</p>
<p style="font-size:28px;font-weight:700;margin:4px 0">{value}</p>
<p style="color:{color};font-size:13px;margin:0">{delta}</p></div>""", unsafe_allow_html=True)


def _filter_banner():
    default_start, default_end = pd.Timestamp("2024-01-01"), pd.Timestamp("2025-12-31")
    active = []
    if st.session_state.get("filter_region"): active.append(f"Région **{st.session_state.filter_region}**")
    if st.session_state.get("filter_categorie"): active.append(f"Catégorie **{st.session_state.filter_categorie}**")
    s = st.session_state.get("filter_date_start", default_start); e = st.session_state.get("filter_date_end", default_end)
    if s != default_start or e != default_end: active.append(f"{s:%d/%m/%Y} → {e:%d/%m/%Y}")
    if active:
        st.info("Filtres actifs : " + " · ".join(active) +
                "  \n→ Cette page affiche la vue globale. Allez sur **Performance** pour les données filtrées.")


def _render_narrative(kpis: dict):
    import html
    auto = st.session_state.get("narrate_requested", False)
    if auto: st.session_state.narrate_requested = False
    col, _ = st.columns([2, 5])
    if col.button("🤖 Générer la synthèse", use_container_width=True) or auto:
        with st.spinner("Génération de la synthèse en cours…"):
            try:
                st.session_state.narrative_text = _narration_service().generate(kpis)
            except Exception as exc:
                st.session_state.narrative_text = ""; st.warning(f"Erreur narration : {exc}")
    if st.session_state.get("narrative_text"):
        from core import config
        st.markdown(f"""<div style="background:#1E1E2E;border-radius:12px;padding:16px 24px;border-left:4px solid #4F8BF9;margin-bottom:8px">
<p style="color:#888;font-size:12px;margin:0 0 8px 0">Synthèse générée par {config.OLLAMA_MODEL}</p>
<p style="margin:0;line-height:1.6">{html.escape(st.session_state.narrative_text)}</p></div>""",
                    unsafe_allow_html=True)


def render(df_all: pd.DataFrame, df_filtered: pd.DataFrame):
    st.title("Vue Globale")
    st.caption("Données retail — toutes régions et catégories (2024–2025)")
    _filter_banner()

    k = repo.compute_kpis(df_all)
    st.markdown("### KPIs 2025 vs 2024")
    c1, c2, c3, c4 = st.columns(4)
    _kpi_card(c1, "CA 2025", f"{k.ca_2025/1e6:.1f} M€", f"{k.ca_delta_pct:+.1f}% vs 2024", k.ca_delta_pct >= 0)
    _kpi_card(c2, "Transactions", f"{df_all[df_all['date'].dt.year==2025]['transactions'].sum():,.0f}",
              f"{k.tx_delta_pct:+.1f}% vs 2024", k.tx_delta_pct >= 0)
    _kpi_card(c3, "Marge moy.", f"{k.marge_2025:.1f}%", f"{k.marge_delta_pts:+.2f} pts vs 2024", k.marge_delta_pts >= 0)
    _kpi_card(c4, "Panier moyen", f"—", f"{k.panier_delta_pct:+.1f}% vs 2024", k.panier_delta_pct >= 0)
    st.markdown("<br>", unsafe_allow_html=True)
    _render_narrative(k.as_dict())

    monthly = (df_all.groupby(df_all["date"].dt.to_period("M").dt.to_timestamp())["ca"].sum()
               .reset_index().rename(columns={"date": "mois"}))
    fig = px.line(monthly, x="mois", y="ca", title="Chiffre d'Affaires mensuel (2024–2025)",
                  labels={"mois": "", "ca": "CA (€)"}, color_discrete_sequence=["#4F8BF9"])
    fig.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                      yaxis=dict(tickformat=",.0f"), hovermode="x unified")
    fig.add_vline(x=pd.Timestamp("2025-01-01").timestamp() * 1000, line_dash="dash",
                  line_color="#888", annotation_text="2025", annotation_position="top right")
    st.plotly_chart(fig, use_container_width=True)

    cl, cr = st.columns(2)
    for col, dim, scale, title in ((cl, "categorie", "Blues", "CA par catégorie (total)"),
                                   (cr, "region", "Teal", "CA par région (total)")):
        perf = df_all.groupby(dim)["ca"].sum().sort_values().reset_index()
        f = px.bar(perf, x="ca", y=dim, orientation="h", title=title,
                   labels={"ca": "CA (€)", dim: ""}, color="ca", color_continuous_scale=scale)
        f.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", coloraxis_showscale=False)
        col.plotly_chart(f, use_container_width=True)
