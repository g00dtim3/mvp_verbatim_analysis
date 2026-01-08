"""
Modèles SQLAlchemy pour l'ORM.
"""

from sqlalchemy import (
    Column, String, Text, Integer, Boolean, DateTime, Float,
    ForeignKey, ARRAY, JSON, CheckConstraint, Index
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy.sql import func
import uuid

Base = declarative_base()


class Project(Base):
    """Projet d'analyse."""
    __tablename__ = "projects"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    source_type = Column(String(50), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    metadata_ = Column("metadata", JSONB, default={})
    
    # Relations
    verbatims = relationship("ProjectVerbatim", back_populates="project", cascade="all, delete-orphan")
    runs = relationship("AnalysisRun", back_populates="project", cascade="all, delete-orphan")
    
    __table_args__ = (
        CheckConstraint(source_type.in_(['brandwatch', 'semantiweb', 'generic_csv'])),
    )


class ProjectVerbatim(Base):
    """Verbatim d'un projet."""
    __tablename__ = "project_verbatims"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    
    # Données
    full_text = Column(Text, nullable=False)
    full_text_clean = Column(Text)
    
    # Métadonnées source
    source_id = Column(String(255))
    source_date = Column(DateTime(timezone=True))
    sentiment = Column(String(50))
    language = Column(String(10))
    page_type = Column(String(100))
    category = Column(String(255))
    author = Column(String(255))
    url = Column(Text)
    
    # Déduplication
    dedup_flag = Column(Boolean, default=False)
    dedup_group_id = Column(UUID(as_uuid=True))
    
    # Extra
    extra_data = Column(JSONB, default={})
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relations
    project = relationship("Project", back_populates="verbatims")
    entities = relationship("RunEntity", back_populates="verbatim", cascade="all, delete-orphan")


class AnalysisRun(Base):
    """Run d'analyse."""
    __tablename__ = "analysis_runs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    
    # Configuration
    mode = Column(String(20), nullable=False)
    brief = Column(Text)
    clean_params = Column(JSONB, default={})
    dedup_threshold = Column(Float, default=0.90)
    
    # Statut
    status = Column(String(20), nullable=False, default="pending")
    
    # Métriques
    total_verbatims = Column(Integer)
    verbatims_after_dedup = Column(Integer)
    total_chunks = Column(Integer)
    chunks_success = Column(Integer, default=0)
    chunks_failed = Column(Integer, default=0)
    
    # Versioning
    gida_version = Column(String(20))
    
    # Timestamps
    started_at = Column(DateTime(timezone=True))
    completed_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Estimations
    estimated_cost = Column(Float)
    estimated_time_seconds = Column(Integer)
    
    # Relations
    project = relationship("Project", back_populates="runs")
    chunks = relationship("AnalysisChunk", back_populates="run", cascade="all, delete-orphan")
    topics = relationship("RunTopic", back_populates="run", cascade="all, delete-orphan")
    ontology = relationship("ProjectOntology", back_populates="run", cascade="all, delete-orphan")
    entities = relationship("RunEntity", back_populates="run", cascade="all, delete-orphan")
    logs = relationship("ProcessingLog", back_populates="run", cascade="all, delete-orphan")
    
    __table_args__ = (
        CheckConstraint(mode.in_(['rapid', 'full'])),
        CheckConstraint(status.in_(['pending', 'processing', 'success', 'partial', 'failed', 'interrupted'])),
    )


class AnalysisChunk(Base):
    """Chunk d'analyse (mode full)."""
    __tablename__ = "analysis_chunks"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    run_id = Column(UUID(as_uuid=True), ForeignKey("analysis_runs.id", ondelete="CASCADE"), nullable=False)
    chunk_index = Column(Integer, nullable=False)
    
    # Contenu
    verbatim_ids = Column(ARRAY(UUID(as_uuid=True)), nullable=False)
    verbatim_count = Column(Integer, nullable=False)
    
    # Statut
    status = Column(String(20), nullable=False, default="pending")
    retry_count = Column(Integer, default=0)
    error_message = Column(Text)
    
    # Timestamps
    started_at = Column(DateTime(timezone=True))
    completed_at = Column(DateTime(timezone=True))
    
    # Résultat
    llm_response = Column(JSONB)
    tokens_used = Column(Integer)
    
    # Relations
    run = relationship("AnalysisRun", back_populates="chunks")
    topics = relationship("ChunkTopic", back_populates="chunk", cascade="all, delete-orphan")
    
    __table_args__ = (
        CheckConstraint(status.in_(['pending', 'processing', 'success', 'failed'])),
        Index('idx_chunks_run_index', 'run_id', 'chunk_index', unique=True),
    )


class ChunkTopic(Base):
    """Thème brut par chunk."""
    __tablename__ = "chunk_topics"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    chunk_id = Column(UUID(as_uuid=True), ForeignKey("analysis_chunks.id", ondelete="CASCADE"), nullable=False)
    
    topic_label = Column(String(255), nullable=False)
    subtopic_label = Column(String(255))
    pain_points = Column(ARRAY(Text))
    benefits = Column(ARRAY(Text))
    usage_context = Column(Text)
    example_verbatims = Column(ARRAY(Text))
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relations
    chunk = relationship("AnalysisChunk", back_populates="topics")


class RunTopic(Base):
    """Thème fusionné (par run)."""
    __tablename__ = "run_topics"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    run_id = Column(UUID(as_uuid=True), ForeignKey("analysis_runs.id", ondelete="CASCADE"), nullable=False)
    
    # Labels
    canonical_label = Column(String(255), nullable=False)
    canonical_subtopic = Column(String(255))
    aliases = Column(ARRAY(Text), default=[])
    
    # Traçabilité
    source_chunk_topic_ids = Column(ARRAY(UUID(as_uuid=True)), default=[])
    merge_method = Column(String(20))
    merge_rationale = Column(Text)
    
    # Contenu
    pain_points = Column(ARRAY(Text))
    benefits = Column(ARRAY(Text))
    usage_context = Column(Text)
    example_verbatims = Column(ARRAY(Text))
    
    # Quantification
    volume_verbatims = Column(Integer, default=0)
    volume_mentions = Column(Integer, default=0)
    pct_of_dataset = Column(Float, default=0)
    
    # État
    is_active = Column(Boolean, default=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relations
    run = relationship("AnalysisRun", back_populates="topics")
    ontology = relationship("ProjectOntology", back_populates="topic", cascade="all, delete-orphan")


class ProjectOntology(Base):
    """Ontologie projet (keywords générés)."""
    __tablename__ = "project_ontology"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    run_id = Column(UUID(as_uuid=True), ForeignKey("analysis_runs.id", ondelete="CASCADE"), nullable=False)
    topic_id = Column(UUID(as_uuid=True), ForeignKey("run_topics.id", ondelete="CASCADE"), nullable=False)
    
    # Keywords
    keywords = Column(JSONB, nullable=False, default=[])
    regex_patterns = Column(JSONB, default=[])
    negative_keywords = Column(JSONB, default=[])
    negation_patterns = Column(JSONB, default=["pas de", "sans", "aucun", "n'ai pas", "ne pas"])
    
    # Validation
    validated_by = Column(String(255))
    validated_at = Column(DateTime(timezone=True))
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relations
    run = relationship("AnalysisRun", back_populates="ontology")
    topic = relationship("RunTopic", back_populates="ontology")


class RunEntity(Base):
    """Entité GIDA détectée."""
    __tablename__ = "run_entities"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    run_id = Column(UUID(as_uuid=True), ForeignKey("analysis_runs.id", ondelete="CASCADE"), nullable=False)
    verbatim_id = Column(UUID(as_uuid=True), ForeignKey("project_verbatims.id", ondelete="CASCADE"), nullable=False)
    
    entity_type = Column(String(50), nullable=False)
    entity_label = Column(String(255), nullable=False)
    entity_id = Column(UUID(as_uuid=True))
    mention_count = Column(Integer, default=1)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relations
    run = relationship("AnalysisRun", back_populates="entities")
    verbatim = relationship("ProjectVerbatim", back_populates="entities")


class DimOntologyEntity(Base):
    """Entité GIDA (référentiel)."""
    __tablename__ = "dim_ontology_entities"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ontology_version = Column(String(20), nullable=False)
    entity_type = Column(String(50), nullable=False)
    label = Column(String(255), nullable=False)
    label_normalized = Column(String(255))
    keywords = Column(JSONB, nullable=False, default=[])
    parent_id = Column(UUID(as_uuid=True), ForeignKey("dim_ontology_entities.id"))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class DimOntologyAttribute(Base):
    """Attribut GIDA (référentiel)."""
    __tablename__ = "dim_ontology_attributes"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ontology_version = Column(String(20), nullable=False)
    attribute_type = Column(String(50), nullable=False)
    label = Column(String(255), nullable=False)
    label_normalized = Column(String(255))
    keywords = Column(JSONB, nullable=False, default=[])
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class ProcessingLog(Base):
    """Log de traitement."""
    __tablename__ = "processing_logs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    run_id = Column(UUID(as_uuid=True), ForeignKey("analysis_runs.id", ondelete="CASCADE"))
    
    log_type = Column(String(50), nullable=False)
    step = Column(String(50))
    message = Column(Text, nullable=False)
    details = Column(JSONB, default={})
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relations
    run = relationship("AnalysisRun", back_populates="logs")
