-- Dictionary Tables Schema for Unified RAG App
-- Run this in Supabase SQL Editor BEFORE running populate_dictionary_role_fields.sql
--
-- This creates the base dictionary tables:
-- - dictionary_components (component anchors)
-- - dictionary_references (references to GDD sections)
-- - dictionary_aliases (component aliases)

-- ============================================================================
-- Dictionary Components Table
-- ============================================================================

CREATE TABLE IF NOT EXISTS dictionary_components (
    component_key TEXT PRIMARY KEY,
    display_name_vi TEXT NOT NULL,
    aliases_vi TEXT[] DEFAULT '{}',
    embedding vector(1024), -- Qwen text-embedding-v4 has 1024 dimensions
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Index for vector similarity search on component embeddings
CREATE INDEX IF NOT EXISTS dictionary_components_embedding_idx ON dictionary_components 
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);

-- Index for display name search
CREATE INDEX IF NOT EXISTS dictionary_components_display_name_idx ON dictionary_components(display_name_vi);

-- ============================================================================
-- Dictionary References Table
-- ============================================================================

CREATE TABLE IF NOT EXISTS dictionary_references (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    component_key TEXT NOT NULL REFERENCES dictionary_components(component_key) ON DELETE CASCADE,
    doc_id TEXT NOT NULL,
    section_path TEXT NOT NULL,
    evidence_text_vi TEXT,
    source_language TEXT DEFAULT 'vi',
    confidence_score FLOAT DEFAULT 0.0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Index for component_key lookups (most common query)
CREATE INDEX IF NOT EXISTS dictionary_references_component_key_idx ON dictionary_references(component_key);

-- Index for doc_id lookups
CREATE INDEX IF NOT EXISTS dictionary_references_doc_id_idx ON dictionary_references(doc_id);

-- Composite index for component + doc queries
CREATE INDEX IF NOT EXISTS dictionary_references_component_doc_idx ON dictionary_references(component_key, doc_id);

-- ============================================================================
-- Dictionary Aliases Table (optional, for alias management)
-- ============================================================================

CREATE TABLE IF NOT EXISTS dictionary_aliases (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    component_key TEXT NOT NULL REFERENCES dictionary_components(component_key) ON DELETE CASCADE,
    alias_vi TEXT NOT NULL,
    source TEXT DEFAULT 'llm', -- 'llm' or 'human'
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Index for alias lookups
CREATE INDEX IF NOT EXISTS dictionary_aliases_component_key_idx ON dictionary_aliases(component_key);
CREATE INDEX IF NOT EXISTS dictionary_aliases_alias_vi_idx ON dictionary_aliases(alias_vi);

-- ============================================================================
-- Triggers for updated_at
-- ============================================================================

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger for dictionary_components
CREATE TRIGGER update_dictionary_components_updated_at
BEFORE UPDATE ON dictionary_components
FOR EACH ROW
EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- Comments
-- ============================================================================

COMMENT ON TABLE dictionary_components IS 
    'Component anchors (Tank, Turret, etc.) or GLOBAL_UI anchors (HUD, menus, etc.)';

COMMENT ON TABLE dictionary_references IS 
    'References from components to GDD document sections with evidence text';

COMMENT ON TABLE dictionary_aliases IS 
    'Alternative names/aliases for components, sourced from LLM or human input';

COMMENT ON COLUMN dictionary_components.component_key IS 
    'Primary key: unique identifier for the component (e.g., "tank", "global_ui")';

COMMENT ON COLUMN dictionary_components.display_name_vi IS 
    'Display name in Vietnamese';

COMMENT ON COLUMN dictionary_components.aliases_vi IS 
    'Array of Vietnamese aliases for the component';

COMMENT ON COLUMN dictionary_references.component_key IS 
    'Foreign key to dictionary_components';

COMMENT ON COLUMN dictionary_references.section_path IS 
    'Path to the section in the GDD document (e.g., "Tank/Garage/Wrap")';

COMMENT ON COLUMN dictionary_references.evidence_text_vi IS 
    'Extracted evidence text in Vietnamese that supports this reference';

