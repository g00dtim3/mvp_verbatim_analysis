"""
Gestion de la connexion à la base de données PostgreSQL / Supabase.
Supporte:
- PostgreSQL local (docker-compose)
- Supabase (backend-as-a-service PostgreSQL)
"""

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool, NullPool
from contextlib import contextmanager
from typing import Generator
from loguru import logger

from src.utils.config import settings


# Obtenir l'URL de connexion (local ou Supabase)
database_url = settings.get_database_url()

# Convertir postgresql:// en postgresql+psycopg:// pour utiliser psycopg3
if database_url.startswith("postgresql://"):
    database_url = database_url.replace("postgresql://", "postgresql+psycopg://", 1)
    logger.debug("Converted database URL to use psycopg3 driver")

# Log du type de connexion
if settings.use_supabase:
    logger.info("🔵 Using Supabase as database backend")
    logger.debug(f"Supabase URL: {settings.supabase_url}")
else:
    logger.info("🐘 Using local PostgreSQL")

# Configuration du pool selon le backend
if settings.use_supabase:
    # Supabase: utiliser NullPool ou pool léger (connection pooler côté Supabase)
    engine = create_engine(
        database_url,
        poolclass=NullPool,  # Supabase gère son propre pooling
        echo=settings.debug,
        connect_args={
            "connect_timeout": 10,
            "options": "-c timezone=utc"
        }
    )
else:
    # PostgreSQL local: pool classique
    engine = create_engine(
        database_url,
        poolclass=QueuePool,
        pool_size=5,
        max_overflow=10,
        pool_timeout=30,
        pool_recycle=1800,
        echo=settings.debug,
    )

# Factory de sessions
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)


@contextmanager
def get_db() -> Generator[Session, None, None]:
    """
    Context manager pour obtenir une session DB.
    
    Usage:
        with get_db() as db:
            result = db.execute(query)
    """
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception as e:
        db.rollback()
        logger.error(f"Database error: {e}")
        raise
    finally:
        db.close()


def get_db_session() -> Session:
    """
    Retourne une session DB (pour Streamlit).
    N'oubliez pas de fermer la session après usage.
    """
    return SessionLocal()


def test_connection() -> bool:
    """
    Teste la connexion à la base de données.
    
    Returns:
        True si la connexion est OK, False sinon.
    """
    try:
        with get_db() as db:
            result = db.execute(text("SELECT 1"))
            logger.info("✅ Database connection successful")
            return True
    except Exception as e:
        logger.error(f"❌ Database connection failed: {e}")
        return False


def get_db_info() -> dict:
    """
    Retourne des informations sur la base de données.
    """
    try:
        with get_db() as db:
            # Version PostgreSQL
            version = db.execute(text("SELECT version()")).scalar()
            
            # Nombre de tables
            tables_count = db.execute(text("""
                SELECT COUNT(*) 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
            """)).scalar()
            
            # Taille de la DB
            db_size = db.execute(text("""
                SELECT pg_size_pretty(pg_database_size(current_database()))
            """)).scalar()
            
            return {
                "version": version,
                "tables_count": tables_count,
                "database_size": db_size,
                "connected": True,
            }
    except Exception as e:
        return {
            "error": str(e),
            "connected": False,
        }


def execute_sql_file(filepath: str) -> bool:
    """
    Exécute un fichier SQL.
    
    Args:
        filepath: Chemin vers le fichier SQL
        
    Returns:
        True si succès, False sinon
    """
    try:
        with open(filepath, 'r') as f:
            sql_content = f.read()
        
        with get_db() as db:
            # Exécuter par blocs (séparés par ;)
            statements = [s.strip() for s in sql_content.split(';') if s.strip()]
            for statement in statements:
                if statement:
                    db.execute(text(statement))
            
        logger.info(f"✅ SQL file executed: {filepath}")
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to execute SQL file: {e}")
        return False
