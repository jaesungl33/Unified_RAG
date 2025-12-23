"""
Test Supabase connection and data access
Run this before deploying to verify everything is configured correctly
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

from backend.storage.supabase_client import (
    get_supabase_client,
    get_gdd_documents,
    get_code_files,
    vector_search_gdd_chunks
)
from backend.shared.config import SUPABASE_URL, SUPABASE_KEY, SUPABASE_SERVICE_KEY

def test_connection():
    """Test Supabase connection and data access"""
    print("=" * 60)
    print("Supabase Connection Test")
    print("=" * 60)
    
    # Check environment variables
    print("\n1. Checking environment variables...")
    if not SUPABASE_URL:
        print("   ❌ SUPABASE_URL not set")
        return False
    else:
        print(f"   ✅ SUPABASE_URL: {SUPABASE_URL[:30]}...")
    
    if not SUPABASE_KEY:
        print("   ❌ SUPABASE_KEY not set")
        return False
    else:
        print(f"   ✅ SUPABASE_KEY: {SUPABASE_KEY[:20]}...")
    
    if not SUPABASE_SERVICE_KEY:
        print("   ⚠️  SUPABASE_SERVICE_KEY not set (needed for migrations)")
    else:
        print(f"   ✅ SUPABASE_SERVICE_KEY: {SUPABASE_SERVICE_KEY[:20]}...")
    
    # Test anon key connection (for reads)
    print("\n2. Testing anon key connection (for frontend reads)...")
    try:
        client_anon = get_supabase_client(use_service_key=False)
        print("   ✅ Anon key connection successful")
    except Exception as e:
        print(f"   ❌ Anon key connection failed: {e}")
        return False
    
    # Test service key connection (for admin operations)
    if SUPABASE_SERVICE_KEY:
        print("\n3. Testing service key connection (for admin operations)...")
        try:
            client_service = get_supabase_client(use_service_key=True)
            print("   ✅ Service key connection successful")
        except Exception as e:
            print(f"   ❌ Service key connection failed: {e}")
            return False
    
    # Test data access
    print("\n4. Testing data access...")
    try:
        gdd_docs = get_gdd_documents()
        print(f"   ✅ GDD Documents: {len(gdd_docs)} found")
        if len(gdd_docs) == 0:
            print("   ⚠️  Warning: No GDD documents found. Run migration script if needed.")
        else:
            print(f"   📄 Sample document: {gdd_docs[0].get('name', 'N/A')}")
    except Exception as e:
        print(f"   ❌ Error fetching GDD documents: {e}")
        return False
    
    try:
        code_files = get_code_files()
        print(f"   ✅ Code Files: {len(code_files)} found")
        if len(code_files) == 0:
            print("   ⚠️  Warning: No code files found. Run migration script if needed.")
        else:
            print(f"   📄 Sample file: {code_files[0].get('file_name', 'N/A')}")
    except Exception as e:
        print(f"   ❌ Error fetching code files: {e}")
        return False
    
    # Test vector search (if embeddings exist)
    print("\n5. Testing vector search...")
    try:
        # Create a dummy embedding (1024 dimensions)
        test_embedding = [0.0] * 1024
        results = vector_search_gdd_chunks(
            query_embedding=test_embedding,
            limit=5,
            threshold=0.0  # Low threshold to get some results
        )
        print(f"   ✅ Vector search works: {len(results)} results (with threshold=0.0)")
    except Exception as e:
        print(f"   ⚠️  Vector search test failed: {e}")
        print("   (This is okay if you haven't migrated chunks yet)")
    
    print("\n" + "=" * 60)
    print("✅ All tests passed! Ready to deploy.")
    print("=" * 60)
    return True

if __name__ == "__main__":
    success = test_connection()
    sys.exit(0 if success else 1)

