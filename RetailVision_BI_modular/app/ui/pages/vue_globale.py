"""Page Vue Globale — KPIs YoY (via repository) + narration LLM (via service Axe 2)."""
from __future__ import annotations
import pandas as pd
import plotly.express as px
import streamlit as st

from ui.components import tts

from core.data import repository as repo


@st.cache_resource
def _narration_service():
    from features.insights_narration.service import NarrationService
    return NarrationService()


def _kpi_card(col, label, icon, value, delta, positive):
    color = "#2ECC71" if positive else "#E74C3C"
    arrow = "↑" if positive else "↓"
    col.markdown(f"""<div style="background:linear-gradient(135deg,#1E1E2E 0%,#252540 100%);border-radius:14px;padding:20px 22px;border-left:4px solid {color};box-shadow:0 4px 20px rgba(0,0,0,0.25);margin-bottom:4px">
<div style="display:flex;align-items:center;gap:8px;margin-bottom:8px">
  <span style="font-size:20px;line-height:1">{icon}</span>
  <p style="color:#9CA3AF;font-size:10px;margin:0;text-transform:uppercase;letter-spacing:1px;font-weight:700">{label}</p>
</div>
<p style="font-size:27px;font-weight:800;margin:0 0 6px 0;letter-spacing:-0.5px">{value}</p>
<p style="color:{color};font-size:12px;margin:0;font-weight:500">{arrow} {delta}</p>
</div>""", unsafe_allow_html=True)


def _filter_banner():
    default_start, default_end = pd.Timestamp("2024-01-01"), pd.Timestamp("2025-12-31")
    active = []
    if st.session_state.get("filter_region"): active.append(f"**{st.session_state.filter_region}**")
    if st.session_state.get("filter_categorie"): active.append(f"**{st.session_state.filter_categorie}**")
    s = st.session_state.get("filter_date_start", default_start); e = st.session_state.get("filter_date_end", default_end)
    if s != default_start or e != default_end: active.append(f"{s:%d/%m/%Y} → {e:%d/%m/%Y}")
    if active:
        st.info(
            "🔍 Filtres actifs : " + " · ".join(active) +
            "  \n→ Cette vue reste globale. Consultez **Performance** ou **Régions** pour les données filtrées.",
            icon="ℹ️",
        )


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
        tts.read_button(st.session_state.narrative_text, key="read_vue_globale")
        from core import config
        st.markdown(
            f"""<div style="background:linear-gradient(135deg,#1E1E2E 0%,#1a2040 100%);border-radius:12px;padding:16px 22px;border-left:4px solid #4F8BF9;margin-bottom:10px;box-shadow:0 2px 12px rgba(0,0,0,0.2)">
<p style="color:#9CA3AF;font-size:10px;text-transform:uppercase;letter-spacing:0.8px;font-weight:700;margin:0 0 8px 0">Synthèse IA — {config.OLLAMA_MODEL}</p>
<p style="margin:0;line-height:1.7;font-size:14px">{html.escape(st.session_state.narrative_text)}</p></div>""",
            unsafe_allow_html=True,
        )


def render(df_all: pd.DataFrame, df_filtered: pd.DataFrame):
    st.title("Vue Globale")
    st.caption("Données retail — toutes régions et catégories (2024–2025)")
    _filter_banner()

    k = repo.compute_kpis(df_all)
    st.markdown("### KPIs 2025 vs 2024")
    c1, c2, c3, c4 = st.columns(4)
    panier_2025 = df_all[df_all["date"].dt.year == 2025]["panier_moyen"].mean()
    _kpi_card(c1, "CA 2025", "💰", f"{k.ca_2025/1e6:.1f} M€", f"{k.ca_delta_pct:+.1f}% vs 2024", k.ca_delta_pct >= 0)
    _kpi_card(c2, "Transactions", "📦", f"{df_all[df_all['date'].dt.year==2025]['transactions'].sum():,.0f}",
              f"{k.tx_delta_pct:+.1f}% vs 2024", k.tx_delta_pct >= 0)
    _kpi_card(c3, "Marge moy.", "📊", f"{k.marge_2025:.1f}%", f"{k.marge_delta_pts:+.2f} pts vs 2024", k.marge_delta_pts >= 0)
    _kpi_card(c4, "Panier moyen", "🛒", f"{panier_2025:.2f} €", f"{k.panier_delta_pct:+.1f}% vs 2024", k.panier_delta_pct >= 0)
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
