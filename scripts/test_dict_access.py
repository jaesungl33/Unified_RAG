#!/usr/bin/env python3
import sys
from pathlib import Path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from backend.storage.supabase_client import get_supabase_client

# Test with service key
client_service = get_supabase_client(use_service_key=True)
res_service = client_service.table('dictionary_components').select('*').limit(5).execute()
print(f"Service key - Components: {len(res_service.data or [])}")
for c in (res_service.data or [])[:3]:
    print(f"  - {c.get('component_key')}: {c.get('display_name_vi')}")

# Test with anon key
client_anon = get_supabase_client(use_service_key=False)
res_anon = client_anon.table('dictionary_components').select('*').limit(5).execute()
print(f"\nAnon key - Components: {len(res_anon.data or [])}")
for c in (res_anon.data or [])[:3]:
    print(f"  - {c.get('component_key')}: {c.get('display_name_vi')}")


