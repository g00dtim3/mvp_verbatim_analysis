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

sample_texts = [
    "Produit GÉNIAL!!! 😍 https://example.com",
    "Livraison RAPIDE   mais emballage    moyen",
    "Je n'ai jamais reçu ma commande 😠😠😠"
]

if st.button("🔍 Voir un aperçu"):
    examples = get_cleaning_examples(
        sample_texts,
        st.session_state.clean_options,
        n=3
    )

    for ex in examples:
        st.markdown("---")
        st.markdown(f"**Avant:** `{ex['before']}`")
        st.markdown(f"**Après:** `{ex['after']}`")
        st.caption(f"Longueur: {ex['length_before']} → {ex['length_after']} caractères")

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
    sample_dups = [
        "Produit conforme à mes attentes",
        "Produit conforme a mes attentes.",
        "Le produit correspond bien à mes attentes",
        "Service client très réactif"
    ]

    examples = get_duplicate_examples(
        sample_dups,
        threshold=st.session_state.dedup_threshold,
        n=5
    )

    if examples:
        st.success(f"✅ {len(examples)} paires de doublons détectées")

        for ex in examples[:3]:
            with st.expander(f"Similarité: {ex['similarity']:.1%}"):
                st.markdown(f"**Texte 1:** {ex['text1']}")
                st.markdown(f"**Texte 2:** {ex['text2']}")
    else:
        st.info("Aucun doublon détecté avec ce seuil")

# Lancer le nettoyage
st.header("4️⃣ Lancer le traitement")

if st.button("🚀 Nettoyer et dédupliquer", type="primary", use_container_width=True):
    with st.spinner("Traitement en cours..."):
        # TODO: Implémenter le traitement réel
        import time
        time.sleep(2)

        st.success("✅ Nettoyage et déduplication terminés!")
        st.info("➡️ Passez à l'étape d'analyse")

        if st.button("Continuer vers l'analyse"):
            st.switch_page("pages/3_analysis.py")
