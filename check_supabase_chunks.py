"""
Simple script to check what's actually stored in Supabase for Mode_Selection_Design
"""

import os
import sys

# Add backend to path
sys.path.insert(0, os.path.dirname(__file__))

from backend.storage.gdd_supabase_storage import get_supabase_client

# Get Supabase client from existing backend
supabase = get_supabase_client()

# Query for Mode_Selection_Design document
doc_id = "Asset_UI_Tank_War_Mode_Selection_Design"

print(f"Querying Supabase for doc_id: {doc_id}")
print("="*80)

# Get all chunks for this document
result = supabase.table('gdd_chunks').select('*').eq('doc_id', doc_id).execute()

print(f"\nTotal chunks found: {len(result.data)}")
print("="*80)

# Show first few chunks
for i, chunk in enumerate(result.data[:5], 1):
    print(f"\nChunk {i}:")
    print(f"  chunk_id: {chunk.get('chunk_id')}")
    print(f"  doc_id: {chunk.get('doc_id')}")
    print(f"  section_path: {chunk.get('section_path')}")
    metadata = chunk.get('metadata', {})
    print(f"  numbered_header: {metadata.get('numbered_header')}")
    print(f"  content preview:")
    content = chunk.get('content', '')
    print(f"    {content[:200]}...")
    print()

# Now check Section 1
print("\n" + "="*80)
print("Filtering for Section '1. Mục đích thiết kế'")
print("="*80)

section_chunks = [
    chunk for chunk in result.data
    if 'mục' in chunk.get('section_path', '').lower() or
       'mục' in chunk.get('metadata', {}).get('numbered_header', '').lower()
]

print(f"\nFound {len(section_chunks)} chunks for Section 1")

for i, chunk in enumerate(section_chunks[:3], 1):
    print(f"\nSection 1 Chunk {i}:")
    print(f"  chunk_id: {chunk.get('chunk_id')}")
    print(f"  section_path: {chunk.get('section_path')}")
    metadata = chunk.get('metadata', {})
    print(f"  numbered_header: {metadata.get('numbered_header')}")
    print(f"  content:")
    content = chunk.get('content', '')
    print(f"    {content[:300]}")
    print()
    
    # Check if content mentions "Garage" (wrong) or "mode" (correct)
    if 'garage' in content.lower():
        print("  ⚠️  WARNING: Content mentions 'Garage' - this is WRONG for Mode_Selection_Design!")
    if 'mode' in content.lower():
        print("  ✓ Content mentions 'mode' - this looks correct!")

