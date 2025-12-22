# Unified RAG Application

A unified Flask web application combining GDD RAG and Code Q&A functionality.

## Features

- **GDD RAG**: Query Game Design Documents using RAG technology
- **Code Q&A**: Query C# codebase using semantic search
- **Unified Interface**: Single Flask app with tabbed navigation
- **Supabase Storage**: Cloud-based vector storage (optional, falls back to local storage)

## Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Environment Variables

Copy `.env.example` to `.env` and fill in your values:

```bash
cp .env.example .env
```

Required variables:
- `DASHSCOPE_API_KEY`: Your Qwen/DashScope API key

Optional (for Supabase):
- `SUPABASE_URL`: Your Supabase project URL
- `SUPABASE_KEY`: Your Supabase anon key
- `SUPABASE_SERVICE_KEY`: Your Supabase service role key

**Note**: If Supabase is not configured, the app will use local file storage (JSON files for GDD, LanceDB for Code Q&A).

### 3. Run Locally

```bash
python app.py
```

The app will be available at `http://localhost:5000`

## Deployment to Render

### 1. Create Render Account

Sign up at [render.com](https://render.com)

### 2. Create New Web Service

1. Connect your Git repository
2. Select "Web Service"
3. Configure:
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn app:app --bind 0.0.0.0:$PORT --workers 2 --timeout 120`
   - **Environment**: Python 3

### 3. Set Environment Variables

Add all variables from `.env.example` in Render dashboard:
- `SUPABASE_URL`
- `SUPABASE_KEY`
- `DASHSCOPE_API_KEY`
- `FLASK_SECRET_KEY`
- etc.

### 4. Deploy

Render will automatically deploy when you push to your repository.

## Project Structure

```
unified_rag_app/
├── app.py                 # Main Flask application
├── requirements.txt       # Python dependencies
├── Procfile              # Process file for Render
├── .env.example          # Environment variables template
├── backend/              # Backend services
│   ├── gdd_service.py    # GDD RAG service (to be created)
│   ├── code_service.py   # Code Q&A service (to be created)
│   ├── storage/          # Storage modules
│   └── shared/          # Shared utilities
├── templates/            # HTML templates
│   ├── base.html
│   ├── index.html
│   ├── gdd_tab.html
│   └── code_tab.html
├── static/              # Static files
│   ├── css/
│   │   └── style.css
│   └── js/
│       ├── tabs.js
│       ├── gdd.js
│       └── code.js
└── deploy/              # Deployment configs
    └── render.yaml
```

## Supabase Integration

The app supports Supabase for cloud-based vector storage. See [SUPABASE_SETUP.md](SUPABASE_SETUP.md) for detailed setup instructions.

**Quick Setup:**
1. Create Supabase project at https://supabase.com
2. Enable pgvector extension in SQL Editor
3. Run `deploy/supabase_schema.sql` in SQL Editor
4. Add Supabase credentials to `.env` file
5. Restart the app

**Migration:**
- Use `scripts/migrate_to_supabase.py` to migrate existing local data to Supabase

## Current Status

1. ✅ Basic Flask app structure created
2. ✅ GDD RAG logic integrated from `gradio_app.py`
3. ✅ Code Q&A structure ready (needs integration)
4. ✅ Supabase integration for GDD RAG (with local fallback)
5. ⏳ Code Q&A Supabase integration (pending)
6. ⏳ Full testing and deployment

## Notes

- This is a new folder - your existing code in `GDD_RAG_Gradio` remains untouched
- The app structure is ready, but API endpoints need to be implemented
- Supabase integration is planned but not yet implemented

