"""
Module d'import CSV et mapping de colonnes.
"""

import pandas as pd
from typing import Dict, List, Optional, Tuple
from pathlib import Path
from loguru import logger
from sqlalchemy.orm import Session
import uuid
from datetime import datetime

from src.db.models import Project, ProjectVerbatim
from src.utils.config import (
    settings,
    BRANDWATCH_COLUMN_MAPPING,
    SEMANTIWEB_COLUMN_MAPPING
)


def detect_source_type(df: pd.DataFrame) -> str:
    """
    Détecte automatiquement le type de source (Brandwatch, Semantiweb, ou generic).

    Args:
        df: DataFrame pandas

    Returns:
        'brandwatch', 'semantiweb', ou 'generic_csv'
    """
    columns = set(df.columns)

    # Colonnes caractéristiques Brandwatch
    brandwatch_markers = {'Full Text', 'Query Id', 'Page Type', 'Sentiment'}
    if brandwatch_markers.issubset(columns):
        logger.info("Source détectée: Brandwatch")
        return 'brandwatch'

    # Colonnes caractéristiques Semantiweb
    semantiweb_markers = {'review_text', 'review_id', 'sentiment_label'}
    if semantiweb_markers.issubset(columns):
        logger.info("Source détectée: Semantiweb")
        return 'semantiweb'

    logger.info("Source détectée: generic_csv")
    return 'generic_csv'


def get_recommended_mapping(source_type: str) -> Dict[str, str]:
    """
    Retourne le mapping recommandé selon le type de source.

    Args:
        source_type: Type de source

    Returns:
        Dictionnaire {colonne_source: colonne_cible}
    """
    if source_type == 'brandwatch':
        return BRANDWATCH_COLUMN_MAPPING
    elif source_type == 'semantiweb':
        return SEMANTIWEB_COLUMN_MAPPING
    else:
        return {}


def apply_column_mapping(
    df: pd.DataFrame,
    mapping: Dict[str, str]
) -> pd.DataFrame:
    """
    Applique le mapping de colonnes à un DataFrame.

    Args:
        df: DataFrame source
        mapping: Dictionnaire {colonne_source: colonne_cible}

    Returns:
        DataFrame avec colonnes renommées
    """
    # Ne garder que les mappings dont les colonnes existent
    valid_mapping = {
        src: tgt for src, tgt in mapping.items()
        if src in df.columns
    }

    # Renommer
    df_mapped = df.rename(columns=valid_mapping)

    logger.info(f"Mapping appliqué: {len(valid_mapping)} colonnes")
    return df_mapped


def validate_mapped_dataframe(df: pd.DataFrame) -> Tuple[bool, List[str]]:
    """
    Valide qu'un DataFrame mappé contient les champs requis.

    Args:
        df: DataFrame mappé

    Returns:
        (is_valid, missing_fields)
    """
    required_fields = ['full_text']
    missing = [f for f in required_fields if f not in df.columns]

    is_valid = len(missing) == 0

    if not is_valid:
        logger.warning(f"Champs manquants: {missing}")

    return is_valid, missing


def load_csv_file(filepath: str, encoding: str = 'utf-8') -> pd.DataFrame:
    """
    Charge un fichier CSV.

    Args:
        filepath: Chemin vers le fichier
        encoding: Encodage (utf-8, latin1, cp1252...)

    Returns:
        DataFrame pandas

    Raises:
        Exception si erreur de lecture
    """
    try:
        df = pd.read_csv(filepath, encoding=encoding)
        logger.info(f"CSV chargé: {len(df)} lignes, {len(df.columns)} colonnes")
        return df

    except UnicodeDecodeError:
        # Essayer avec un autre encodage
        logger.warning(f"Échec encodage {encoding}, essai avec latin1")
        df = pd.read_csv(filepath, encoding='latin1')
        logger.info(f"CSV chargé (latin1): {len(df)} lignes")
        return df

    except Exception as e:
        logger.error(f"Erreur chargement CSV: {e}")
        raise


def parse_date_column(
    df: pd.DataFrame,
    date_column: str = 'source_date'
) -> pd.DataFrame:
    """
    Parse une colonne de date avec gestion des erreurs.

    Args:
        df: DataFrame
        date_column: Nom de la colonne date

    Returns:
        DataFrame avec colonne date parsée
    """
    if date_column not in df.columns:
        return df

    try:
        df[date_column] = pd.to_datetime(df[date_column], errors='coerce')
        logger.info(f"Colonne {date_column} parsée en datetime")
    except Exception as e:
        logger.warning(f"Impossible de parser {date_column}: {e}")

    return df


def create_project_from_csv(
    db: Session,
    name: str,
    filepath: str,
    source_type: Optional[str] = None,
    column_mapping: Optional[Dict[str, str]] = None,
    description: Optional[str] = None,
) -> Tuple[Project, int]:
    """
    Crée un projet et importe les verbatims depuis un CSV.

    Args:
        db: Session DB
        name: Nom du projet
        filepath: Chemin vers le CSV
        source_type: Type de source (auto-détecté si None)
        column_mapping: Mapping personnalisé (auto si None)
        description: Description du projet

    Returns:
        (project, nb_verbatims_imported)

    Raises:
        ValueError si validation échoue
    """
    # 1. Charger le CSV
    df = load_csv_file(filepath)

    if len(df) > settings.max_verbatims:
        raise ValueError(
            f"Dataset trop large: {len(df)} verbatims "
            f"(max: {settings.max_verbatims})"
        )

    # 2. Détecter la source si nécessaire
    if source_type is None:
        source_type = detect_source_type(df)

    # 3. Obtenir le mapping
    if column_mapping is None:
        column_mapping = get_recommended_mapping(source_type)

    # 4. Appliquer le mapping
    df = apply_column_mapping(df, column_mapping)

    # 5. Parser les dates
    df = parse_date_column(df, 'source_date')

    # 6. Valider
    is_valid, missing = validate_mapped_dataframe(df)
    if not is_valid:
        raise ValueError(f"Champs requis manquants: {missing}")

    # 7. Créer le projet
    project = Project(
        name=name,
        description=description,
        source_type=source_type,
        metadata_={
            'original_filepath': str(filepath),
            'original_rows': len(df),
            'original_columns': list(df.columns),
            'column_mapping': column_mapping,
        }
    )
    db.add(project)
    db.flush()  # Pour obtenir l'ID

    logger.info(f"Projet créé: {project.id} - {name}")

    # 8. Insérer les verbatims
    verbatims = []
    for _, row in df.iterrows():
        verbatim = ProjectVerbatim(
            project_id=project.id,
            full_text=str(row.get('full_text', '')),
            source_id=str(row.get('source_id', '')),
            source_date=row.get('source_date') if pd.notna(row.get('source_date')) else None,
            sentiment=str(row.get('sentiment', '')) if pd.notna(row.get('sentiment')) else None,
            language=str(row.get('language', '')) if pd.notna(row.get('language')) else None,
            page_type=str(row.get('page_type', '')) if pd.notna(row.get('page_type')) else None,
            category=str(row.get('category', '')) if pd.notna(row.get('category')) else None,
            author=str(row.get('author', '')) if pd.notna(row.get('author')) else None,
            url=str(row.get('url', '')) if pd.notna(row.get('url')) else None,
            extra_data={
                k: v for k, v in row.items()
                if k not in [
                    'full_text', 'source_id', 'source_date', 'sentiment',
                    'language', 'page_type', 'category', 'author', 'url'
                ] and pd.notna(v)
            }
        )
        verbatims.append(verbatim)

    db.bulk_save_objects(verbatims)
    db.commit()

    logger.info(f"✅ {len(verbatims)} verbatims importés")

    return project, len(verbatims)


def get_project_summary(db: Session, project_id: uuid.UUID) -> Dict:
    """
    Retourne un résumé du projet importé.

    Args:
        db: Session DB
        project_id: ID du projet

    Returns:
        Dictionnaire avec statistiques
    """
    project = db.query(Project).filter(Project.id == project_id).first()

    if not project:
        raise ValueError(f"Projet {project_id} non trouvé")

    # Compter verbatims
    total_verbatims = db.query(ProjectVerbatim).filter(
        ProjectVerbatim.project_id == project_id
    ).count()

    # Stats par langue
    languages = db.query(
        ProjectVerbatim.language,
        db.func.count(ProjectVerbatim.id)
    ).filter(
        ProjectVerbatim.project_id == project_id,
        ProjectVerbatim.language.isnot(None)
    ).group_by(ProjectVerbatim.language).all()

    # Stats par sentiment
    sentiments = db.query(
        ProjectVerbatim.sentiment,
        db.func.count(ProjectVerbatim.id)
    ).filter(
        ProjectVerbatim.project_id == project_id,
        ProjectVerbatim.sentiment.isnot(None)
    ).group_by(ProjectVerbatim.sentiment).all()

    return {
        'project_id': str(project.id),
        'project_name': project.name,
        'source_type': project.source_type,
        'total_verbatims': total_verbatims,
        'languages': dict(languages),
        'sentiments': dict(sentiments),
        'created_at': project.created_at,
    }
