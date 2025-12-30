"""Check all chunk types for a file."""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv()

from backend.storage.supabase_client import get_supabase_client

client = get_supabase_client(use_service_key=True)
response = client.table('code_chunks').select('chunk_type, class_name').eq('file_path', 'Assets/_GameModules/Editor/NamingConventionScanner.cs').execute()

print("All chunks for NamingConventionScanner.cs:")
for chunk in response.data:
    print(f"  {chunk['chunk_type']}: {chunk['class_name']}")

print(f"\nTotal: {len(response.data)} chunks")

