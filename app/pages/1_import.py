"""
Page d'import de dataset.
"""

import streamlit as st
import pandas as pd
from pathlib import Path
import sys
import uuid
from datetime import datetime

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.utils.config import (
    settings,
    BRANDWATCH_COLUMN_MAPPING,
    SEMANTIWEB_COLUMN_MAPPING,
    CLEANING_OPTIONS
)
from src.db.connection import get_db
from src.db.models import Project, ProjectVerbatim

st.set_page_config(page_title="Import Dataset", page_icon="📁", layout="wide")

st.title("📁 Import Dataset")
st.markdown("Chargez votre fichier CSV Brandwatch ou Semantiweb")

# État de session
if "uploaded_df" not in st.session_state:
    st.session_state.uploaded_df = None
if "uploaded_df_full" not in st.session_state:
    st.session_state.uploaded_df_full = None
if "detected_source" not in st.session_state:
    st.session_state.detected_source = None
if "column_mapping" not in st.session_state:
    st.session_state.column_mapping = {}
if "uploaded_filename" not in st.session_state:
    st.session_state.uploaded_filename = None
if "current_project_id" not in st.session_state:
    st.session_state.current_project_id = None
if "current_project_name" not in st.session_state:
    st.session_state.current_project_name = None


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
        # Charger tout le fichier pour l'import
        df_full = pd.read_csv(uploaded_file)
        st.session_state.uploaded_df_full = df_full

        # Charger preview limité pour l'affichage
        uploaded_file.seek(0)  # Revenir au début du fichier
        df_preview = pd.read_csv(uploaded_file, nrows=1000)
        st.session_state.uploaded_df = df_preview
        st.session_state.uploaded_filename = uploaded_file.name

        # Détecter le type (sur le preview)
        source_type = detect_source_type(df_preview.columns.tolist())
        st.session_state.detected_source = source_type

        # Auto-mapping
        st.session_state.column_mapping = get_auto_mapping(
            df_preview.columns.tolist(),
            source_type
        )

        st.success(f"✅ Fichier chargé: {len(df_full):,} lignes totales, {len(df_preview.columns)} colonnes (preview: {len(df_preview)} lignes)")

    except Exception as e:
        st.error(f"❌ Erreur de chargement: {e}")

# Aperçu
if st.session_state.uploaded_df is not None:
    df = st.session_state.uploaded_df
    
    st.header("2️⃣ Aperçu du dataset")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        total_rows = len(st.session_state.uploaded_df_full) if st.session_state.uploaded_df_full is not None else len(df)
        st.metric("Lignes totales", f"{total_rows:,}")
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
        ("subcategory", "Sous Catégorie", False),
        ("brand", "Marque", False),
        ("product", "Produit", False),
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
            if not project_name or project_name.strip() == "":
                st.error("❌ Le nom du projet est obligatoire")
            else:
                with st.spinner("Import en cours..."):
                    try:
                        # Utiliser le DataFrame complet (pas juste le preview)
                        df_to_import = st.session_state.uploaded_df_full
                        if df_to_import is None:
                            st.error("❌ Erreur: fichier non chargé")
                            st.stop()

                        # Appliquer le mapping aux colonnes
                        mapping_dict = {}
                        for target_field, _, _ in target_fields:
                            source_col = mapping.get(target_field)
                            if source_col and source_col != "(Non mappé)":
                                mapping_dict[source_col] = target_field

                        # Renommer les colonnes selon le mapping
                        df_mapped = df_to_import.rename(columns=mapping_dict)

                        # Parser les dates si présentes
                        if 'source_date' in df_mapped.columns:
                            df_mapped['source_date'] = pd.to_datetime(
                                df_mapped['source_date'],
                                errors='coerce'
                            )

                        # Créer le projet en DB
                        with get_db() as db:
                            project = Project(
                                name=project_name.strip(),
                                description=f"Import depuis {st.session_state.uploaded_filename}",
                                source_type=st.session_state.detected_source,
                                metadata_={
                                    'original_filename': st.session_state.uploaded_filename,
                                    'original_rows': len(df_mapped),
                                    'original_columns': list(df_to_import.columns.tolist()),
                                    'column_mapping': mapping_dict,
                                    'imported_at': datetime.now().isoformat()
                                }
                            )
                            db.add(project)
                            db.flush()

                            # Insérer les verbatims
                            verbatims = []
                            for idx, row in df_mapped.iterrows():
                                # Préparer extra_data avec les champs supplémentaires
                                extra_data = {}

                                # Ajouter les nouveaux champs mappables dans extra_data
                                if pd.notna(row.get('brand')):
                                    extra_data['brand'] = str(row.get('brand'))
                                if pd.notna(row.get('product')):
                                    extra_data['product'] = str(row.get('product'))
                                if pd.notna(row.get('subcategory')):
                                    extra_data['subcategory'] = str(row.get('subcategory'))

                                # Ajouter tous les autres champs non mappés
                                for k, v in row.items():
                                    if k not in [
                                        'full_text', 'source_id', 'source_date', 'sentiment',
                                        'language', 'page_type', 'category', 'author', 'url',
                                        'brand', 'product', 'subcategory'
                                    ] and pd.notna(v):
                                        extra_data[k] = str(v)

                                verbatim = ProjectVerbatim(
                                    project_id=project.id,
                                    full_text=str(row.get('full_text', '')),
                                    source_id=str(row.get('source_id', '')) if pd.notna(row.get('source_id')) else None,
                                    source_date=row.get('source_date') if pd.notna(row.get('source_date')) else None,
                                    sentiment=str(row.get('sentiment', '')) if pd.notna(row.get('sentiment')) else None,
                                    language=str(row.get('language', '')) if pd.notna(row.get('language')) else None,
                                    page_type=str(row.get('page_type', '')) if pd.notna(row.get('page_type')) else None,
                                    category=str(row.get('category', '')) if pd.notna(row.get('category')) else None,
                                    author=str(row.get('author', '')) if pd.notna(row.get('author')) else None,
                                    url=str(row.get('url', '')) if pd.notna(row.get('url')) else None,
                                    extra_data=extra_data
                                )
                                verbatims.append(verbatim)

                            db.bulk_save_objects(verbatims)
                            db.commit()

                            # Stocker l'ID du projet dans session state
                            st.session_state.current_project_id = str(project.id)
                            st.session_state.current_project_name = project_name

                        st.success(f"✅ Dataset '{project_name}' importé avec succès! {len(verbatims)} verbatims insérés.")
                        st.balloons()

                        # Redirection
                        st.info("➡️ Passez à l'étape de nettoyage")

                    except Exception as e:
                        st.error(f"❌ Erreur lors de l'import: {str(e)}")
                        import traceback
                        with st.expander("Détails de l'erreur"):
                            st.code(traceback.format_exc())
