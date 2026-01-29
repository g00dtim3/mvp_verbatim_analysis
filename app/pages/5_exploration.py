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

# Force redeploy - 2026-01-22

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
            AnalysisRun.total_verbatims,
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

        # Charger les thèmes de ce run et convertir en dictionnaires
        topics_raw = db.query(RunTopic).filter(
            RunTopic.run_id == uuid.UUID(selected_run_id)
        ).all()

        if not topics_raw:
            st.warning("Aucun thème trouvé pour cette analyse.")
            st.stop()

        # Convertir en liste de dictionnaires pour éviter DetachedInstanceError
        topics = []
        for t in topics_raw:
            topics.append({
                'id': t.id,
                'canonical_label': t.canonical_label,
                'pain_points': t.pain_points or [],
                'benefits': t.benefits or [],
                'volume_verbatims': t.volume_verbatims,
                'volume_mentions': t.volume_mentions,
                'pct_of_dataset': t.pct_of_dataset
            })

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
    # Calculer la proportion pain/benefit
    nb_pains = len(topic['pain_points']) if topic['pain_points'] else 0
    nb_benefits = len(topic['benefits']) if topic['benefits'] else 0
    total_sentiment = nb_pains + nb_benefits

    if total_sentiment > 0:
        pct_pain = (nb_pains / total_sentiment) * 100
        pct_benefit = (nb_benefits / total_sentiment) * 100
        sentiment_label = f"{pct_pain:.0f}% Pain / {pct_benefit:.0f}% Bénéfice"
    else:
        sentiment_label = "Neutre"

    topics_data.append({
        'Thème': topic['canonical_label'],
        'Sentiment': sentiment_label,
        'Volume': topic['volume_verbatims'],
        '% Dataset': f"{topic['pct_of_dataset']:.1f}%",
        'Mentions': topic['volume_mentions']
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
    pain_count = sum(1 for t in topics if t['pain_points'] and len(t['pain_points']) > 0)
    st.metric("Topics avec pains", pain_count)

with col3:
    benefit_count = sum(1 for t in topics if t['benefits'] and len(t['benefits']) > 0)
    st.metric("Topics avec bénéfices", benefit_count)

with col4:
    total_volume = sum(t['volume_verbatims'] for t in topics)
    coverage = (total_volume / selected_run.total_verbatims * 100) if selected_run.total_verbatims > 0 else 0
    st.metric("Couverture", f"{coverage:.1f}%")

# Explorer les verbatims
st.divider()
st.header("🔎 Explorer les verbatims")

# Filtre par thème
topic_options = ["Tous les verbatims"] + [t['canonical_label'] for t in topics]
selected_topic_filter = st.selectbox(
    "Filtrer par thème",
    options=topic_options,
    help="Sélectionnez un thème pour voir uniquement les verbatims correspondants"
)

try:
    with get_db() as db:
        # Charger les verbatims du projet
        from src.db.models import ProjectVerbatim

        verbatims_raw = db.query(ProjectVerbatim).join(
            AnalysisRun, ProjectVerbatim.project_id == AnalysisRun.project_id
        ).filter(
            AnalysisRun.id == uuid.UUID(selected_run_id)
        ).all()

        # Convertir en dictionnaires pour éviter DetachedInstanceError
        verbatims_list = []
        for v in verbatims_raw:
            verbatims_list.append({
                'id': v.id,
                'full_text': v.full_text,
                'created_at': v.created_at,
                'is_duplicate': v.is_duplicate
            })

        # Charger les ontologies pour le highlighting
        ontologies_map = {}
        ontologies_raw = db.query(
            ProjectOntology,
            RunTopic.id,
            RunTopic.canonical_label
        ).join(
            RunTopic, ProjectOntology.topic_id == RunTopic.id
        ).filter(
            ProjectOntology.run_id == uuid.UUID(selected_run_id)
        ).all()

        for onto, topic_id, topic_label in ontologies_raw:
            ontologies_map[topic_label] = {
                'keywords': onto.keywords or [],
                'negative_keywords': onto.negative_keywords or [],
                'regex_patterns': onto.regex_patterns or []
            }

    # Fonction pour highlighter les keywords
    def highlight_keywords(text, keywords):
        """Met en surbrillance les keywords dans le texte."""
        if not text:
            return ""

        highlighted = text
        for kw in keywords:
            # Simple replacement case-insensitive
            import re
            pattern = re.compile(re.escape(kw), re.IGNORECASE)
            highlighted = pattern.sub(lambda m: f"**{m.group()}**", highlighted)

        return highlighted

    # Filtrer et afficher
    if selected_topic_filter == "Tous les verbatims":
        verbatims_to_show = verbatims_list[:50]  # Limit pour performance
        st.caption(f"Affichage des 50 premiers verbatims sur {len(verbatims_list)} au total")
        keywords_to_highlight = []
    else:
        # Filtrer par thème en utilisant quantification
        from src.api.quantification import match_keywords_in_text

        ontology = ontologies_map.get(selected_topic_filter, {})
        keywords = ontology.get('keywords', [])
        negative_keywords = ontology.get('negative_keywords', [])

        matched_verbatims = []
        for v in verbatims_list:
            matched = match_keywords_in_text(
                text=v['full_text'],
                keywords=keywords,
                negative_keywords=negative_keywords
            )
            if matched:
                matched_verbatims.append(v)

        verbatims_to_show = matched_verbatims[:50]
        keywords_to_highlight = keywords
        st.caption(f"Affichage de {len(verbatims_to_show)} verbatims matchant '{selected_topic_filter}' (max 50)")

    # Afficher les verbatims
    if verbatims_to_show:
        for i, verbatim in enumerate(verbatims_to_show, 1):
            text_to_display = verbatim['full_text']

            # Highlighter les keywords si un thème est sélectionné
            if keywords_to_highlight:
                text_to_display = highlight_keywords(text_to_display, keywords_to_highlight[:5])

            with st.expander(f"Verbatim #{i}: {text_to_display[:80]}...", expanded=False):
                st.markdown(text_to_display)

                # Afficher métadonnées si disponibles
                col1, col2 = st.columns(2)
                with col1:
                    if verbatim['created_at']:
                        st.caption(f"📅 {verbatim['created_at'].strftime('%Y-%m-%d')}")
                with col2:
                    if verbatim['is_duplicate']:
                        st.caption("⚠️ Doublon détecté")
    else:
        st.info("Aucun verbatim trouvé pour ce filtre")

except Exception as e:
    st.error(f"Erreur lors du chargement des verbatims: {str(e)}")
    import traceback
    with st.expander("Détails de l'erreur"):
        st.code(traceback.format_exc())

# Ontologies des thèmes
st.divider()
st.header("🔍 Ontologies générées")

st.markdown("Keywords et patterns générés par le LLM pour chaque thème:")

with get_db() as db:
    # Charger les ontologies avec les labels des topics
    ontologies_raw = db.query(
        ProjectOntology,
        RunTopic.canonical_label
    ).join(
        RunTopic, ProjectOntology.topic_id == RunTopic.id
    ).filter(
        ProjectOntology.run_id == uuid.UUID(selected_run_id)
    ).all()

    # Convertir en liste de dictionnaires et décoder Unicode
    def decode_unicode_string(s):
        """Décode les séquences Unicode échappées dans une chaîne."""
        try:
            if isinstance(s, str) and '\\u' in s:
                return s.encode('utf-8').decode('unicode_escape')
            return s
        except (UnicodeDecodeError, AttributeError):
            return s

    ontologies = []
    for onto, label in ontologies_raw:
        ontologies.append({
            'label': label,
            'keywords': [decode_unicode_string(kw) for kw in (onto.keywords or [])],
            'regex_patterns': [decode_unicode_string(p) for p in (onto.regex_patterns or [])],
            'negative_keywords': [decode_unicode_string(kw) for kw in (onto.negative_keywords or [])]
        })

for onto in ontologies:
    with st.expander(f"**{onto['label']}**", expanded=False):
        col1, col2 = st.columns(2)

        with col1:
            st.markdown("**Keywords positifs:**")
            if onto['keywords']:
                for kw in onto['keywords'][:10]:  # Afficher max 10
                    st.markdown(f"- `{kw}`")
                if len(onto['keywords']) > 10:
                    st.caption(f"... et {len(onto['keywords']) - 10} autres")
            else:
                st.caption("Aucun")

        with col2:
            st.markdown("**Patterns regex:**")
            if onto['regex_patterns']:
                for pattern in onto['regex_patterns'][:5]:
                    st.code(pattern, language="regex")
            else:
                st.caption("Aucun")

        if onto['negative_keywords']:
            st.markdown("**Keywords négatifs:**")
            st.caption(", ".join(onto['negative_keywords'][:10]))

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
