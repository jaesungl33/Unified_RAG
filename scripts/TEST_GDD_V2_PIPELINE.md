# GDD V2 Pipeline - Testing with 10 Files

## ✅ Status: Scripts Ready

The scripts are now fixed and ready to test. Supabase configuration is verified.

## Step-by-Step Testing

### Step 0: Cleanup Existing GDD Data (Optional but Recommended)
```bash
# Remove all existing GDD data from Supabase to avoid conflicts
python scripts/cleanup_gdd_before_v2_test.py --yes
```

Or to remove only specific documents:
```bash
python scripts/cleanup_gdd_before_v2_test.py --doc-ids DocID1 DocID2 --yes
```

### Step 1: Run Schema Migration (One-time)
```sql
-- In Supabase SQL Editor, run:
-- File: deploy/supabase_schema_gdd_v2_upgrade.sql
```

### Step 2: Re-chunk 10 Markdown Files
```bash
# Activate venv first
.\venv\Scripts\Activate.ps1

# Run chunking for 10 files
python scripts/gdd_v2_chunk_markdown.py --limit 10
```

**Expected Output:**
- Processes first 10 markdown files from `gdd_data/markdown/`
- Saves to `gdd_data_v2/chunks/{doc_id}/{doc_id}_chunks.json`
- Each chunk will have:
  - `numbered_header`: "1. Mụcđíchthiếtkế", "4.1 DanhsáchTanks", etc.
  - `section_path`: Hierarchical path
  - `content_type`: ui, logic, flow, table, etc.
  - `doc_category`: UI Design, Character System, etc.

### Step 3: Index 10 Documents to Supabase
```bash
# Still in venv
python scripts/gdd_v2_index_to_supabase.py --limit 10
```

**Expected Output:**
- Loads chunks from `gdd_data_v2/chunks/`
- Generates embeddings
- Stores in Supabase with all enhanced metadata

### Step 4: Verify in Supabase
```sql
-- Check documents
SELECT doc_id, name, doc_category, chunks_count 
FROM gdd_documents 
ORDER BY indexed_at DESC 
LIMIT 10;

-- Check chunks with numbered headers
SELECT 
    chunk_id, 
    doc_id, 
    section_path, 
    section_title,
    content_type,
    metadata->>'numbered_header' as numbered_header
FROM gdd_chunks
WHERE doc_id IN (
    SELECT doc_id FROM gdd_documents ORDER BY indexed_at DESC LIMIT 10
)
LIMIT 20;

-- Count chunks per document
SELECT doc_id, COUNT(*) as chunk_count
FROM gdd_chunks
WHERE doc_id IN (
    SELECT doc_id FROM gdd_documents ORDER BY indexed_at DESC LIMIT 10
)
GROUP BY doc_id;
```

## Troubleshooting

### If chunking script fails:
1. Check that markdown files exist: `gdd_data/markdown/*.md`
2. Verify Python can import `gdd_rag_backbone` modules
3. Check for encoding errors (should be fixed now)

### If indexing script fails:
1. Run test script: `python scripts/test_supabase_config.py`
2. Verify schema migration was run
3. Check that chunks were generated first

### Unicode Errors (Fixed):
- All Unicode characters (✓, ✗, ⚠) have been replaced with ASCII-safe alternatives
- Scripts should work on Windows console now

## What Gets Tested

✅ **Numbered Header Preservation**: All chunks from "4. GiaodiệnTankGarage" will have `numbered_header: "4. GiaodiệnTankGarage"` even if split

✅ **Section Path Tracking**: Hierarchical paths like "4. GiaodiệnTankGarage / 4.1 DanhsáchTanks"

✅ **Content Type Detection**: Automatically detects ui, logic, flow, table, monetization

✅ **Document Categorization**: Groups into "UI Design", "Character System", etc.

## Next Steps After Testing

If the 10-file test succeeds:
1. Run full chunking: `python scripts/gdd_v2_chunk_markdown.py`
2. Run full indexing: `python scripts/gdd_v2_index_to_supabase.py`
3. Update retrieval logic to use new metadata fields
