#!/usr/bin/env python3
"""
Script d'initialisation de la base de données.
Crée toutes les tables selon les modèles SQLAlchemy.
"""

import sys
from pathlib import Path

# Ajouter le root au path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from loguru import logger
from sqlalchemy import text

from src.db.connection import engine, get_db, test_connection
from src.db.models import Base
from src.utils.config import settings


def init_database():
    """Initialise la base de données."""
    logger.info("=== Initialisation de la base de données ===")

    # 1. Tester la connexion
    logger.info("1. Test de connexion...")
    if not test_connection():
        logger.error("❌ Impossible de se connecter à la base de données")
        logger.error(f"   URL: {settings.database_url}")
        return False

    logger.info("✅ Connexion établie")

    # 2. Créer les tables
    logger.info("2. Création des tables...")

    try:
        Base.metadata.create_all(bind=engine)
        logger.info("✅ Tables créées avec succès")

    except Exception as e:
        logger.error(f"❌ Erreur lors de la création des tables: {e}")
        return False

    # 3. Vérifier les tables
    logger.info("3. Vérification des tables...")

    try:
        with get_db() as db:
            result = db.execute(text("""
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public'
                ORDER BY table_name
            """))

            tables = [row[0] for row in result]

            logger.info(f"   Tables créées: {len(tables)}")
            for table in tables:
                logger.info(f"   - {table}")

    except Exception as e:
        logger.error(f"❌ Erreur lors de la vérification: {e}")
        return False

    # 4. Créer des index si nécessaire
    logger.info("4. Création des index additionnels...")

    additional_indexes = [
        "CREATE INDEX IF NOT EXISTS idx_verbatims_project ON project_verbatims(project_id)",
        "CREATE INDEX IF NOT EXISTS idx_verbatims_clean ON project_verbatims(full_text_clean)",
        "CREATE INDEX IF NOT EXISTS idx_runs_project ON analysis_runs(project_id)",
        "CREATE INDEX IF NOT EXISTS idx_runs_status ON analysis_runs(status)",
        "CREATE INDEX IF NOT EXISTS idx_entities_run ON run_entities(run_id)",
        "CREATE INDEX IF NOT EXISTS idx_entities_verbatim ON run_entities(verbatim_id)",
    ]

    try:
        with get_db() as db:
            for index_sql in additional_indexes:
                db.execute(text(index_sql))

        logger.info("✅ Index créés avec succès")

    except Exception as e:
        logger.error(f"❌ Erreur lors de la création des index: {e}")
        return False

    logger.info("\n=== ✅ Base de données initialisée avec succès ===\n")
    return True


def drop_all_tables():
    """
    ⚠️ DANGER: Supprime toutes les tables.
    À utiliser uniquement en développement.
    """
    logger.warning("⚠️  ATTENTION: Suppression de toutes les tables!")

    confirm = input("Êtes-vous sûr? (tapez 'OUI' pour confirmer): ")

    if confirm != "OUI":
        logger.info("Annulé.")
        return

    try:
        Base.metadata.drop_all(bind=engine)
        logger.info("✅ Toutes les tables ont été supprimées")

    except Exception as e:
        logger.error(f"❌ Erreur lors de la suppression: {e}")


def reset_database():
    """Supprime et recrée toutes les tables."""
    logger.warning("=== RESET de la base de données ===")

    confirm = input("⚠️  Toutes les données seront perdues. Continuer? (tapez 'OUI'): ")

    if confirm != "OUI":
        logger.info("Annulé.")
        return

    logger.info("Suppression des tables...")
    Base.metadata.drop_all(bind=engine)

    logger.info("Recréation des tables...")
    init_database()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Gestion de la base de données")
    parser.add_argument(
        "action",
        choices=["init", "drop", "reset"],
        help="Action à effectuer: init (créer), drop (supprimer), reset (recréer)"
    )

    args = parser.parse_args()

    if args.action == "init":
        success = init_database()
        sys.exit(0 if success else 1)

    elif args.action == "drop":
        drop_all_tables()

    elif args.action == "reset":
        reset_database()
