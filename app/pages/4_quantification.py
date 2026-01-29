"""
Page de quantification et validation de l'ontologie.
"""

import streamlit as st
from pathlib import Path
import sys
import pandas as pd
import uuid

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.utils.config import settings
from src.db.connection import get_db
from src.db.models import AnalysisRun, RunTopic, ProjectOntology, Project
from sqlalchemy import func, desc

st.set_page_config(page_title="Quantification", page_icon="📊", layout="wide")

st.title("📊 Quantification & Ontologie Projet")

# Info
st.info("""
ℹ️ **Note**: La quantification est automatiquement effectuée lors de l'analyse LLM.
Cette page vous permet de visualiser et ajuster les ontologies générées.
""")

# Sélection d'une analyse
st.header("📁 Sélection de l'analyse")

try:
    with get_db() as db:
        # Charger toutes les analyses terminées
        runs = db.query(
            AnalysisRun.id,
            AnalysisRun.brief,
            AnalysisRun.created_at,
            Project.name.label('project_name'),
            func.count(RunTopic.id).label('total_themes')
        ).join(
            Project, AnalysisRun.project_id == Project.id
        ).outerjoin(
            RunTopic, AnalysisRun.id == RunTopic.run_id
        ).filter(
            AnalysisRun.status == 'success'
        ).group_by(
            AnalysisRun.id, Project.name
        ).order_by(
            desc(AnalysisRun.created_at)
        ).all()

        if not runs:
            st.warning("⚠️ Aucune analyse terminée. Lancez d'abord une analyse.")
            if st.button("← Aller à l'analyse"):
                st.switch_page("pages/3_analysis.py")
            st.stop()

        # Sélecteur
        run_options = {
            str(r.id): f"{r.project_name} - {r.brief[:50]}... ({r.total_themes} thèmes, {r.created_at.strftime('%Y-%m-%d %H:%M')})"
            for r in runs
        }

        selected_run_id = st.selectbox(
            "Choisir une analyse",
            options=list(run_options.keys()),
            format_func=lambda x: run_options[x]
        )

        # Afficher les infos
        selected_run = next(r for r in runs if str(r.id) == selected_run_id)

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Projet", selected_run.project_name)
        with col2:
            st.metric("Thèmes quantifiés", selected_run.total_themes)
        with col3:
            st.metric("GIDA Version", f"v{settings.gida_version}")

except Exception as e:
    st.error(f"Erreur lors du chargement: {str(e)}")
    st.stop()

st.divider()

# Charger les ontologies et les résultats de quantification
st.header("1️⃣ Ontologies & Résultats de quantification")

st.markdown("""
Les ontologies contiennent les keywords et regex générés par le LLM pour chaque thème.
La quantification a déjà été effectuée automatiquement lors de l'analyse.
""")

try:
    with get_db() as db:
        # Charger les topics avec leurs ontologies
        topics_with_ontologies = db.query(
            RunTopic,
            ProjectOntology
        ).join(
            ProjectOntology, RunTopic.id == ProjectOntology.topic_id
        ).filter(
            RunTopic.run_id == uuid.UUID(selected_run_id)
        ).all()

        if not topics_with_ontologies:
            st.warning("Aucune ontologie trouvée pour cette analyse.")
            st.stop()

        # Afficher les résultats de quantification
        st.subheader("📊 Résultats de la quantification")

        results_data = []
        for topic, _ in topics_with_ontologies:
            results_data.append({
                "Thème": topic.canonical_label,
                "Volume (verbatims)": topic.volume_verbatims,
                "Volume (mentions)": topic.volume_mentions,
                "% dataset": topic.pct_of_dataset
            })

        results_df = pd.DataFrame(results_data)
        results_df = results_df.sort_values("Volume (verbatims)", ascending=False)

        st.dataframe(results_df, use_container_width=True, hide_index=True)

        # Visualiser/éditer les ontologies
        st.divider()
        st.subheader("🔍 Ontologies générées")

        st.markdown("Cliquez sur un thème pour voir et ajuster son ontologie:")

        for topic, ontology in topics_with_ontologies:
            with st.expander(
                f"🏷️ {topic.canonical_label} ({topic.volume_verbatims} verbatims matchés, {topic.pct_of_dataset:.1f}%)"
            ):
                col1, col2 = st.columns(2)

                with col1:
                    st.markdown("**Keywords positifs:**")
                    keywords = ontology.keywords or []
                    if keywords:
                        keywords_text = st.text_area(
                            "Keywords",
                            value="\n".join(keywords),
                            height=150,
                            key=f"kw_{topic.id}",
                            label_visibility="collapsed",
                            help="Un keyword par ligne"
                        )
                    else:
                        st.caption("Aucun keyword défini")

                with col2:
                    st.markdown("**Keywords négatifs:**")
                    neg_keywords = ontology.negative_keywords or []
                    if neg_keywords:
                        neg_keywords_text = st.text_area(
                            "Negative Keywords",
                            value="\n".join(neg_keywords),
                            height=150,
                            key=f"neg_{topic.id}",
                            label_visibility="collapsed",
                            help="Un keyword négatif par ligne"
                        )
                    else:
                        st.caption("Aucun keyword négatif")

                # Regex patterns
                regex_patterns = ontology.regex_patterns or []
                if regex_patterns:
                    st.markdown("**Patterns regex:**")
                    for pattern in regex_patterns[:5]:
                        st.code(pattern, language="regex")
                    if len(regex_patterns) > 5:
                        st.caption(f"... et {len(regex_patterns) - 5} autres patterns")

                # Pain points et benefits
                col3, col4 = st.columns(2)
                with col3:
                    if topic.pain_points:
                        st.markdown("**Pain points:**")
                        for pp in topic.pain_points[:3]:
                            st.caption(f"• {pp}")
                        if len(topic.pain_points) > 3:
                            st.caption(f"... et {len(topic.pain_points) - 3} autres")

                with col4:
                    if topic.benefits:
                        st.markdown("**Bénéfices:**")
                        for b in topic.benefits[:3]:
                            st.caption(f"• {b}")
                        if len(topic.benefits) > 3:
                            st.caption(f"... et {len(topic.benefits) - 3} autres")

        # Note sur la sauvegarde
        st.info("""
        💡 **Note**: Les modifications d'ontologies nécessiteraient une re-quantification pour être prises en compte.
        Cette fonctionnalité sera disponible dans une version future.
        """)

except Exception as e:
    st.error(f"Erreur lors du chargement des ontologies: {str(e)}")
    import traceback
    with st.expander("Détails de l'erreur"):
        st.code(traceback.format_exc())

# Navigation
st.divider()
st.info("➡️ Pour explorer les résultats en détail, utilisez la page d'exploration")
if st.button("Continuer vers l'exploration", use_container_width=True):
    # Stocker l'ID du run dans la session pour la page exploration
    st.session_state.current_run_id = selected_run_id
    st.switch_page("pages/5_exploration.py")
