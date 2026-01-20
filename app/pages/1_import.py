"""
Page d'import de dataset.
"""

import streamlit as st
import pandas as pd
from pathlib import Path
import sys

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.utils.config import (
    settings, 
    BRANDWATCH_COLUMN_MAPPING, 
    SEMANTIWEB_COLUMN_MAPPING,
    CLEANING_OPTIONS
)

st.set_page_config(page_title="Import Dataset", page_icon="📁", layout="wide")

st.title("📁 Import Dataset")
st.markdown("Chargez votre fichier CSV Brandwatch ou Semantiweb")

# État de session
if "uploaded_df" not in st.session_state:
    st.session_state.uploaded_df = None
if "detected_source" not in st.session_state:
    st.session_state.detected_source = None
if "column_mapping" not in st.session_state:
    st.session_state.column_mapping = {}
if "uploaded_filename" not in st.session_state:
    st.session_state.uploaded_filename = None


def detect_source_type(columns: list) -> str:
    """Détecte le type de source basé sur les colonnes."""
    columns_lower = [c.lower() for c in columns]
    
    # Brandwatch
    brandwatch_indicators = ["full text", "page type", "query id"]
    if any(ind in " ".join(columns_lower) for ind in brandwatch_indicators):
        return "brandwatch"
    
    # Semantiweb
    semantiweb_indicators = ["review_text", "review_date", "review_id"]
    if any(ind in columns_lower for ind in semantiweb_indicators):
        return "semantiweb"
    
    return "generic_csv"


def get_auto_mapping(columns: list, source_type: str) -> dict:
    """Retourne le mapping automatique basé sur le type de source."""
    mapping = {}
    
    if source_type == "brandwatch":
        reference = BRANDWATCH_COLUMN_MAPPING
    elif source_type == "semantiweb":
        reference = SEMANTIWEB_COLUMN_MAPPING
    else:
        reference = {}
    
    for col in columns:
        for ref_col, target in reference.items():
            if col.lower() == ref_col.lower():
                mapping[col] = target
                break
    
    return mapping


# Upload
st.header("1️⃣ Upload du fichier")

uploaded_file = st.file_uploader(
    "Glissez-déposez votre fichier CSV",
    type=["csv"],
    help="Fichiers supportés: Brandwatch, Semantiweb, CSV générique"
)

if uploaded_file:
    # Charger le fichier
    try:
        df = pd.read_csv(uploaded_file, nrows=1000)  # Preview limité
        st.session_state.uploaded_df = df
        st.session_state.uploaded_filename = uploaded_file.name

        # Détecter le type
        source_type = detect_source_type(df.columns.tolist())
        st.session_state.detected_source = source_type

        # Auto-mapping
        st.session_state.column_mapping = get_auto_mapping(
            df.columns.tolist(),
            source_type
        )

        st.success(f"✅ Fichier chargé: {len(df)} lignes (preview), {len(df.columns)} colonnes")

    except Exception as e:
        st.error(f"❌ Erreur de chargement: {e}")

# Aperçu
if st.session_state.uploaded_df is not None:
    df = st.session_state.uploaded_df
    
    st.header("2️⃣ Aperçu du dataset")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Lignes (preview)", f"{len(df):,}")
    with col2:
        st.metric("Colonnes", len(df.columns))
    with col3:
        source_labels = {
            "brandwatch": "🟢 Brandwatch",
            "semantiweb": "🔵 Semantiweb",
            "generic_csv": "⚪ CSV Générique"
        }
        st.metric("Source détectée", source_labels.get(st.session_state.detected_source, "?"))
    
    # Table preview
    st.dataframe(df.head(30), use_container_width=True, height=300)
    
    # Mapping des colonnes
    st.header("3️⃣ Mapping des colonnes")
    
    st.info("Vérifiez et ajustez le mapping des colonnes si nécessaire.")
    
    target_fields = [
        ("full_text", "Texte du verbatim *", True),
        ("source_date", "Date", False),
        ("sentiment", "Sentiment", False),
        ("language", "Langue", False),
        ("page_type", "Type de page", False),
        ("category", "Catégorie", False),
        ("author", "Auteur", False),
        ("url", "URL", False),
        ("source_id", "ID source", False),
    ]
    
    col1, col2 = st.columns(2)
    
    mapping = {}
    columns_with_none = ["(non mappé)"] + df.columns.tolist()
    
    for i, (field_key, field_label, required) in enumerate(target_fields):
        col = col1 if i % 2 == 0 else col2
        
        with col:
            # Trouver la valeur par défaut
            default_idx = 0
            for mapped_col, target in st.session_state.column_mapping.items():
                if target == field_key and mapped_col in df.columns:
                    default_idx = columns_with_none.index(mapped_col)
                    break
            
            selected = st.selectbox(
                f"{field_label} {'🔴' if required else ''}",
                columns_with_none,
                index=default_idx,
                key=f"map_{field_key}"
            )
            
            if selected != "(non mappé)":
                mapping[field_key] = selected
    
    # Validation
    st.header("4️⃣ Validation")
    
    if "full_text" not in mapping:
        st.error("❌ Le champ 'Texte du verbatim' est obligatoire")
    else:
        # Résumé
        st.success("✅ Mapping valide")
        
        with st.expander("📋 Résumé du mapping"):
            for target, source in mapping.items():
                st.write(f"**{target}** ← {source}")
        
        # Nom du projet
        default_name = ""
        if st.session_state.uploaded_filename:
            default_name = st.session_state.uploaded_filename.replace(".csv", "")

        project_name = st.text_input(
            "Nom du projet",
            value=default_name,
            help="Nom pour identifier ce dataset"
        )
        
        # Bouton d'import
        if st.button("🚀 Importer le dataset", type="primary", use_container_width=True):
            with st.spinner("Import en cours..."):
                # TODO: Implémenter l'import réel en DB
                
                # Simulation
                import time
                time.sleep(2)
                
                st.success(f"✅ Dataset '{project_name}' importé avec succès!")
                st.balloons()
                
                # Redirection
                st.info("➡️ Passez à l'étape de nettoyage")
                if st.button("Continuer vers le nettoyage"):
                    st.switch_page("pages/2_cleaning.py")
