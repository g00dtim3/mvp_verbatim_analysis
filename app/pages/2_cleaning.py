"""
Page de nettoyage et déduplication des verbatims.
"""

import streamlit as st
import pandas as pd
from pathlib import Path
import sys

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.api.cleaning import get_default_cleaning_options, get_cleaning_examples, clean_verbatims
from src.api.deduplication import get_duplicate_examples
from src.utils.config import CLEANING_OPTIONS
from src.db.connection import get_db
from src.db.models import Project, ProjectVerbatim
from sqlalchemy import func, desc

st.set_page_config(page_title="Nettoyage & Déduplication", page_icon="🧹", layout="wide")

st.title("🧹 Nettoyage & Déduplication")

# Session state
if "current_project_id" not in st.session_state:
    st.session_state.current_project_id = None
if "current_project_name" not in st.session_state:
    st.session_state.current_project_name = None
if "clean_options" not in st.session_state:
    st.session_state.clean_options = get_default_cleaning_options()
if "dedup_threshold" not in st.session_state:
    st.session_state.dedup_threshold = 0.90

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
            "Choisir un projet",
            options=list(project_options.keys()),
            format_func=lambda x: project_options[x],
            index=list(project_options.keys()).index(st.session_state.current_project_id)
            if st.session_state.current_project_id in project_options
            else 0,
            key="project_selector"
        )

        # Mettre à jour la session
        if selected_project_id != st.session_state.current_project_id:
            st.session_state.current_project_id = selected_project_id
            st.session_state.current_project_name = next(
                p.name for p in projects if str(p.id) == selected_project_id
            )
            st.rerun()

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
    if st.button("← Retour à l'import"):
        st.switch_page("pages/1_import.py")
    st.stop()

st.divider()

# Options de nettoyage
st.header("1️⃣ Options de nettoyage")

st.markdown("Sélectionnez les opérations à appliquer:")

cols = st.columns(2)

for i, (key, label) in enumerate(CLEANING_OPTIONS.items()):
    col = cols[i % 2]
    with col:
        st.session_state.clean_options[key] = st.checkbox(
            label,
            value=st.session_state.clean_options.get(key, True),
            key=f"clean_{key}"
        )

# Preview du nettoyage
st.header("2️⃣ Aperçu du nettoyage")

if st.button("🔍 Voir un aperçu"):
    try:
        with get_db() as db:
            # Charger un échantillon de vraies données du projet
            sample_verbatims = db.query(ProjectVerbatim.full_text).filter(
                ProjectVerbatim.project_id == selected_project_id
            ).limit(5).all()

            sample_texts = [v.full_text for v in sample_verbatims if v.full_text]

        if not sample_texts:
            st.warning("Aucun verbatim trouvé dans ce projet")
        else:
            examples = get_cleaning_examples(
                sample_texts,
                st.session_state.clean_options,
                n=len(sample_texts)
            )

            for ex in examples:
                st.markdown("---")
                st.markdown(f"**Avant:** `{ex['before']}`")
                st.markdown(f"**Après:** `{ex['after']}`")
                st.caption(f"Longueur: {ex['length_before']} → {ex['length_after']} caractères")

    except Exception as e:
        st.error(f"Erreur lors du chargement de l'aperçu: {str(e)}")

# Déduplication
st.header("3️⃣ Déduplication")

st.markdown("Détectez et retirez les verbatims similaires:")

st.session_state.dedup_threshold = st.slider(
    "Seuil de similarité (fuzzy matching)",
    min_value=0.80,
    max_value=0.95,
    value=0.90,
    step=0.01,
    help="Plus le seuil est élevé, plus les textes doivent être similaires pour être considérés comme doublons"
)

st.caption(f"Seuil actuel: **{st.session_state.dedup_threshold:.2f}**")

# Preview doublons
if st.button("🔍 Détecter les doublons potentiels"):
    try:
        with st.spinner("Recherche de doublons..."):
            with get_db() as db:
                # Charger un échantillon pour la détection rapide
                sample_verbatims = db.query(ProjectVerbatim.full_text).filter(
                    ProjectVerbatim.project_id == selected_project_id
                ).limit(100).all()

                sample_texts = [v.full_text for v in sample_verbatims if v.full_text]

            if not sample_texts:
                st.warning("Aucun verbatim trouvé dans ce projet")
            else:
                examples = get_duplicate_examples(
                    sample_texts,
                    threshold=st.session_state.dedup_threshold,
                    n=10
                )

                if examples:
                    st.success(f"✅ {len(examples)} paires de doublons détectées (sur échantillon de {len(sample_texts)} verbatims)")

                    for ex in examples[:5]:
                        with st.expander(f"Similarité: {ex['similarity']:.1%}"):
                            st.markdown(f"**Texte 1:** {ex['text1']}")
                            st.markdown(f"**Texte 2:** {ex['text2']}")
                else:
                    st.info("Aucun doublon détecté avec ce seuil")

    except Exception as e:
        st.error(f"Erreur lors de la détection: {str(e)}")

# Lancer le nettoyage
st.header("4️⃣ Lancer le traitement")

if st.button("🚀 Nettoyer et dédupliquer", type="primary", use_container_width=True):
    try:
        with st.spinner("Chargement des verbatims..."):
            with get_db() as db:
                # Charger tous les verbatims du projet
                verbatims = db.query(ProjectVerbatim).filter(
                    ProjectVerbatim.project_id == selected_project_id
                ).all()

                if not verbatims:
                    st.error("Aucun verbatim trouvé dans ce projet")
                    st.stop()

                # Extraire les textes
                original_texts = [v.full_text for v in verbatims]

        # Étape 1: Nettoyage
        with st.spinner(f"Nettoyage de {len(original_texts)} verbatims..."):
            cleaned_texts = clean_verbatims(
                original_texts,
                st.session_state.clean_options
            )

        # Étape 2: Déduplication
        with st.spinner("Déduplication en cours..."):
            from src.api.deduplication import deduplicate_texts

            texts_unique, indices_kept, dedup_stats = deduplicate_texts(
                cleaned_texts,
                threshold=st.session_state.dedup_threshold
            )

        # Étape 3: Sauvegarde dans la base
        with st.spinner("Sauvegarde dans la base de données..."):
            with get_db() as db:
                # Sauvegarder le texte nettoyé pour tous les verbatims
                for i, verbatim in enumerate(verbatims):
                    verbatim.full_text_clean = cleaned_texts[i]
                    verbatim.dedup_flag = i not in indices_kept

                db.commit()

        # Afficher les résultats
        st.success("✅ Nettoyage et déduplication terminés!")

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Verbatims nettoyés", len(cleaned_texts))
        with col2:
            st.metric("Doublons détectés", dedup_stats['removed'])
        with col3:
            st.metric("Verbatims uniques", dedup_stats['total_after'])

        st.info("➡️ Les données sont prêtes pour l'analyse. Passez à l'étape suivante!")

        if st.button("Continuer vers l'analyse"):
            st.switch_page("pages/3_analysis.py")

    except Exception as e:
        st.error(f"❌ Erreur lors du traitement: {str(e)}")
        import traceback
        with st.expander("Détails de l'erreur"):
            st.code(traceback.format_exc())
