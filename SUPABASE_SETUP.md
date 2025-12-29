# Supabase Integration Setup Guide

This guide will help you set up Supabase for the Unified RAG App.

## Step 1: Create Supabase Project

1. Go to https://supabase.com
2. Sign up or log in
3. Click "New Project"
4. Fill in:
   - **Name**: Your project name (e.g., "unified-rag-app")
   - **Database Password**: Choose a strong password (save it!)
   - **Region**: Choose closest to you
5. Click "Create new project"
6. Wait for project to be created (2-3 minutes)

## Step 2: Enable pgvector Extension

1. In Supabase dashboard, go to **SQL Editor**
2. Run this command:
   ```sql
   CREATE EXTENSION IF NOT EXISTS vector;
   ```
3. Click "Run" to execute

## Step 3: Create Database Tables

1. In Supabase dashboard, go to **SQL Editor**
2. Open the file: `deploy/supabase_schema.sql`
3. Copy the entire contents
4. Paste into SQL Editor
5. Click "Run" to execute
6. You should see "Success. No rows returned"

This creates:
- `gdd_documents` - GDD document metadata
- `gdd_chunks` - GDD document chunks with embeddings
- `code_files` - Code file metadata
- `code_chunks` - Code chunks (methods/classes) with embeddings
- Vector search functions: `match_gdd_chunks` and `match_code_chunks`

## Step 4: Get Your API Keys

1. In Supabase dashboard, go to **Settings** → **API**
2. Copy these values:
   - **Project URL** → `SUPABASE_URL`
   - **anon public** key → `SUPABASE_KEY`
   - **service_role** key → `SUPABASE_SERVICE_KEY` (keep this secret!)

## Step 5: Configure Environment Variables

1. In `unified_rag_app` folder, copy `env.example` to `.env`:
   ```powershell
   copy env.example .env
   ```

2. Edit `.env` and add your Supabase credentials:
   ```env
   SUPABASE_URL=https://your-project-id.supabase.co
   SUPABASE_KEY=your-anon-key-here
   SUPABASE_SERVICE_KEY=your-service-role-key-here
   ```

## Step 6: Test the Connection

Run the app and check if Supabase is being used:

```powershell
.\venv\Scripts\python.exe app.py
```

Check the console output - it should indicate if Supabase is configured.

## Step 7: Migrate Existing Data (Optional)

If you have existing documents/chunks in local storage, you can migrate them:

```powershell
python scripts/migrate_to_supabase.py
```

(This script will be created next)

## Verification

To verify Supabase is working:

1. Upload a document via the web UI
2. Check Supabase dashboard → **Table Editor** → `gdd_documents`
3. You should see your document listed
4. Check `gdd_chunks` table - you should see chunks with embeddings

## Troubleshooting

### "Supabase is not configured" error
- Check that `.env` file exists and has correct values
- Make sure you're using the correct keys (anon vs service_role)

### "Extension vector does not exist"
- Run `CREATE EXTENSION IF NOT EXISTS vector;` in SQL Editor

### "Table does not exist"
- Make sure you ran the `supabase_schema.sql` script completely

### Vector search not working
- Check that embeddings are being inserted (check `gdd_chunks.embedding` column)
- Verify pgvector extension is enabled
- Check that embedding dimensions match (should be 1024 for Qwen)

## Next Steps

After Supabase is set up:
1. Test document upload and indexing
2. Test queries
3. Migrate existing data if needed
4. Deploy to Render with Supabase credentials in environment variables

