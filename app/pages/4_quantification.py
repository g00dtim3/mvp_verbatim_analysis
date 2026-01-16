"""
Page de quantification et validation de l'ontologie.
"""

import streamlit as st
from pathlib import Path
import sys
import pandas as pd

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.utils.config import settings

st.set_page_config(page_title="Quantification", page_icon="📊", layout="wide")

st.title("📊 Quantification & Ontologie Projet")

# Session state
if "ontology_validated" not in st.session_state:
    st.session_state.ontology_validated = False

# Info GIDA
st.header("ℹ️ Information")

col1, col2 = st.columns([3, 1])

with col1:
    st.info(f"📚 Analyse réalisée avec **GIDA v{settings.gida_version}**")

with col2:
    st.metric("Thèmes détectés", 25)

# Ontologie projet
st.header("1️⃣ Ontologie Projet (optionnel)")

st.markdown("""
L'ontologie projet contient les keywords et regex générés par le LLM pour chaque thème.
Vous pouvez la valider et l'ajuster avant la quantification finale.
""")

validation_option = st.radio(
    "Que souhaitez-vous faire?",
    ["Skip (utiliser l'ontologie générée automatiquement)", "Valider et ajuster l'ontologie"],
    help="La validation est recommandée pour garantir la précision du comptage"
)

if validation_option.startswith("Valider"):
    st.warning("🔍 **Validation recommandée**")

    # Mock données
    themes_sample = [
        {
            "theme": "Livraison rapide",
            "keywords": ["livraison rapide", "livré rapidement", "livraison express", "délai court"],
            "negative_keywords": ["pas rapide", "trop lent"],
            "examples": 15
        },
        {
            "theme": "Emballage",
            "keywords": ["emballage", "packaging", "colis", "carton"],
            "negative_keywords": ["sans emballage"],
            "examples": 42
        },
        {
            "theme": "Qualité du produit",
            "keywords": ["qualité", "bien fait", "solide", "robuste", "durable"],
            "negative_keywords": ["mauvaise qualité", "pas de qualité"],
            "examples": 78
        }
    ]

    for theme_data in themes_sample:
        with st.expander(f"🏷️ {theme_data['theme']} ({theme_data['examples']} verbatims matchés)"):
            col1, col2 = st.columns(2)

            with col1:
                st.markdown("**Keywords:**")
                keywords_text = st.text_area(
                    "Keywords",
                    value="\n".join(theme_data['keywords']),
                    height=100,
                    key=f"kw_{theme_data['theme']}",
                    label_visibility="collapsed"
                )

            with col2:
                st.markdown("**Negative Keywords:**")
                neg_keywords_text = st.text_area(
                    "Negative Keywords",
                    value="\n".join(theme_data['negative_keywords']),
                    height=100,
                    key=f"neg_{theme_data['theme']}",
                    label_visibility="collapsed"
                )

    if st.button("✅ Valider l'ontologie", type="primary"):
        st.session_state.ontology_validated = True
        st.success("Ontologie validée!")
else:
    st.info("✓ L'ontologie générée automatiquement sera utilisée")
    st.session_state.ontology_validated = True

# Quantification
if st.session_state.ontology_validated:
    st.header("2️⃣ Lancer la quantification")

    st.markdown("""
    La quantification va compter de manière **déterministe** (Python) le nombre d'occurrences
    de chaque thème dans le dataset complet.
    """)

    st.markdown("**Métriques calculées:**")
    st.markdown("""
    - **volume_verbatims**: Nombre de verbatims contenant ≥ 1 match
    - **volume_mentions**: Nombre de keywords distincts détectés
    - **pct_of_dataset**: Pourcentage du dataset total
    """)

    if st.button("🚀 Lancer la quantification", type="primary", use_container_width=True):
        with st.spinner("Quantification en cours..."):
            import time
            time.sleep(2)

            st.success("✅ Quantification terminée!")

            # Résultats mock
            st.header("📈 Résultats")

            results_df = pd.DataFrame([
                {"Thème": "Qualité du produit", "Volume (verbatims)": 234, "Volume (mentions)": 12, "% dataset": 15.2},
                {"Thème": "Livraison rapide", "Volume (verbatims)": 189, "Volume (mentions)": 8, "% dataset": 12.3},
                {"Thème": "Emballage", "Volume (verbatims)": 156, "Volume (mentions)": 6, "% dataset": 10.1},
                {"Thème": "Service client", "Volume (verbatims)": 98, "Volume (mentions)": 5, "% dataset": 6.4},
                {"Thème": "Prix", "Volume (verbatims)": 67, "Volume (mentions)": 4, "% dataset": 4.3},
            ])

            st.dataframe(results_df, use_container_width=True)

            # Navigation
            st.info("➡️ Explorez les résultats détaillés")
            if st.button("Continuer vers l'exploration"):
                st.switch_page("pages/5_exploration.py")
