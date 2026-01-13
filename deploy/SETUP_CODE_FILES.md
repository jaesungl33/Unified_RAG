# Setup Supabase for Code Files

This guide will help you set up Supabase specifically for code file storage and indexing.

## Prerequisites

- A Supabase project (create one at https://supabase.com if you don't have one)
- Your Supabase project URL and API keys

## Step 1: Run the Setup Script

1. Go to your Supabase dashboard
2. Navigate to **SQL Editor**
3. Open the file: `deploy/setup_code_files_supabase.sql`
4. Copy the entire contents
5. Paste into the SQL Editor
6. Click **Run** to execute

This will create:
- `code_files` table - stores metadata about uploaded .cs files
- `code_chunks` table - stores code chunks (methods, classes, structs, interfaces, enums) with embeddings
- Indexes for fast queries
- Vector search function `match_code_chunks` for semantic search
- RLS policies for security

## Step 2: Verify the Setup

After running the script, verify everything was created:

### Check Tables
```sql
SELECT table_name 
FROM information_schema.tables 
WHERE table_schema = 'public' 
AND table_name IN ('code_files', 'code_chunks');
```

You should see both `code_files` and `code_chunks` in the results.

### Check Indexes
```sql
SELECT indexname 
FROM pg_indexes 
WHERE tablename IN ('code_files', 'code_chunks');
```

You should see indexes like:
- `code_chunks_embedding_idx` (for vector search)
- `code_chunks_file_path_idx` (for file filtering)
- `code_chunks_type_idx` (for chunk type filtering)
- `code_files_file_path_idx` (for file lookups)

### Check Function
```sql
SELECT routine_name 
FROM information_schema.routines 
WHERE routine_schema = 'public' 
AND routine_name = 'match_code_chunks';
```

You should see `match_code_chunks` in the results.

### Check RLS Policies
```sql
SELECT tablename, rowsecurity 
FROM pg_tables 
WHERE schemaname = 'public' 
AND tablename IN ('code_files', 'code_chunks');
```

Both tables should have `rowsecurity = true`.

## Step 3: Update Chunk Type Constraint (if needed)

If you already have the `code_chunks` table but it only allows 'method' and 'class', you need to update it to also allow 'struct', 'interface', and 'enum':

1. Run the script: `deploy/update_chunk_type_constraint.sql`
2. Or run this SQL:

```sql
-- Drop existing constraint
ALTER TABLE code_chunks 
DROP CONSTRAINT IF EXISTS code_chunks_chunk_type_check;

-- Add new constraint
ALTER TABLE code_chunks 
ADD CONSTRAINT code_chunks_chunk_type_check 
CHECK (chunk_type IN ('method', 'class', 'struct', 'interface', 'enum'));
```

## Step 4: Configure Environment Variables

Make sure your `.env` file has the Supabase credentials:

```env
SUPABASE_URL=https://your-project-id.supabase.co
SUPABASE_KEY=your-anon-key-here
SUPABASE_SERVICE_KEY=your-service-role-key-here
```

To get these values:
1. Go to Supabase dashboard → **Settings** → **API**
2. Copy **Project URL** → `SUPABASE_URL`
3. Copy **anon public** key → `SUPABASE_KEY`
4. Copy **service_role** key → `SUPABASE_SERVICE_KEY` (keep this secret!)

## Step 5: Test the Setup

1. Start your Flask app:
   ```powershell
   python app.py
   ```

2. Go to the **Manage Documents** tab
3. Click on **Code Files** sub-tab
4. Upload a `.cs` file
5. Check the queue - it should process and index the file

6. Verify in Supabase:
   - Go to **Table Editor** → `code_files`
   - You should see your uploaded file
   - Go to **Table Editor** → `code_chunks`
   - You should see chunks with embeddings

## Troubleshooting

### "Table does not exist" error
- Make sure you ran the `setup_code_files_supabase.sql` script completely
- Check that you're connected to the correct Supabase project

### "chunk_type constraint violation"
- Run the `update_chunk_type_constraint.sql` script
- This happens if the table was created with only 'method' and 'class' allowed

### "Extension vector does not exist"
- Run: `CREATE EXTENSION IF NOT EXISTS vector;` in SQL Editor

### "RLS policy violation"
- Check that RLS policies were created correctly
- Verify your API keys are correct (anon key for reads, service_role for writes)

### Upload fails silently
- Check the Flask app logs for errors
- Verify `SUPABASE_SERVICE_KEY` is set correctly (needed for writes)
- Check that the `match_code_chunks` function exists

### Vector search not working
- Verify embeddings are being inserted (check `code_chunks.embedding` column - should not be NULL)
- Check that embedding dimensions match (should be 1024 for Qwen)
- Verify pgvector extension is enabled

## Schema Details

### code_files Table
- `id`: UUID primary key
- `file_path`: Unique file path (used as foreign key)
- `file_name`: File name
- `normalized_path`: Normalized path for matching
- `indexed_at`: When the file was indexed
- `created_at`, `updated_at`: Timestamps

### code_chunks Table
- `id`: UUID primary key
- `file_path`: Foreign key to code_files
- `chunk_type`: 'method', 'class', 'struct', 'interface', or 'enum'
- `class_name`: Name of the class (if applicable)
- `method_name`: Name of the method (for method chunks)
- `source_code`: Full source code of the chunk
- `code`: Method code (for method chunks only)
- `embedding`: Vector embedding (1024 dimensions)
- `doc_comment`: Documentation comment
- `constructor_declaration`: Constructor (for classes)
- `method_declarations`: Method declarations (for classes)
- `code_references`: Code references
- `metadata`: JSONB metadata
- `created_at`, `updated_at`: Timestamps

## Next Steps

After setup is complete:
1. Test uploading a code file via the Manage Documents tab
2. Test querying code via the Code Q&A tab
3. Verify chunks are being created correctly
4. Check that vector search is working

