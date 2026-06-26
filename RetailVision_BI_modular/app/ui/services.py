"""Instance partagee du service Q&A — une seule source de verite pour tout l'UI."""
import streamlit as st


@st.cache_resource
def get_qa_service():
    from features.analytics_qa.service import AnalyticsQAService
    service = AnalyticsQAService()
    # Precharge le modele en RAM des le 1er acces (evite le cold start ~100 s sur la 1ere question).
    service.llm.warmup()
    return service
