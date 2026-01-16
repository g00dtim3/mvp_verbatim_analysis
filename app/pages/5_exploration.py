"""
Page d'exploration des résultats et export.
"""

import streamlit as st
from pathlib import Path
import sys
import pandas as pd
import io

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

st.set_page_config(page_title="Exploration & Export", page_icon="📊", layout="wide")

st.title("📊 Exploration & Export")

# Mock data
mock_results = pd.DataFrame([
    {
        "Index": 1,
        "Verbatim": "Produit de très bonne qualité, livraison rapide et emballage soigné",
        "Thèmes": "Qualité du produit | Livraison rapide | Emballage",
        "GIDA_brand": "XYZ",
        "GIDA_pathology": "None"
    },
    {
        "Index": 2,
        "Verbatim": "Service client très réactif, problème résolu rapidement",
        "Thèmes": "Service client",
        "GIDA_brand": "XYZ",
        "GIDA_pathology": "None"
    },
    {
        "Index": 3,
        "Verbatim": "Prix un peu élevé mais le produit est durable",
        "Thèmes": "Prix | Qualité du produit",
        "GIDA_brand": "XYZ",
        "GIDA_pathology": "None"
    },
] * 50)  # Répéter pour avoir plus de données

# Filtres
st.header("🔍 Filtres")

col1, col2, col3 = st.columns(3)

with col1:
    theme_filter = st.multiselect(
        "Filtrer par thème",
        ["Qualité du produit", "Livraison rapide", "Emballage", "Service client", "Prix"],
        default=None
    )

with col2:
    brand_filter = st.multiselect(
        "Filtrer par marque GIDA",
        ["XYZ", "ABC", "DEF"],
        default=None
    )

with col3:
    search_text = st.text_input(
        "Recherche full-text",
        placeholder="Rechercher dans les verbatims..."
    )

# Dataset filtré
df_filtered = mock_results.copy()

if theme_filter:
    df_filtered = df_filtered[df_filtered["Thèmes"].str.contains("|".join(theme_filter), na=False)]

if search_text:
    df_filtered = df_filtered[df_filtered["Verbatim"].str.contains(search_text, case=False, na=False)]

# Métriques
st.header("📊 Statistiques")

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("Total verbatims", f"{len(mock_results):,}")

with col2:
    st.metric("Verbatims filtrés", f"{len(df_filtered):,}")

with col3:
    st.metric("Thèmes uniques", 25)

with col4:
    st.metric("Taux de couverture", "87%")

# Table explorable
st.header("📝 Verbatims enrichis")

# Highlighting simulé
def highlight_search(text, search):
    if search and search in text.lower():
        # Note: Streamlit dataframe ne supporte pas le HTML, on garde le texte brut
        return text
    return text

st.dataframe(
    df_filtered,
    use_container_width=True,
    height=400,
    column_config={
        "Verbatim": st.column_config.TextColumn("Verbatim", width="large"),
        "Thèmes": st.column_config.TextColumn("Thèmes", width="medium"),
    }
)

st.caption(f"Affichage de {len(df_filtered)} verbatims")

# Export
st.header("📤 Export des résultats")

col1, col2, col3 = st.columns(3)

with col1:
    # Export Excel
    if st.button("📊 Exporter en Excel", use_container_width=True):
        # Créer un buffer
        buffer = io.BytesIO()

        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            df_filtered.to_excel(writer, sheet_name='Verbatims', index=False)

        buffer.seek(0)

        st.download_button(
            label="⬇️ Télécharger Excel",
            data=buffer,
            file_name="resultats_analyse_verbatims.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )

with col2:
    # Export CSV
    if st.button("📄 Exporter en CSV", use_container_width=True):
        csv = df_filtered.to_csv(index=False).encode('utf-8')

        st.download_button(
            label="⬇️ Télécharger CSV",
            data=csv,
            file_name="resultats_analyse_verbatims.csv",
            mime="text/csv",
            use_container_width=True
        )

with col3:
    # Export Markdown
    if st.button("📋 Copier pour PowerPoint", use_container_width=True):
        markdown_table = """
| Thème | Volume | % |
|-------|--------|---|
| Qualité du produit | 234 | 15.2% |
| Livraison rapide | 189 | 12.3% |
| Emballage | 156 | 10.1% |
| Service client | 98 | 6.4% |
| Prix | 67 | 4.3% |
"""
        st.code(markdown_table, language="markdown")
        st.caption("Copiez ce tableau pour l'insérer dans PowerPoint")

# Synthèse thématique
st.header("📈 Synthèse Thématique")

synthesis_df = pd.DataFrame([
    {"Thème": "Qualité du produit", "Volume": 234, "% dataset": 15.2, "Pain Points": "Durabilité limitée", "Bénéfices": "Robustesse, bon rapport qualité/prix"},
    {"Thème": "Livraison rapide", "Volume": 189, "% dataset": 12.3, "Pain Points": "Délais variables", "Bénéfices": "Livraison express, ponctualité"},
    {"Thème": "Emballage", "Volume": 156, "% dataset": 10.1, "Pain Points": "Emballage excessif", "Bénéfices": "Protection, présentation soignée"},
    {"Thème": "Service client", "Volume": 98, "% dataset": 6.4, "Pain Points": "Temps de réponse", "Bénéfices": "Réactivité, résolution rapide"},
    {"Thème": "Prix", "Volume": 67, "% dataset": 4.3, "Pain Points": "Prix élevé", "Bénéfices": "Bon rapport qualité/prix"},
])

st.dataframe(synthesis_df, use_container_width=True, height=250)

# Footer
st.divider()
st.caption("MVP Analyse Verbatims v1.0 | Tous droits réservés")
