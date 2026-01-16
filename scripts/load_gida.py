#!/usr/bin/env python3
"""
Script de chargement des entités GIDA dans la base de données.
"""

import sys
import json
from pathlib import Path
from uuid import uuid4

# Ajouter le root au path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from loguru import logger
from src.db.connection import get_db
from src.db.models import DimOntologyEntity, DimOntologyAttribute
from src.utils.config import settings


def load_gida_data(filepath: str = None):
    """
    Charge les données GIDA depuis le fichier JSON dans la base de données.

    Args:
        filepath: Chemin vers le fichier GIDA JSON
    """
    filepath = filepath or settings.gida_path
    filepath = Path(filepath)

    logger.info(f"=== Chargement des données GIDA ===")
    logger.info(f"Fichier: {filepath}")

    # Vérifier que le fichier existe
    if not filepath.exists():
        logger.error(f"❌ Fichier non trouvé: {filepath}")
        return False

    # Charger le JSON
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            gida_data = json.load(f)

        version = gida_data.get('version', 'unknown')
        entities = gida_data.get('entities', [])

        logger.info(f"Version GIDA: {version}")
        logger.info(f"Nombre d'entités: {len(entities)}")

    except Exception as e:
        logger.error(f"❌ Erreur lors de la lecture du fichier: {e}")
        return False

    # Insérer dans la base de données
    try:
        with get_db() as db:
            # Supprimer les anciennes données de cette version
            logger.info(f"Suppression des données existantes pour version {version}...")

            db.query(DimOntologyEntity).filter(
                DimOntologyEntity.ontology_version == version
            ).delete()

            db.query(DimOntologyAttribute).filter(
                DimOntologyAttribute.ontology_version == version
            ).delete()

            # Insérer les nouvelles données
            logger.info("Insertion des nouvelles données...")

            for entity_data in entities:
                entity_type = entity_data.get('entity_type')

                # Distinguer entités vs attributs
                if entity_type == 'attribute':
                    # Attribut
                    attribute = DimOntologyAttribute(
                        id=uuid4(),
                        ontology_version=version,
                        attribute_type=entity_type,
                        label=entity_data.get('label'),
                        label_normalized=entity_data.get('label_normalized'),
                        keywords=entity_data.get('keywords', []),
                        is_active=True
                    )
                    db.add(attribute)

                else:
                    # Entité (pathology, brand, zone)
                    entity = DimOntologyEntity(
                        id=uuid4(),
                        ontology_version=version,
                        entity_type=entity_type,
                        label=entity_data.get('label'),
                        label_normalized=entity_data.get('label_normalized'),
                        keywords=entity_data.get('keywords', []),
                        parent_id=None,  # TODO: Gérer les relations parent-enfant si nécessaire
                        is_active=True
                    )
                    db.add(entity)

            db.commit()

        logger.info(f"✅ {len(entities)} entités GIDA chargées avec succès")
        return True

    except Exception as e:
        logger.error(f"❌ Erreur lors de l'insertion: {e}")
        return False


def get_gida_stats():
    """Affiche les statistiques des données GIDA en base."""
    logger.info("=== Statistiques GIDA ===")

    try:
        with get_db() as db:
            # Entités
            entities_count = db.query(DimOntologyEntity).count()
            logger.info(f"Entités: {entities_count}")

            # Par type
            from sqlalchemy import func
            entity_types = db.query(
                DimOntologyEntity.entity_type,
                func.count(DimOntologyEntity.id)
            ).group_by(DimOntologyEntity.entity_type).all()

            for entity_type, count in entity_types:
                logger.info(f"  - {entity_type}: {count}")

            # Attributs
            attributes_count = db.query(DimOntologyAttribute).count()
            logger.info(f"Attributs: {attributes_count}")

    except Exception as e:
        logger.error(f"❌ Erreur: {e}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Gestion des données GIDA")
    parser.add_argument(
        "action",
        choices=["load", "stats"],
        help="Action: load (charger), stats (statistiques)"
    )
    parser.add_argument(
        "--file",
        help="Chemin vers le fichier GIDA JSON (optionnel)"
    )

    args = parser.parse_args()

    if args.action == "load":
        success = load_gida_data(filepath=args.file)
        sys.exit(0 if success else 1)

    elif args.action == "stats":
        get_gida_stats()
