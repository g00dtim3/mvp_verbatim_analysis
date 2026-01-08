"""
MVP Analyse Verbatims - Application Streamlit
Point d'entrée principal
"""

import streamlit as st
from pathlib import Path
import sys

# Ajouter le répertoire src au path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.utils.config import settings
from src.db.connection import test_connection as test_db, get_db_info
from src.llm.client import test_connection as test_llm

# Configuration de la page
st.set_page_config(
    page_title="Analyse Verbatims",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# CSS custom
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1F4E79;
        margin-bottom: 0.5rem;
    }
    .sub-header {
        font-size: 1.2rem;
        color: #666;
        margin-bottom: 2rem;
    }
    .status-ok {
        color: #28a745;
        font-weight: bold;
    }
    .status-error {
        color: #dc3545;
        font-weight: bold;
    }
    .metric-card {
        background-color: #f8f9fa;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #1F4E79;
    }
</style>
""", unsafe_allow_html=True)


def main():
    """Page d'accueil principale."""
    
    # Header
    st.markdown('<p class="main-header">📊 Analyse Verbatims</p>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">Outil d\'analyse quali/quanti pour Social Data & Reviews</p>', unsafe_allow_html=True)
    
    # Sidebar
    with st.sidebar:
        st.header("🔧 Configuration")
        
        # Status des connexions
        st.subheader("État du système")
        
        # Test DB
        with st.spinner("Test connexion DB..."):
            db_ok = test_db()
        if db_ok:
            st.success("✅ Base de données connectée")
        else:
            st.error("❌ Base de données non connectée")
        
        # Test OpenAI
        with st.spinner("Test connexion OpenAI..."):
            llm_ok = test_llm()
        if llm_ok:
            st.success("✅ OpenAI API connectée")
        else:
            st.error("❌ OpenAI API non connectée")
        
        st.divider()
        
        # Infos
        st.subheader("ℹ️ Informations")
        st.caption(f"GIDA Version: {settings.gida_version}")
        st.caption(f"Modèle LLM: {settings.openai_model}")
        st.caption(f"Max verbatims: {settings.max_verbatims:,}")
    
    # Contenu principal
    st.header("🚀 Démarrage rapide")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("""
        <div class="metric-card">
            <h3>1️⃣ Import</h3>
            <p>Chargez votre fichier CSV Brandwatch ou Semantiweb</p>
        </div>
        """, unsafe_allow_html=True)
        if st.button("📁 Importer un dataset", use_container_width=True):
            st.switch_page("pages/1_import.py")
    
    with col2:
        st.markdown("""
        <div class="metric-card">
            <h3>2️⃣ Analyse</h3>
            <p>Lancez l'analyse thématique par LLM</p>
        </div>
        """, unsafe_allow_html=True)
        if st.button("🔍 Analyser", use_container_width=True):
            st.switch_page("pages/3_analysis.py")
    
    with col3:
        st.markdown("""
        <div class="metric-card">
            <h3>3️⃣ Export</h3>
            <p>Explorez et exportez vos résultats</p>
        </div>
        """, unsafe_allow_html=True)
        if st.button("📊 Explorer", use_container_width=True):
            st.switch_page("pages/5_exploration.py")
    
    st.divider()
    
    # Projets récents
    st.header("📂 Projets récents")
    
    # TODO: Charger depuis la DB
    st.info("Aucun projet récent. Commencez par importer un dataset.")
    
    # Workflow
    st.header("📋 Workflow d'analyse")
    
    st.markdown("""
    | Étape | Description | Durée estimée |
    |-------|-------------|---------------|
    | **Import** | Upload CSV + mapping automatique | ~1 min |
    | **Nettoyage** | Options configurables + déduplication | ~2 min |
    | **Analyse LLM** | Mode Rapide (750) ou Complet | 1-30 min |
    | **Quantification** | Comptage Python déterministe | ~2 min |
    | **Export** | Excel, CSV, Markdown | Instantané |
    """)
    
    st.divider()
    
    # Footer
    st.caption("MVP Analyse Verbatims v1.0 | Développé avec ❤️")


if __name__ == "__main__":
    main()
