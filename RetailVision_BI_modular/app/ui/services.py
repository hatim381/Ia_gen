"""Instance partagee du service Q&A — une seule source de verite pour tout l'UI."""
import streamlit as st


@st.cache_resource
def get_qa_service():
    from features.analytics_qa.service import AnalyticsQAService
    return AnalyticsQAService()
