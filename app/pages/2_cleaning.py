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

st.set_page_config(page_title="Nettoyage & Déduplication", page_icon="🧹", layout="wide")

st.title("🧹 Nettoyage & Déduplication")

# Session state
if "project_data" not in st.session_state:
    st.session_state.project_data = None
if "clean_options" not in st.session_state:
    st.session_state.clean_options = get_default_cleaning_options()
if "dedup_threshold" not in st.session_state:
    st.session_state.dedup_threshold = 0.90

# Mock data pour démo (TODO: charger depuis DB)
if st.session_state.project_data is None:
    st.warning("⚠️ Aucun projet chargé. Retournez à l'étape d'import.")
    if st.button("← Retour à l'import"):
        st.switch_page("pages/1_import.py")
    st.stop()

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
