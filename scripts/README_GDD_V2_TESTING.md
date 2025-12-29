# GDD V2 Pipeline Testing Guide

## Quick Start: Test with 10 Files

### Step 1: Run Schema Migration (One-time)
```sql
-- Run in Supabase SQL Editor
-- File: deploy/supabase_schema_gdd_v2_upgrade.sql
```

### Step 2: Re-chunk 10 Markdown Files
```bash
python scripts/gdd_v2_chunk_markdown.py --limit 10
```

This will:
- Process only the first 10 markdown files from `gdd_data/markdown/`
- Save enhanced chunks to `gdd_data_v2/chunks/{doc_id}/{doc_id}_chunks.json`
- Preserve numbered section headers (e.g., "1. Mụcđíchthiếtkế", "4.1 DanhsáchTanks")

### Step 3: Index 10 Documents to Supabase
```bash
python scripts/gdd_v2_index_to_supabase.py --limit 10
```

This will:
- Load chunks from `gdd_data_v2/chunks/`
- Generate embeddings using Qwen text-embedding-v4
- Store in Supabase with all enhanced metadata:
  - `section_path`: "4. GiaodiệnTankGarage"
  - `section_title`: "4. GiaodiệnTankGarage"
  - `numbered_header`: "4. GiaodiệnTankGarage" (in metadata)
  - `content_type`: "ui", "logic", "flow", "table", etc.
  - `doc_category`: "UI Design", "Character System", etc.
  - `tags`: ["garage", "tank", "decor"]

## Verify Results

### Check Chunks Generated
```bash
# List generated chunk files
ls gdd_data_v2/chunks/*/
```

### Check Supabase
```sql
-- Check documents indexed
SELECT doc_id, name, doc_category, chunks_count 
FROM gdd_documents 
ORDER BY indexed_at DESC 
LIMIT 10;

-- Check chunks with numbered headers
SELECT chunk_id, doc_id, section_path, section_title, content_type, numbered_header
FROM gdd_chunks
WHERE doc_id IN (
    SELECT doc_id FROM gdd_documents ORDER BY indexed_at DESC LIMIT 10
)
LIMIT 20;

-- Check metadata for numbered headers
SELECT chunk_id, doc_id, metadata->>'numbered_header' as numbered_header
FROM gdd_chunks
WHERE metadata->>'numbered_header' IS NOT NULL
LIMIT 20;
```

## Full Pipeline (After Testing)

Once you're satisfied with the 10-file test:

```bash
# Re-chunk ALL files
python scripts/gdd_v2_chunk_markdown.py

# Index ALL documents
python scripts/gdd_v2_index_to_supabase.py
```

## Key Features Tested

✅ **Numbered Header Preservation**: All chunks from section "4. GiaodiệnTankGarage" will have `numbered_header: "4. GiaodiệnTankGarage"` even if split into multiple chunks

✅ **Section Path Tracking**: Hierarchical paths like "4. GiaodiệnTankGarage / 4.1 DanhsáchTanks"

✅ **Content Type Detection**: Automatically detects ui, logic, flow, table, monetization

✅ **Document Categorization**: Groups documents into categories like "UI Design", "Character System"

## Troubleshooting

### If chunking fails:
- Check that markdown files exist in `gdd_data/markdown/`
- Verify Python can import `gdd_rag_backbone` modules

### If indexing fails:
- Verify Supabase credentials in `.env`
- Check that schema migration was run
- Ensure chunks were generated first

### To re-test:
```bash
# Delete test chunks
rm -rf gdd_data_v2/chunks/*

# Delete from Supabase (optional)
# Run: DELETE FROM gdd_chunks WHERE doc_id IN (...);
# Then re-run chunking and indexing
```
