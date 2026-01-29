-- Add images JSONB column to keyword_documents for storing extracted document image metadata.
-- Each entry: { "filename": "...", "url": "https://...", "path": "doc_id/images/filename" }
-- Run in Supabase SQL Editor.

ALTER TABLE keyword_documents
ADD COLUMN IF NOT EXISTS images jsonb DEFAULT '[]'::jsonb;

COMMENT ON COLUMN keyword_documents.images IS 'Array of {filename, url, path} for images extracted from PDF (Chandra), stored in gdd_pdfs/{doc_id}/images/';
