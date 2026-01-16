"""
Configuration centralisée de l'application.
Charge les variables depuis .env
"""

from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional
from functools import lru_cache


class Settings(BaseSettings):
    """Configuration de l'application."""
    
    # ----- Base de données -----
    database_url: str = Field(
        default="postgresql://verbatim_user:verbatim_password@localhost:5432/verbatim_analysis",
        description="URL de connexion PostgreSQL"
    )

    # ----- Supabase (optionnel) -----
    # Si ces valeurs sont fournies, elles remplacent database_url
    supabase_url: Optional[str] = Field(
        default=None,
        description="URL du projet Supabase (ex: https://xxxxx.supabase.co)"
    )
    supabase_key: Optional[str] = Field(
        default=None,
        description="Clé API Supabase (anon/service key)"
    )
    supabase_db_url: Optional[str] = Field(
        default=None,
        description="URL de connexion directe à la DB Supabase (connection pooler)"
    )
    use_supabase: bool = Field(
        default=False,
        description="Utiliser Supabase au lieu de PostgreSQL local"
    )

    # ----- OpenAI -----
    openai_api_key: str = Field(
        default="",
        description="Clé API OpenAI"
    )
    openai_model: str = Field(
        default="gpt-4-turbo-preview",
        description="Modèle OpenAI à utiliser"
    )
    
    # ----- Application -----
    debug: bool = Field(default=True)
    log_level: str = Field(default="INFO")
    
    # ----- Limites -----
    max_verbatims: int = Field(
        default=30000,
        description="Nombre maximum de verbatims par projet"
    )
    max_chunks: int = Field(
        default=500,
        description="Nombre maximum de chunks (blocage)"
    )
    chunk_size: int = Field(
        default=200,
        description="Nombre de verbatims par chunk"
    )
    sample_size_rapid: int = Field(
        default=750,
        description="Taille de l'échantillon en mode rapide"
    )
    
    # ----- Timeouts -----
    llm_timeout: int = Field(
        default=120,
        description="Timeout par appel LLM en secondes"
    )
    llm_max_retries: int = Field(
        default=3,
        description="Nombre max de retries par chunk"
    )
    
    # ----- Parallélisme -----
    llm_parallel_calls: int = Field(
        default=10,
        description="Nombre d'appels LLM en parallèle"
    )
    
    # ----- Seuils -----
    dedup_threshold_default: float = Field(
        default=0.90,
        description="Seuil de déduplication par défaut"
    )
    fuzzy_merge_threshold: float = Field(
        default=0.92,
        description="Seuil fuzzy pour fusion Pass 1"
    )
    jaccard_merge_threshold: float = Field(
        default=0.75,
        description="Seuil Jaccard pour fusion Pass 1"
    )
    negation_window: int = Field(
        default=3,
        description="Fenêtre de mots pour détection négation"
    )
    
    # ----- Sampling -----
    min_per_stratum: int = Field(
        default=30,
        description="Minimum de verbatims par strate"
    )
    cap_per_stratum: int = Field(
        default=300,
        description="Maximum de verbatims par strate"
    )
    sampling_seed: int = Field(
        default=42,
        description="Seed pour reproductibilité du sampling"
    )
    
    # ----- GIDA -----
    gida_version: str = Field(
        default="2026.01",
        description="Version du référentiel GIDA"
    )
    gida_path: str = Field(
        default="data/gida/gida_2026_01.json",
        description="Chemin vers le fichier GIDA"
    )
    
    # ----- Alertes -----
    chunk_warning_threshold: int = Field(
        default=100,
        description="Seuil d'alerte (warning) en nombre de chunks"
    )
    chunk_blocking_threshold: int = Field(
        default=500,
        description="Seuil de blocage en nombre de chunks"
    )
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False

    def get_database_url(self) -> str:
        """
        Retourne l'URL de connexion à la base de données.
        Priorité: Supabase DB URL > database_url local
        """
        if self.use_supabase and self.supabase_db_url:
            return self.supabase_db_url
        return self.database_url

    def is_supabase_configured(self) -> bool:
        """Vérifie si Supabase est correctement configuré."""
        return (
            self.use_supabase
            and self.supabase_url is not None
            and self.supabase_key is not None
            and self.supabase_db_url is not None
        )


@lru_cache()
def get_settings() -> Settings:
    """Retourne l'instance de configuration (cached)."""
    return Settings()


# Instance globale pour import direct
settings = get_settings()


# ----- Constantes -----

# Patterns de négation par défaut
DEFAULT_NEGATION_PATTERNS = [
    "pas de",
    "sans",
    "aucun",
    "aucune",
    "n'ai pas",
    "n'a pas",
    "ne pas",
    "ni",
    "jamais",
    "plus de",  # "je n'ai plus de"
]

# Options de nettoyage disponibles
CLEANING_OPTIONS = {
    "lowercase": "Mettre en minuscules",
    "remove_urls": "Retirer les URLs",
    "remove_emojis": "Retirer les emojis",
    "remove_extra_spaces": "Normaliser les espaces",
    "remove_punctuation": "Retirer la ponctuation excessive",
}

# Mapping colonnes Brandwatch
BRANDWATCH_COLUMN_MAPPING = {
    "Full Text": "full_text",
    "Date": "source_date",
    "Sentiment": "sentiment",
    "Language": "language",
    "Page Type": "page_type",
    "URL": "url",
    "Author": "author",
    "Query Id": "source_id",
}

# Mapping colonnes Semantiweb
SEMANTIWEB_COLUMN_MAPPING = {
    "review_text": "full_text",
    "review_date": "source_date",
    "sentiment_label": "sentiment",
    "language": "language",
    "source": "page_type",
    "review_url": "url",
    "author_name": "author",
    "review_id": "source_id",
    "category": "category",
}

# Statuts possibles pour un run
RUN_STATUSES = {
    "pending": "En attente",
    "processing": "En cours",
    "success": "Terminé",
    "partial": "Partiel (chunks échoués)",
    "failed": "Échoué",
    "interrupted": "Interrompu",
}

# Types d'entités GIDA
GIDA_ENTITY_TYPES = [
    "pathology",
    "brand",
    "zone",
    "attribute",
]
