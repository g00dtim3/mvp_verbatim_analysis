-- ===========================================
-- MVP Analyse Verbatims - Schéma Base de Données
-- Version: 1.0
-- ===========================================

-- Extension pour UUID
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- =====================
-- TABLES PRINCIPALES
-- =====================

-- Projets d'analyse
CREATE TABLE projects (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    source_type VARCHAR(50) NOT NULL CHECK (source_type IN ('brandwatch', 'semantiweb', 'generic_csv')),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    metadata JSONB DEFAULT '{}'::jsonb
);

CREATE INDEX idx_projects_source_type ON projects(source_type);
CREATE INDEX idx_projects_created_at ON projects(created_at DESC);

-- Verbatims du projet
CREATE TABLE project_verbatims (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    
    -- Données brutes
    full_text TEXT NOT NULL,
    full_text_clean TEXT,
    
    -- Métadonnées source
    source_id VARCHAR(255),  -- ID original Brandwatch/Semantiweb
    source_date TIMESTAMP WITH TIME ZONE,
    sentiment VARCHAR(50),
    language VARCHAR(10),
    page_type VARCHAR(100),
    category VARCHAR(255),
    author VARCHAR(255),
    url TEXT,
    
    -- Déduplication
    dedup_flag BOOLEAN DEFAULT FALSE,
    dedup_group_id UUID,
    
    -- Métadonnées additionnelles (flexible)
    extra_data JSONB DEFAULT '{}'::jsonb,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_verbatims_project ON project_verbatims(project_id);
CREATE INDEX idx_verbatims_sentiment ON project_verbatims(sentiment);
CREATE INDEX idx_verbatims_language ON project_verbatims(language);
CREATE INDEX idx_verbatims_dedup ON project_verbatims(dedup_flag);
CREATE INDEX idx_verbatims_dedup_group ON project_verbatims(dedup_group_id);
CREATE INDEX idx_verbatims_full_text_clean ON project_verbatims USING gin(to_tsvector('french', full_text_clean));

-- Runs d'analyse
CREATE TABLE analysis_runs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    
    -- Configuration
    mode VARCHAR(20) NOT NULL CHECK (mode IN ('rapid', 'full')),
    brief TEXT,
    clean_params JSONB DEFAULT '{}'::jsonb,
    dedup_threshold DECIMAL(3,2) DEFAULT 0.90,
    
    -- Statut
    status VARCHAR(20) NOT NULL DEFAULT 'pending' 
        CHECK (status IN ('pending', 'processing', 'success', 'partial', 'failed', 'interrupted')),
    
    -- Métriques
    total_verbatims INTEGER,
    verbatims_after_dedup INTEGER,
    total_chunks INTEGER,
    chunks_success INTEGER DEFAULT 0,
    chunks_failed INTEGER DEFAULT 0,
    
    -- Versioning
    gida_version VARCHAR(20),
    
    -- Timestamps
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- Estimations
    estimated_cost DECIMAL(10,4),
    estimated_time_seconds INTEGER
);

CREATE INDEX idx_runs_project ON analysis_runs(project_id);
CREATE INDEX idx_runs_status ON analysis_runs(status);
CREATE INDEX idx_runs_created ON analysis_runs(created_at DESC);

-- Chunks d'analyse (mode full)
CREATE TABLE analysis_chunks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    run_id UUID NOT NULL REFERENCES analysis_runs(id) ON DELETE CASCADE,
    chunk_index INTEGER NOT NULL,
    
    -- Contenu
    verbatim_ids UUID[] NOT NULL,
    verbatim_count INTEGER NOT NULL,
    
    -- Statut
    status VARCHAR(20) NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending', 'processing', 'success', 'failed')),
    retry_count INTEGER DEFAULT 0,
    error_message TEXT,
    
    -- Timestamps
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    
    -- Résultat brut LLM
    llm_response JSONB,
    tokens_used INTEGER
);

CREATE INDEX idx_chunks_run ON analysis_chunks(run_id);
CREATE INDEX idx_chunks_status ON analysis_chunks(status);
CREATE UNIQUE INDEX idx_chunks_run_index ON analysis_chunks(run_id, chunk_index);

-- Thèmes bruts par chunk
CREATE TABLE chunk_topics (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    chunk_id UUID NOT NULL REFERENCES analysis_chunks(id) ON DELETE CASCADE,
    
    topic_label VARCHAR(255) NOT NULL,
    subtopic_label VARCHAR(255),
    pain_points TEXT[],
    benefits TEXT[],
    usage_context TEXT,
    example_verbatims TEXT[],
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_chunk_topics_chunk ON chunk_topics(chunk_id);

-- Thèmes fusionnés (par run)
CREATE TABLE run_topics (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    run_id UUID NOT NULL REFERENCES analysis_runs(id) ON DELETE CASCADE,
    
    -- Labels
    canonical_label VARCHAR(255) NOT NULL,
    canonical_subtopic VARCHAR(255),
    aliases TEXT[] DEFAULT '{}',
    
    -- Traçabilité fusion
    source_chunk_topic_ids UUID[] DEFAULT '{}',
    merge_method VARCHAR(20) CHECK (merge_method IN ('pass1_fuzzy', 'pass2_llm', 'manual', 'single')),
    merge_rationale TEXT,
    
    -- Contenu
    pain_points TEXT[],
    benefits TEXT[],
    usage_context TEXT,
    example_verbatims TEXT[],
    
    -- Quantification
    volume_verbatims INTEGER DEFAULT 0,
    volume_mentions INTEGER DEFAULT 0,
    pct_of_dataset DECIMAL(5,2) DEFAULT 0,
    
    -- État
    is_active BOOLEAN DEFAULT TRUE,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_run_topics_run ON run_topics(run_id);
CREATE INDEX idx_run_topics_active ON run_topics(is_active);

-- Ontologie projet (keywords générés par LLM)
CREATE TABLE project_ontology (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    run_id UUID NOT NULL REFERENCES analysis_runs(id) ON DELETE CASCADE,
    topic_id UUID NOT NULL REFERENCES run_topics(id) ON DELETE CASCADE,
    
    -- Keywords et patterns
    keywords JSONB NOT NULL DEFAULT '[]'::jsonb,
    regex_patterns JSONB DEFAULT '[]'::jsonb,
    negative_keywords JSONB DEFAULT '[]'::jsonb,
    negation_patterns JSONB DEFAULT '["pas de", "sans", "aucun", "n''ai pas", "ne pas"]'::jsonb,
    
    -- Validation
    validated_by VARCHAR(255),
    validated_at TIMESTAMP WITH TIME ZONE,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_ontology_run ON project_ontology(run_id);
CREATE INDEX idx_ontology_topic ON project_ontology(topic_id);

-- Entités GIDA détectées
CREATE TABLE run_entities (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    run_id UUID NOT NULL REFERENCES analysis_runs(id) ON DELETE CASCADE,
    verbatim_id UUID NOT NULL REFERENCES project_verbatims(id) ON DELETE CASCADE,
    
    entity_type VARCHAR(50) NOT NULL,  -- 'pathology', 'brand', 'zone', 'attribute'
    entity_label VARCHAR(255) NOT NULL,
    entity_id UUID,  -- Référence vers dim_ontology_entities
    
    mention_count INTEGER DEFAULT 1,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_run_entities_run ON run_entities(run_id);
CREATE INDEX idx_run_entities_verbatim ON run_entities(verbatim_id);
CREATE INDEX idx_run_entities_type ON run_entities(entity_type);

-- =====================
-- TABLES DE RÉFÉRENCE (GIDA)
-- =====================

-- Entités GIDA
CREATE TABLE dim_ontology_entities (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    ontology_version VARCHAR(20) NOT NULL,
    entity_type VARCHAR(50) NOT NULL,
    label VARCHAR(255) NOT NULL,
    label_normalized VARCHAR(255),
    keywords JSONB NOT NULL DEFAULT '[]'::jsonb,
    parent_id UUID REFERENCES dim_ontology_entities(id),
    
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_dim_entities_version ON dim_ontology_entities(ontology_version);
CREATE INDEX idx_dim_entities_type ON dim_ontology_entities(entity_type);
CREATE INDEX idx_dim_entities_label ON dim_ontology_entities(label_normalized);

-- Attributs GIDA
CREATE TABLE dim_ontology_attributes (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    ontology_version VARCHAR(20) NOT NULL,
    attribute_type VARCHAR(50) NOT NULL,
    label VARCHAR(255) NOT NULL,
    label_normalized VARCHAR(255),
    keywords JSONB NOT NULL DEFAULT '[]'::jsonb,
    
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_dim_attributes_version ON dim_ontology_attributes(ontology_version);
CREATE INDEX idx_dim_attributes_type ON dim_ontology_attributes(attribute_type);

-- =====================
-- LOGS
-- =====================

CREATE TABLE processing_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    run_id UUID REFERENCES analysis_runs(id) ON DELETE CASCADE,
    
    log_type VARCHAR(50) NOT NULL,  -- 'info', 'warning', 'error', 'merge_conflict', 'llm_call'
    step VARCHAR(50),  -- 'import', 'cleaning', 'analysis', 'merge', 'quantification'
    message TEXT NOT NULL,
    details JSONB DEFAULT '{}'::jsonb,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_logs_run ON processing_logs(run_id);
CREATE INDEX idx_logs_type ON processing_logs(log_type);
CREATE INDEX idx_logs_created ON processing_logs(created_at DESC);

-- =====================
-- FONCTIONS UTILITAIRES
-- =====================

-- Fonction pour mettre à jour updated_at automatiquement
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Trigger sur projects
CREATE TRIGGER update_projects_updated_at
    BEFORE UPDATE ON projects
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- =====================
-- VUES UTILES
-- =====================

-- Vue résumé des runs
CREATE VIEW v_run_summary AS
SELECT 
    r.id,
    r.project_id,
    p.name as project_name,
    r.mode,
    r.status,
    r.total_verbatims,
    r.verbatims_after_dedup,
    r.total_chunks,
    r.chunks_success,
    r.chunks_failed,
    r.gida_version,
    r.created_at,
    r.completed_at,
    EXTRACT(EPOCH FROM (r.completed_at - r.started_at)) as duration_seconds,
    COUNT(DISTINCT rt.id) as topic_count
FROM analysis_runs r
JOIN projects p ON r.project_id = p.id
LEFT JOIN run_topics rt ON r.id = rt.run_id AND rt.is_active = TRUE
GROUP BY r.id, p.name;

-- Vue thèmes avec métriques
CREATE VIEW v_topics_with_metrics AS
SELECT 
    rt.*,
    r.mode as run_mode,
    p.name as project_name
FROM run_topics rt
JOIN analysis_runs r ON rt.run_id = r.id
JOIN projects p ON r.project_id = p.id
WHERE rt.is_active = TRUE;

-- =====================
-- DONNÉES INITIALES
-- =====================

-- Insérer les patterns de négation par défaut (pour référence)
-- Ces valeurs sont utilisées par défaut dans project_ontology

COMMENT ON TABLE projects IS 'Projets d''analyse de verbatims';
COMMENT ON TABLE project_verbatims IS 'Verbatims bruts et nettoyés';
COMMENT ON TABLE analysis_runs IS 'Historique des runs d''analyse';
COMMENT ON TABLE analysis_chunks IS 'Chunks pour le mode full coverage';
COMMENT ON TABLE chunk_topics IS 'Thèmes bruts extraits par chunk';
COMMENT ON TABLE run_topics IS 'Thèmes fusionnés et quantifiés';
COMMENT ON TABLE project_ontology IS 'Keywords/regex générés pour la quantification';
COMMENT ON TABLE run_entities IS 'Entités GIDA détectées par verbatim';
COMMENT ON TABLE dim_ontology_entities IS 'Référentiel GIDA - Entités';
COMMENT ON TABLE dim_ontology_attributes IS 'Référentiel GIDA - Attributs';
COMMENT ON TABLE processing_logs IS 'Logs de traitement détaillés';

-- Fin du script
SELECT 'Schema created successfully!' as status;
