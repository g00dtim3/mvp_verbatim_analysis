"""
Page d'analyse thématique LLM.
"""

import streamlit as st
from pathlib import Path
import sys
import uuid
from datetime import datetime

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.api.analysis_llm import estimate_analysis_cost, check_cost_alerts
from src.api.sampling import stratified_sample
from src.utils.config import settings
from src.db.connection import get_db
from src.db.models import Project, ProjectVerbatim, AnalysisRun, RunTopic, ProjectOntology, AnalysisChunk, ChunkTopic
from src.llm.langgraph_pipeline import VerbatimAnalysisPipeline
from sqlalchemy import func, desc
import pandas as pd

st.set_page_config(page_title="Analyse Thématique", page_icon="🔍", layout="wide")

st.title("🔍 Analyse Thématique par LLM")

# Session state
if "current_project_id" not in st.session_state:
    st.session_state.current_project_id = None
if "current_project_name" not in st.session_state:
    st.session_state.current_project_name = None
if "brief" not in st.session_state:
    st.session_state.brief = ""
if "analysis_mode" not in st.session_state:
    st.session_state.analysis_mode = "rapid"

# Sélection du projet
st.header("📁 Sélection du projet")

try:
    with get_db() as db:
        # Charger tous les projets
        projects = db.query(
            Project.id,
            Project.name,
            Project.source_type,
            Project.created_at,
            func.count(ProjectVerbatim.id).label('verbatim_count')
        ).outerjoin(
            ProjectVerbatim, Project.id == ProjectVerbatim.project_id
        ).group_by(
            Project.id
        ).order_by(
            desc(Project.created_at)
        ).all()

        if not projects:
            st.warning("⚠️ Aucun projet trouvé. Commencez par importer un dataset.")
            if st.button("← Aller à l'import"):
                st.switch_page("pages/1_import.py")
            st.stop()

        # Options pour le selectbox
        project_options = {
            str(p.id): f"{p.name} ({p.verbatim_count:,} verbatims - {p.created_at.strftime('%Y-%m-%d')})"
            for p in projects
        }

        # Sélecteur
        selected_project_id = st.selectbox(
            "Choisir un projet à analyser",
            options=list(project_options.keys()),
            format_func=lambda x: project_options[x],
            index=list(project_options.keys()).index(st.session_state.current_project_id)
            if st.session_state.current_project_id in project_options
            else 0,
            key="project_selector_analysis"
        )

        # Mettre à jour la session
        if selected_project_id != st.session_state.current_project_id:
            st.session_state.current_project_id = selected_project_id
            st.session_state.current_project_name = next(
                p.name for p in projects if str(p.id) == selected_project_id
            )

        # Afficher les infos du projet sélectionné
        selected_project = next(p for p in projects if str(p.id) == selected_project_id)

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Verbatims", f"{selected_project.verbatim_count:,}")
        with col2:
            st.metric("Source", selected_project.source_type)
        with col3:
            st.metric("Date import", selected_project.created_at.strftime('%Y-%m-%d'))

except Exception as e:
    st.error(f"Erreur lors du chargement des projets: {str(e)}")
    if st.button("← Retour à l'accueil"):
        st.switch_page("app.py")
    st.stop()

st.divider()

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

if st.button("📊 Calculer l'estimation"):
    with st.spinner("Calcul en cours..."):
        try:
            with get_db() as db:
                # Charger les verbatims depuis la DB
                verbatims_query = db.query(ProjectVerbatim.full_text).filter(
                    ProjectVerbatim.project_id == uuid.UUID(st.session_state.current_project_id)
                ).all()

                all_verbatims = [v.full_text for v in verbatims_query if v.full_text]

                if st.session_state.analysis_mode == "rapid":
                    # Échantillon de 750
                    sample = all_verbatims[:min(750, len(all_verbatims))]
                else:
                    sample = all_verbatims

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

        except Exception as e:
            st.error(f"Erreur lors du calcul: {str(e)}")

# Lancer l'analyse
st.header("4️⃣ Lancer l'analyse")

if not st.session_state.brief:
    st.warning("⚠️ Veuillez fournir un contexte d'analyse (brief)")
else:
    if st.button("🚀 Lancer l'analyse LLM", type="primary", use_container_width=True):
        try:
            with st.spinner("Chargement des verbatims..."):
                with get_db() as db:
                    # Charger les verbatims
                    verbatims_query = db.query(ProjectVerbatim.full_text).filter(
                        ProjectVerbatim.project_id == uuid.UUID(st.session_state.current_project_id)
                    ).all()

                    all_verbatims = [v.full_text for v in verbatims_query if v.full_text]

                    if not all_verbatims:
                        st.error("Aucun verbatim trouvé dans ce projet")
                        st.stop()

                    # Appliquer sampling si mode rapide
                    if st.session_state.analysis_mode == "rapid":
                        df = pd.DataFrame({'full_text': all_verbatims})
                        df_sample, sample_info = stratified_sample(
                            df,
                            n_samples=min(750, len(all_verbatims))
                        )
                        verbatims_to_analyze = df_sample['full_text'].tolist()
                        st.info(f"📊 Mode rapide: {len(verbatims_to_analyze)} verbatims sélectionnés ({sample_info.get('strategy', 'stratified')})")
                    else:
                        verbatims_to_analyze = all_verbatims
                        st.info(f"📊 Mode complet: {len(verbatims_to_analyze)} verbatims")

            # Créer l'AnalysisRun dans la DB
            with st.spinner("Initialisation de l'analyse..."):
                with get_db() as db:
                    analysis_run = AnalysisRun(
                        project_id=uuid.UUID(st.session_state.current_project_id),
                        mode=st.session_state.analysis_mode,
                        brief=st.session_state.brief,
                        status='processing',
                        gida_version=settings.gida_version,
                        started_at=datetime.now()
                    )
                    db.add(analysis_run)
                    db.commit()
                    db.refresh(analysis_run)
                    run_id = analysis_run.id

            # Lancer le pipeline
            progress_bar = st.progress(0)
            status_text = st.empty()

            status_text.text("⏳ Initialisation du pipeline LangGraph...")
            pipeline = VerbatimAnalysisPipeline()
            progress_bar.progress(10)

            status_text.text("⏳ Analyse en cours... (cela peut prendre quelques minutes)")
            result = pipeline.run(
                verbatims=verbatims_to_analyze,
                brief=st.session_state.brief,
                mode=st.session_state.analysis_mode
            )
            progress_bar.progress(90)

            # Mettre à jour l'AnalysisRun et sauvegarder les résultats
            status_text.text("⏳ Sauvegarde des résultats...")
            with get_db() as db:
                run = db.query(AnalysisRun).filter(AnalysisRun.id == run_id).first()
                run.status = result['status']
                run.completed_at = datetime.now()
                run.total_verbatims = len(verbatims_to_analyze)
                run.total_chunks = result.get('stats', {}).get('nb_chunks', 0)
                run.chunks_success = result.get('stats', {}).get('chunks_success', 0)
                run.chunks_failed = result.get('stats', {}).get('chunks_failed', 0)

                # Sauvegarder les thèmes fusionnés avec quantification
                topics_quantified = result.get('topics_quantified', [])
                for item in topics_quantified:
                    # Extraire les données de la structure imbriquée
                    topic = item.get('topic', {})
                    ontology = item.get('ontology', {})
                    metrics = item.get('metrics', {})

                    # Créer le RunTopic avec les métriques de quantification
                    run_topic = RunTopic(
                        run_id=run_id,
                        canonical_label=topic.get('canonical_label', 'Unknown'),
                        aliases=topic.get('aliases', []),
                        pain_points=topic.get('pain_points', []),
                        benefits=topic.get('benefits', []),
                        merge_method=topic.get('merge_method', 'pass1_fuzzy'),
                        volume_verbatims=metrics.get('volume_verbatims', 0),
                        volume_mentions=metrics.get('volume_mentions', 0),
                        pct_of_dataset=metrics.get('pct_of_dataset', 0.0),
                        source_chunk_topic_ids=topic.get('source_chunk_topic_ids', [])
                    )
                    db.add(run_topic)
                    db.flush()  # Pour obtenir l'ID

                    # Créer le ProjectOntology pour ce topic
                    project_ontology = ProjectOntology(
                        run_id=run_id,
                        topic_id=run_topic.id,
                        keywords=ontology.get('keywords', []),
                        regex_patterns=ontology.get('regex_patterns', []),
                        negative_keywords=ontology.get('negative_keywords', []),
                        negation_patterns=ontology.get('negation_patterns', [])
                    )
                    db.add(project_ontology)

                db.commit()

            progress_bar.progress(100)
            status_text.text("✅ Analyse terminée!")

            st.success(f"✅ Analyse terminée avec succès!")
            st.balloons()

            # Résumé
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Thèmes identifiés", len(result.get('topics_quantified', [])))
            with col2:
                st.metric("Chunks traités", result.get('stats', {}).get('chunks_success', 0))
            with col3:
                st.metric("Verbatims analysés", len(verbatims_to_analyze))

            # Stocker l'ID du run dans la session
            st.session_state.current_run_id = str(run_id)

            if st.button("➡️ Voir les résultats"):
                st.switch_page("pages/5_exploration.py")

        except Exception as e:
            st.error(f"❌ Erreur lors de l'analyse: {str(e)}")
            import traceback
            with st.expander("Détails de l'erreur"):
                st.code(traceback.format_exc())

            # Marquer le run comme failed
            try:
                with get_db() as db:
                    if 'run_id' in locals():
                        run = db.query(AnalysisRun).filter(AnalysisRun.id == run_id).first()
                        if run:
                            run.status = 'failed'
                            run.completed_at = datetime.now()
                            db.commit()
            except:
                pass
