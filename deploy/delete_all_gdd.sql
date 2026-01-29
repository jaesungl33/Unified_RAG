-- Delete all GDD-related data from Supabase.
-- Run this in Supabase SQL Editor. Order matters: chunks first (foreign key), then documents.
-- Optionally run storage cleanup separately (see comments below).

-- 1. Delete all keyword chunks (referenced by keyword_documents via doc_id)
DELETE FROM keyword_chunks;

-- 2. Delete all keyword documents (GDD + Keyword Finder share this table; this removes all)
DELETE FROM keyword_documents;

-- Optional: Clean up storage bucket "gdd_pdfs" (PDFs and images).
-- Supabase Storage cannot be cleared via SQL. Use Dashboard > Storage > gdd_pdfs > delete files,
-- or use the Storage API in a script to list and remove objects under gdd_pdfs/.
