"""
Diagnose and fix the code_chunks chunk_type constraint issue.

This script:
1. Checks current constraint definition
2. Provides SQL to fix it
3. Tests if enum chunks can be inserted (after you run the SQL)
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

from backend.storage.supabase_client import get_supabase_client

def check_constraint():
    """Check the current constraint definition"""
    print("=" * 70)
    print("Checking code_chunks chunk_type constraint...")
    print("=" * 70)
    
    try:
        client = get_supabase_client(use_service_key=True)
        
        # Query constraint definition using RPC (if available) or direct query
        # Since we can't execute raw SQL directly, we'll check by trying to query
        # the information_schema or pg_constraint via a workaround
        
        print("\n1. Checking existing chunk types in database...")
        result = client.table('code_chunks').select('chunk_type').execute()
        
        if result.data:
            chunk_types = set(row['chunk_type'] for row in result.data)
            print(f"   Found chunk types: {sorted(chunk_types)}")
            
            type_counts = {}
            for row in result.data:
                chunk_type = row['chunk_type']
                type_counts[chunk_type] = type_counts.get(chunk_type, 0) + 1
            
            print("\n   Chunk type counts:")
            for chunk_type, count in sorted(type_counts.items()):
                print(f"     - {chunk_type}: {count}")
        else:
            print("   No chunks found in database")
        
        print("\n2. Testing constraint by checking if 'enum' is allowed...")
        print("   (This will show an error if constraint doesn't allow 'enum')")
        
        # Try to get a sample chunk to see structure
        sample = client.table('code_chunks').select('*').limit(1).execute()
        if sample.data:
            print("   ✅ Can query code_chunks table")
        else:
            print("   ⚠️  No chunks found to test structure")
        
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False
    
    print("\n" + "=" * 70)
    print("SQL TO FIX CONSTRAINT")
    print("=" * 70)
    print("\nCopy and paste this SQL into Supabase SQL Editor and run it:\n")
    print("-" * 70)
    print("""
-- Step 1: Drop the existing constraint
ALTER TABLE code_chunks 
DROP CONSTRAINT IF EXISTS code_chunks_chunk_type_check;

-- Step 2: Add the new constraint that allows all chunk types
ALTER TABLE code_chunks 
ADD CONSTRAINT code_chunks_chunk_type_check 
CHECK (chunk_type IN ('method', 'class', 'struct', 'interface', 'enum'));

-- Step 3: Verify the constraint was updated
SELECT 
    conname as constraint_name,
    pg_get_constraintdef(oid) as constraint_definition
FROM pg_constraint 
WHERE conrelid = 'code_chunks'::regclass 
AND conname = 'code_chunks_chunk_type_check';
""")
    print("-" * 70)
    
    print("\n" + "=" * 70)
    print("VERIFICATION")
    print("=" * 70)
    print("\nAfter running the SQL above, run this query to verify:\n")
    print("-" * 70)
    print("""
SELECT 
    conname as constraint_name,
    pg_get_constraintdef(oid) as constraint_definition
FROM pg_constraint 
WHERE conrelid = 'code_chunks'::regclass 
AND conname = 'code_chunks_chunk_type_check';
""")
    print("-" * 70)
    print("\nExpected result should show:")
    print("CHECK ((chunk_type = ANY (ARRAY['method'::text, 'class'::text, 'struct'::text, 'interface'::text, 'enum'::text])))")
    
    return True

def test_enum_insert():
    """Test if we can insert an enum chunk (after constraint is fixed)"""
    print("\n" + "=" * 70)
    print("TESTING ENUM INSERT (After running SQL)")
    print("=" * 70)
    
    try:
        client = get_supabase_client(use_service_key=True)
        
        # Try to insert a test enum chunk
        # We'll use a dummy file path that likely doesn't exist
        test_chunk = {
            'file_path': 'TEST_ENUM_CHECK.cs',
            'chunk_type': 'enum',
            'chunk_name': 'TestEnum',
            'source_code': 'enum TestEnum { Value1, Value2 }',
            'embedding': [0.0] * 1024,  # Dummy embedding
            'metadata': {'test': True}
        }
        
        print("\nAttempting to insert test enum chunk...")
        result = client.table('code_chunks').insert(test_chunk).execute()
        
        if result.data:
            print("   ✅ SUCCESS! Enum chunks can be inserted.")
            print("   Cleaning up test chunk...")
            
            # Delete the test chunk
            client.table('code_chunks').delete().eq('file_path', 'TEST_ENUM_CHECK.cs').execute()
            print("   ✅ Test chunk deleted")
            return True
        else:
            print("   ⚠️  Insert returned no data (but no error)")
            return False
            
    except Exception as e:
        error_msg = str(e)
        if 'check constraint' in error_msg.lower() or '23514' in error_msg:
            print(f"   ❌ CONSTRAINT STILL BLOCKING ENUM!")
            print(f"   Error: {error_msg}")
            print("\n   The constraint has NOT been updated correctly.")
            print("   Please run the SQL fix above in Supabase SQL Editor.")
            return False
        else:
            print(f"   ⚠️  Other error (may be expected): {e}")
            return None

if __name__ == '__main__':
    print("\n")
    check_constraint()
    
    print("\n" + "=" * 70)
    print("NEXT STEPS")
    print("=" * 70)
    print("\n1. Copy the SQL above")
    print("2. Go to Supabase Dashboard → SQL Editor")
    print("3. Paste and run the SQL")
    print("4. Verify the constraint definition")
    print("5. Run this script again to test: python scripts/fix_chunk_type_constraint.py --test")
    print("\n")
    
    # If --test flag is provided, test the insert
    if '--test' in sys.argv:
        test_enum_insert()

