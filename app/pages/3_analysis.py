"""
Page d'analyse thématique LLM.
"""

import streamlit as st
from pathlib import Path
import sys

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.api.analysis_llm import estimate_analysis_cost, check_cost_alerts
from src.utils.config import settings

st.set_page_config(page_title="Analyse Thématique", page_icon="🔍", layout="wide")

st.title("🔍 Analyse Thématique par LLM")

# Session state
if "brief" not in st.session_state:
    st.session_state.brief = ""
if "analysis_mode" not in st.session_state:
    st.session_state.analysis_mode = "rapid"

# Brief contexte
st.header("1️⃣ Contexte de l'analyse")

st.markdown("""
Fournissez un contexte pour guider l'analyse du LLM.
Indiquez les objectifs, la marque, le produit, ou toute information pertinente.
""")

st.session_state.brief = st.text_area(
    "Brief d'analyse",
    value=st.session_state.brief,
    placeholder="Exemple: Analyse des avis consommateurs pour la marque XYZ, produit ABC. "
                "Focus sur la livraison, l'emballage et la qualité du produit.",
    height=150,
    help="Ce contexte sera utilisé par le LLM pour orienter l'extraction des thèmes"
)

# Mode d'analyse
st.header("2️⃣ Mode d'analyse")

col1, col2 = st.columns(2)

with col1:
    if st.button(
        "⚡ Mode Rapide (750 verbatims)",
        use_container_width=True,
        type="primary" if st.session_state.analysis_mode == "rapid" else "secondary"
    ):
        st.session_state.analysis_mode = "rapid"

    st.markdown("""
    **Mode Rapide**
    - Échantillon stratifié de 750 verbatims
    - Durée: ~1-2 minutes
    - Idéal pour cadrage rapide
    """)

with col2:
    if st.button(
        "📊 Mode Complet (tout le dataset)",
        use_container_width=True,
        type="primary" if st.session_state.analysis_mode == "full" else "secondary"
    ):
        st.session_state.analysis_mode = "full"

    st.markdown("""
    **Mode Complet**
    - Analyse 100% du dataset
    - Chunks de 200 verbatims
    - Couverture exhaustive
    """)

# Estimation du coût
st.header("3️⃣ Estimation")

# Mock data (TODO: charger depuis DB)
mock_verbatims = ["verbatim " + str(i) for i in range(5000)]

if st.button("📊 Calculer l'estimation"):
    with st.spinner("Calcul en cours..."):
        if st.session_state.analysis_mode == "rapid":
            # Échantillon de 750
            sample = mock_verbatims[:750]
        else:
            sample = mock_verbatims

        estimate = estimate_analysis_cost(
            verbatims=sample,
            brief=st.session_state.brief or "Analyse générale"
        )

        # Vérifier les alertes
        alert = check_cost_alerts(estimate['nb_chunks'])

        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric("Verbatims", f"{estimate['nb_verbatims']:,}")
        with col2:
            st.metric("Chunks", estimate['nb_chunks'])
        with col3:
            st.metric("Coût estimé", f"${estimate['estimated_cost_usd']:.2f}")
        with col4:
            mins = estimate['estimated_time_seconds'] // 60
            st.metric("Durée estimée", f"~{mins} min")

        # Alerte
        if alert['alert_level'] == 'blocking':
            st.error(alert['message'])
        elif alert['alert_level'] == 'warning':
            st.warning(alert['message'])
        else:
            st.success(alert['message'])

# Lancer l'analyse
st.header("4️⃣ Lancer l'analyse")

if not st.session_state.brief:
    st.warning("⚠️ Veuillez fournir un contexte d'analyse (brief)")
else:
    if st.button("🚀 Lancer l'analyse LLM", type="primary", use_container_width=True):
        with st.spinner("Analyse en cours... Cela peut prendre plusieurs minutes"):
            # TODO: Implémenter le pipeline LangGraph
            import time

            progress_bar = st.progress(0)
            status_text = st.empty()

            steps = [
                ("Création des chunks", 20),
                ("Analyse LLM par chunk", 60),
                ("Fusion des thèmes", 80),
                ("Génération de l'ontologie", 90),
                ("Quantification", 100)
            ]

            for step_name, progress in steps:
                status_text.text(f"⏳ {step_name}...")
                time.sleep(1)
                progress_bar.progress(progress)

            st.success("✅ Analyse terminée avec succès!")
            st.balloons()

            # Résumé
            st.info("""
            **Résultats:**
            - 25 thèmes identifiés
            - 3 chunks traités
            - Coût: $1.45
            """)

            if st.button("➡️ Voir les résultats"):
                st.switch_page("pages/5_exploration.py")
