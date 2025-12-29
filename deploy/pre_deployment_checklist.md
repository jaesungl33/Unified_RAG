# Pre-Deployment Checklist: Supabase + Render

## ✅ Step 1: Verify Supabase Setup

### 1.1 Database Schema
- [x] Run `supabase_schema.sql` - Creates tables and functions
- [x] Run `supabase_rls_policies.sql` - Sets up Row Level Security

### 1.2 Data Migration
- [x] GDD documents migrated (43 documents)
- [x] GDD chunks migrated (~727 chunks)
- [x] Code files migrated (484 files)
- [x] Code chunks migrated (4228 chunks)

### 1.3 Verify Data in Supabase
Run this in Supabase SQL Editor:
```sql
SELECT 'gdd_documents' as table_name, COUNT(*) as count FROM gdd_documents
UNION ALL
SELECT 'gdd_chunks', COUNT(*) FROM gdd_chunks
UNION ALL
SELECT 'code_files', COUNT(*) FROM code_files
UNION ALL
SELECT 'code_chunks', COUNT(*) FROM code_chunks;
```

Expected results:
- `gdd_documents`: 43
- `gdd_chunks`: ~727
- `code_files`: 484
- `code_chunks`: 4228

### 1.4 Verify RLS Policies
Run `check_rls_policies.sql` in Supabase SQL Editor to verify:
- RLS is enabled on all tables
- Policies exist for `anon` (SELECT) and `service_role` (INSERT/UPDATE/DELETE)

## ✅ Step 2: Verify Environment Variables

### 2.1 Local `.env` file
Check `unified_rag_app/.env` has:
```env
SUPABASE_URL=https://your-project-id.supabase.co
SUPABASE_KEY=your-publishable-key-or-anon-key
SUPABASE_SERVICE_KEY=your-secret-key-or-service-role-key
DASHSCOPE_API_KEY=your-dashscope-key
```

### 2.2 Render Environment Variables
In Render Dashboard → Your Service → Environment:
- [ ] `SUPABASE_URL` - Must match your Supabase project URL
- [ ] `SUPABASE_KEY` - Must be your publishable/anon key (for frontend reads)
- [ ] `SUPABASE_SERVICE_KEY` - Must be your secret/service_role key (for admin operations)
- [ ] `DASHSCOPE_API_KEY` - Your DashScope API key
- [ ] `FLASK_SECRET_KEY` - Random secret for Flask sessions
- [ ] `PYTHON_VERSION` - Should be `3.11.9` (to avoid tiktoken build issues)

## ✅ Step 3: Test Locally

Run locally to verify everything works:
```bash
python app.py
```

Check:
- [x] GDD RAG tab shows all 43 documents in sidebar
- [x] Code Q&A tab shows all 484 files in sidebar
- [x] Can query GDD documents and get answers
- [x] Can query codebase and get answers

## ✅ Step 4: Pre-Deployment Verification

### 4.1 Test Supabase Connection from Local
Run this Python script to test:
```python
from backend.storage.supabase_client import get_supabase_client, get_gdd_documents, get_code_files

# Test anon key (for reads)
client = get_supabase_client(use_service_key=False)
docs = get_gdd_documents()
files = get_code_files()
print(f"GDD Documents: {len(docs)}")
print(f"Code Files: {len(files)}")
```

### 4.2 Verify Render Service Settings
In Render Dashboard → Your Service → Settings:
- [ ] **Root Directory**: Should be empty or `.` (not `unified_rag_app`)
- [ ] **Build Command**: `pip install -r requirements.txt`
- [ ] **Start Command**: `gunicorn app:app --bind 0.0.0.0:$PORT --workers 2 --timeout 120`
- [ ] **Python Version**: `3.11.9` (set in Environment Variables)

## ✅ Step 5: Ready to Deploy

Once all above are checked:
1. Commit and push your code to GitHub (if using Git)
2. In Render, click "Manual Deploy" → "Deploy latest commit"
3. Monitor the build logs for any errors
4. Once deployed, test the public URL:
   - GDD RAG tab should show documents
   - Code Q&A tab should show files
   - Queries should work

## 🔍 Troubleshooting After Deployment

If deployed app shows empty sidebars:
1. Check Render logs for errors
2. Verify environment variables are set correctly
3. Test Supabase connection from Render (add a test endpoint)
4. Check RLS policies allow `anon` role to SELECT

