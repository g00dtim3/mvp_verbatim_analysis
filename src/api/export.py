"""
Module d'export des résultats (Excel, CSV, Markdown).
"""

import pandas as pd
from typing import List, Dict, Optional
from pathlib import Path
from loguru import logger
import json
from datetime import datetime


def export_to_excel(
    enriched_data: List[Dict],
    topics_quantified: List[Dict],
    output_path: str
) -> bool:
    """
    Exporte les résultats vers Excel avec plusieurs feuilles.

    Args:
        enriched_data: Dataset enrichi
        topics_quantified: Résultats de quantification
        output_path: Chemin du fichier de sortie

    Returns:
        True si succès
    """
    logger.info(f"Export Excel vers: {output_path}")

    try:
        # Créer le writer Excel
        with pd.ExcelWriter(output_path, engine='openpyxl') as writer:

            # Feuille 1: Verbatims enrichis
            df_verbatims = _create_verbatims_dataframe(enriched_data)
            df_verbatims.to_excel(writer, sheet_name='Verbatims', index=False)

            # Feuille 2: Synthèse thématique
            df_topics = _create_topics_dataframe(topics_quantified)
            df_topics.to_excel(writer, sheet_name='Synthèse Thématique', index=False)

            # Feuille 3: Top keywords par thème
            df_keywords = _create_keywords_dataframe(topics_quantified)
            df_keywords.to_excel(writer, sheet_name='Keywords', index=False)

        logger.info(f"✅ Export Excel réussi: {output_path}")
        return True

    except Exception as e:
        logger.error(f"❌ Erreur export Excel: {e}")
        return False


def _create_verbatims_dataframe(enriched_data: List[Dict]) -> pd.DataFrame:
    """
    Crée un DataFrame des verbatims enrichis.

    Args:
        enriched_data: Dataset enrichi

    Returns:
        DataFrame pandas
    """
    rows = []

    for item in enriched_data:
        row = {
            'Index': item.get('verbatim_index', ''),
            'Verbatim': item.get('full_text', ''),
            'Thèmes': ' | '.join(item.get('topics', [])),
        }

        # Ajouter les entités GIDA
        entities = item.get('entities', {})
        for entity_type, entity_values in entities.items():
            row[f'GIDA_{entity_type}'] = ' | '.join(entity_values)

        rows.append(row)

    return pd.DataFrame(rows)


def _create_topics_dataframe(topics_quantified: List[Dict]) -> pd.DataFrame:
    """
    Crée un DataFrame de synthèse thématique.

    Args:
        topics_quantified: Résultats de quantification

    Returns:
        DataFrame pandas
    """
    rows = []

    for item in topics_quantified:
        topic = item['topic']
        metrics = item['metrics']

        row = {
            'Thème': topic.get('canonical_label', ''),
            'Sous-thème': topic.get('canonical_subtopic', ''),
            'Alias': ' | '.join(topic.get('aliases', [])),
            'Volume (verbatims)': metrics['volume_verbatims'],
            'Volume (mentions)': metrics['volume_mentions'],
            '% du dataset': metrics['pct_of_dataset'],
            'Pain Points': ' | '.join(topic.get('pain_points', [])),
            'Bénéfices': ' | '.join(topic.get('benefits', [])),
            'Contexte': topic.get('usage_context', ''),
        }

        rows.append(row)

    df = pd.DataFrame(rows)

    # Trier par volume décroissant
    df = df.sort_values('Volume (verbatims)', ascending=False)

    return df


def _create_keywords_dataframe(topics_quantified: List[Dict]) -> pd.DataFrame:
    """
    Crée un DataFrame des keywords par thème.

    Args:
        topics_quantified: Résultats de quantification

    Returns:
        DataFrame pandas
    """
    rows = []

    for item in topics_quantified:
        topic = item['topic']
        ontology = item['ontology']
        metrics = item['metrics']

        topic_label = topic.get('canonical_label', '')

        # Keywords
        for kw in ontology.get('keywords', []):
            count = metrics['keyword_counts'].get(kw, 0)
            rows.append({
                'Thème': topic_label,
                'Type': 'Keyword',
                'Valeur': kw,
                'Occurrences': count
            })

        # Negative keywords
        for neg_kw in ontology.get('negative_keywords', []):
            rows.append({
                'Thème': topic_label,
                'Type': 'Negative Keyword',
                'Valeur': neg_kw,
                'Occurrences': 0
            })

    return pd.DataFrame(rows)


def export_to_csv(
    enriched_data: List[Dict],
    output_path: str
) -> bool:
    """
    Exporte les verbatims enrichis en CSV.

    Args:
        enriched_data: Dataset enrichi
        output_path: Chemin du fichier de sortie

    Returns:
        True si succès
    """
    logger.info(f"Export CSV vers: {output_path}")

    try:
        df = _create_verbatims_dataframe(enriched_data)
        df.to_csv(output_path, index=False, encoding='utf-8')

        logger.info(f"✅ Export CSV réussi: {output_path}")
        return True

    except Exception as e:
        logger.error(f"❌ Erreur export CSV: {e}")
        return False


def export_to_markdown(
    topics_quantified: List[Dict],
    output_path: Optional[str] = None
) -> str:
    """
    Génère un rapport Markdown de synthèse.

    Args:
        topics_quantified: Résultats de quantification
        output_path: Chemin du fichier de sortie (optionnel)

    Returns:
        Contenu Markdown (string)
    """
    logger.info("Génération du rapport Markdown...")

    lines = []

    # Header
    lines.append("# 📊 Rapport d'Analyse Verbatims\n")
    lines.append(f"*Généré le {datetime.now().strftime('%Y-%m-%d %H:%M')}*\n")
    lines.append("---\n")

    # Synthèse
    total_topics = len(topics_quantified)
    topics_with_matches = sum(
        1 for item in topics_quantified
        if item['metrics']['volume_verbatims'] > 0
    )

    lines.append("## 📈 Synthèse\n")
    lines.append(f"- **Nombre total de thèmes:** {total_topics}")
    lines.append(f"- **Thèmes avec occurrences:** {topics_with_matches}")
    lines.append(f"- **Thèmes sans occurrences:** {total_topics - topics_with_matches}\n")
    lines.append("---\n")

    # Top thèmes
    top_topics = sorted(
        topics_quantified,
        key=lambda x: x['metrics']['volume_verbatims'],
        reverse=True
    )[:10]

    lines.append("## 🔝 Top 10 Thèmes\n")
    lines.append("| Rang | Thème | Volume | % Dataset |")
    lines.append("|------|-------|--------|-----------|")

    for i, item in enumerate(top_topics, 1):
        topic = item['topic']
        metrics = item['metrics']
        lines.append(
            f"| {i} | {topic.get('canonical_label', '')} | "
            f"{metrics['volume_verbatims']} | {metrics['pct_of_dataset']:.1f}% |"
        )

    lines.append("\n---\n")

    # Détails par thème
    lines.append("## 📝 Détails par Thème\n")

    for item in top_topics:
        topic = item['topic']
        metrics = item['metrics']
        ontology = item['ontology']

        label = topic.get('canonical_label', '')
        sublabel = topic.get('canonical_subtopic', '')

        lines.append(f"### {label}")
        if sublabel:
            lines.append(f"*Sous-thème: {sublabel}*")

        lines.append(f"\n**Volume:** {metrics['volume_verbatims']} verbatims ({metrics['pct_of_dataset']:.1f}%)\n")

        # Pain points
        pain_points = topic.get('pain_points', [])
        if pain_points:
            lines.append("**Pain Points:**")
            for pp in pain_points[:5]:
                lines.append(f"- {pp}")
            lines.append("")

        # Bénéfices
        benefits = topic.get('benefits', [])
        if benefits:
            lines.append("**Bénéfices attendus:**")
            for b in benefits[:5]:
                lines.append(f"- {b}")
            lines.append("")

        # Keywords
        keywords = ontology.get('keywords', [])
        if keywords:
            lines.append(f"**Keywords:** {', '.join(keywords[:10])}\n")

        lines.append("---\n")

    markdown_content = "\n".join(lines)

    # Écrire dans fichier si demandé
    if output_path:
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(markdown_content)
            logger.info(f"✅ Rapport Markdown sauvegardé: {output_path}")
        except Exception as e:
            logger.error(f"❌ Erreur écriture Markdown: {e}")

    return markdown_content


def export_run_metadata(
    run_data: Dict,
    output_path: str
) -> bool:
    """
    Exporte les métadonnées d'un run en JSON.

    Args:
        run_data: Données du run
        output_path: Chemin du fichier de sortie

    Returns:
        True si succès
    """
    logger.info(f"Export métadonnées vers: {output_path}")

    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(run_data, f, ensure_ascii=False, indent=2, default=str)

        logger.info(f"✅ Export métadonnées réussi: {output_path}")
        return True

    except Exception as e:
        logger.error(f"❌ Erreur export métadonnées: {e}")
        return False


def create_powerpoint_table_markdown(
    topics_quantified: List[Dict],
    top_n: int = 20
) -> str:
    """
    Génère un tableau Markdown optimisé pour copie dans PowerPoint.

    Args:
        topics_quantified: Résultats de quantification
        top_n: Nombre de thèmes à inclure

    Returns:
        Tableau Markdown
    """
    top_topics = sorted(
        topics_quantified,
        key=lambda x: x['metrics']['volume_verbatims'],
        reverse=True
    )[:top_n]

    lines = []
    lines.append("| Thème | Sous-thème | Volume | % |")
    lines.append("|-------|------------|--------|---|")

    for item in top_topics:
        topic = item['topic']
        metrics = item['metrics']

        label = topic.get('canonical_label', '')
        sublabel = topic.get('canonical_subtopic', '') or '-'
        volume = metrics['volume_verbatims']
        pct = metrics['pct_of_dataset']

        lines.append(f"| {label} | {sublabel} | {volume} | {pct:.1f}% |")

    return "\n".join(lines)
