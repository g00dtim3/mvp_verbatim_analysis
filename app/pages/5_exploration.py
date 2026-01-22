"""
Page d'exploration des résultats et export.
"""

import streamlit as st
from pathlib import Path
import sys
import pandas as pd
import io
import uuid

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.db.connection import get_db
from src.db.models import Project, ProjectVerbatim, AnalysisRun, RunTopic, ProjectOntology
from sqlalchemy import func, desc

st.set_page_config(page_title="Exploration & Export", page_icon="📊", layout="wide")

st.title("📊 Exploration & Export")

# Session state
if "current_run_id" not in st.session_state:
    st.session_state.current_run_id = None

# Sélection du run d'analyse
st.header("📁 Sélection de l'analyse")

try:
    with get_db() as db:
        # Charger tous les runs d'analyse (success uniquement)
        runs = db.query(
            AnalysisRun.id,
            AnalysisRun.brief,
            AnalysisRun.mode,
            AnalysisRun.total_themes,
            AnalysisRun.total_verbatims,
            AnalysisRun.created_at,
            Project.name.label('project_name')
        ).join(
            Project, AnalysisRun.project_id == Project.id
        ).filter(
            AnalysisRun.status == 'success'
        ).order_by(
            desc(AnalysisRun.created_at)
        ).all()

        if not runs:
            st.warning("⚠️ Aucune analyse terminée. Commencez par lancer une analyse.")
            if st.button("← Aller à l'analyse"):
                st.switch_page("pages/3_analysis.py")
            st.stop()

        # Options pour le selectbox
        run_options = {
            str(r.id): f"{r.project_name} - {r.brief[:50]}... ({r.total_themes} thèmes, {r.created_at.strftime('%Y-%m-%d %H:%M')})"
            for r in runs
        }

        # Sélecteur
        selected_run_id = st.selectbox(
            "Choisir une analyse",
            options=list(run_options.keys()),
            format_func=lambda x: run_options[x],
            index=list(run_options.keys()).index(st.session_state.current_run_id)
            if st.session_state.current_run_id in run_options
            else 0,
            key="run_selector"
        )

        # Mettre à jour la session
        if selected_run_id != st.session_state.current_run_id:
            st.session_state.current_run_id = selected_run_id

        # Afficher les infos du run sélectionné
        selected_run = next(r for r in runs if str(r.id) == selected_run_id)

        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Projet", selected_run.project_name)
        with col2:
            st.metric("Thèmes identifiés", selected_run.total_themes)
        with col3:
            st.metric("Verbatims analysés", f"{selected_run.total_verbatims:,}")
        with col4:
            st.metric("Mode", "⚡ Rapide" if selected_run.mode == 'rapid' else "📊 Complet")

        st.divider()

        # Charger les thèmes de ce run
        topics = db.query(RunTopic).filter(
            RunTopic.run_id == uuid.UUID(selected_run_id)
        ).all()

        if not topics:
            st.warning("Aucun thème trouvé pour cette analyse.")
            st.stop()

except Exception as e:
    st.error(f"Erreur lors du chargement des analyses: {str(e)}")
    import traceback
    with st.expander("Détails de l'erreur"):
        st.code(traceback.format_exc())
    st.stop()

# Résumé des thèmes
st.header("📊 Synthèse des thèmes")

# Créer un DataFrame avec les thèmes
topics_data = []
for topic in topics:
    topics_data.append({
        'Thème': topic.canonical_label,
        'Type': '😢 Pain' if topic.pain_or_benefit == 'pain' else '😊 Bénéfice' if topic.pain_or_benefit == 'benefit' else '⚪ Neutre',
        'Volume': topic.volume_verbatims,
        '% Dataset': f"{topic.pct_of_dataset:.1f}%",
        'Mentions': topic.volume_mentions
    })

df_topics = pd.DataFrame(topics_data)
df_topics = df_topics.sort_values('Volume', ascending=False)

st.dataframe(
    df_topics,
    use_container_width=True,
    hide_index=True
)

# Statistiques globales
st.divider()
st.header("📈 Statistiques")

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("Total thèmes", len(topics))

with col2:
    pain_count = sum(1 for t in topics if t.pain_or_benefit == 'pain')
    st.metric("Pain points", pain_count)

with col3:
    benefit_count = sum(1 for t in topics if t.pain_or_benefit == 'benefit')
    st.metric("Bénéfices", benefit_count)

with col4:
    total_volume = sum(t.volume_verbatims for t in topics)
    coverage = (total_volume / selected_run.total_verbatims * 100) if selected_run.total_verbatims > 0 else 0
    st.metric("Couverture", f"{coverage:.1f}%")

# Ontologies des thèmes
st.divider()
st.header("🔍 Ontologies générées")

st.markdown("Keywords et patterns générés par le LLM pour chaque thème:")

with get_db() as db:
    # Charger les ontologies
    ontologies = db.query(ProjectOntology).filter(
        ProjectOntology.run_id == uuid.UUID(selected_run_id)
    ).all()

    for onto in ontologies:
        with st.expander(f"**{onto.label}**", expanded=False):
            col1, col2 = st.columns(2)

            with col1:
                st.markdown("**Keywords positifs:**")
                if onto.keywords:
                    for kw in onto.keywords[:10]:  # Afficher max 10
                        st.markdown(f"- `{kw}`")
                    if len(onto.keywords) > 10:
                        st.caption(f"... et {len(onto.keywords) - 10} autres")
                else:
                    st.caption("Aucun")

            with col2:
                st.markdown("**Patterns regex:**")
                if onto.regex_patterns:
                    for pattern in onto.regex_patterns[:5]:
                        st.code(pattern, language="regex")
                else:
                    st.caption("Aucun")

            if onto.negative_keywords:
                st.markdown("**Keywords négatifs:**")
                st.caption(", ".join(onto.negative_keywords[:10]))

# Export
st.divider()
st.header("📤 Export des résultats")

col1, col2 = st.columns(2)

with col1:
    # Export Excel
    if st.button("📊 Exporter en Excel", use_container_width=True):
        # Créer un buffer
        buffer = io.BytesIO()

        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            df_topics.to_excel(writer, sheet_name='Synthèse Thèmes', index=False)

        buffer.seek(0)

        st.download_button(
            label="⬇️ Télécharger Excel",
            data=buffer,
            file_name=f"analyse_themes_{selected_run.project_name}_{selected_run.created_at.strftime('%Y%m%d')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )

with col2:
    # Export CSV
    if st.button("📄 Exporter en CSV", use_container_width=True):
        csv = df_topics.to_csv(index=False).encode('utf-8')

        st.download_button(
            label="⬇️ Télécharger CSV",
            data=csv,
            file_name=f"analyse_themes_{selected_run.project_name}_{selected_run.created_at.strftime('%Y%m%d')}.csv",
            mime="text/csv",
            use_container_width=True
        )

# Footer
st.divider()
st.caption(f"MVP Analyse Verbatims v1.0 | Analyse du {selected_run.created_at.strftime('%Y-%m-%d %H:%M')}")
