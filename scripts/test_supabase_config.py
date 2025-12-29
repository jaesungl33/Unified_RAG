"""
Test Supabase Configuration
===========================
Verifies that Supabase is properly configured and accessible.
"""

import os
import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv()

print("=" * 70)
print("SUPABASE CONFIGURATION TEST")
print("=" * 70)
print()

# Check environment variables
supabase_url = os.getenv('SUPABASE_URL')
supabase_key = os.getenv('SUPABASE_KEY')
supabase_service_key = os.getenv('SUPABASE_SERVICE_KEY')

print("Environment Variables:")
print(f"  SUPABASE_URL: {'[OK] Set' if supabase_url else '[MISSING]'}")
if supabase_url:
    print(f"    Value: {supabase_url[:50]}...")
print(f"  SUPABASE_KEY: {'[OK] Set' if supabase_key else '[MISSING]'}")
if supabase_key:
    print(f"    Value: {supabase_key[:20]}...")
print(f"  SUPABASE_SERVICE_KEY: {'[OK] Set' if supabase_service_key else '[MISSING]'}")
if supabase_service_key:
    print(f"    Value: {supabase_service_key[:20]}...")
print()

# Try importing supabase_client
print("Testing Imports:")
try:
    from backend.storage.supabase_client import (
        get_supabase_client,
        SUPABASE_URL,
        SUPABASE_KEY,
        SUPABASE_SERVICE_KEY
    )
    print("  [OK] Successfully imported supabase_client")
    print(f"  SUPABASE_URL from config: {'[OK] Set' if SUPABASE_URL else '[MISSING]'}")
    print(f"  SUPABASE_KEY from config: {'[OK] Set' if SUPABASE_KEY else '[MISSING]'}")
    print(f"  SUPABASE_SERVICE_KEY from config: {'[OK] Set' if SUPABASE_SERVICE_KEY else '[MISSING]'}")
except ImportError as e:
    print(f"  ✗ Failed to import supabase_client: {e}")
    sys.exit(1)
except Exception as e:
    print(f"  ✗ Error importing: {e}")
    sys.exit(1)

print()

# Try importing gdd_supabase_storage
print("Testing GDD Supabase Storage:")
try:
    from backend.storage.gdd_supabase_storage import USE_SUPABASE
    print(f"  USE_SUPABASE: {USE_SUPABASE}")
    if not USE_SUPABASE:
        print("  ✗ USE_SUPABASE is False - checking why...")
except ImportError as e:
    print(f"  ✗ Failed to import gdd_supabase_storage: {e}")
except Exception as e:
    print(f"  ✗ Error: {e}")

print()

# Try to get Supabase client
print("Testing Supabase Client Connection:")
try:
    client = get_supabase_client(use_service_key=False)
    print("  [OK] Successfully created Supabase client (anon key)")
    
    # Try a simple query
    try:
        result = client.table('gdd_documents').select('doc_id').limit(1).execute()
        print(f"  [OK] Successfully queried gdd_documents table")
        print(f"    Sample result: {len(result.data)} row(s)")
    except Exception as e:
        print(f"  [WARNING] Could not query gdd_documents: {e}")
        print("    (Table might not exist yet - this is OK if you haven't run schema migration)")
    
except Exception as e:
    print(f"  [ERROR] Failed to create Supabase client: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print()

# Try service key client
print("Testing Supabase Service Key Client:")
try:
    service_client = get_supabase_client(use_service_key=True)
    print("  [OK] Successfully created Supabase client (service key)")
except Exception as e:
    print(f"  [ERROR] Failed to create service key client: {e}")
    print("    (This is needed for indexing)")

print()

# Check shared config
print("Testing Shared Config:")
try:
    from backend.shared.config import SUPABASE_URL as SHARED_URL, SUPABASE_KEY as SHARED_KEY
    print(f"  Shared SUPABASE_URL: {'[OK] Set' if SHARED_URL else '[MISSING]'}")
    print(f"  Shared SUPABASE_KEY: {'[OK] Set' if SHARED_KEY else '[MISSING]'}")
except ImportError:
    print("  [WARNING] Could not import from backend.shared.config")
except Exception as e:
    print(f"  [ERROR] Error: {e}")

print()
print("=" * 70)
print("TEST COMPLETE")
print("=" * 70)
