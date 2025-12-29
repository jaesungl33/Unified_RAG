"""
Diagnostic script to check section filtering and chunk retrieval.
Compares Supabase chunks with actual markdown content.
"""

import os
import sys
from supabase import create_client
from dotenv import load_dotenv
import json

# Add backend to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

from gdd_query_parser import parse_section_targets
from storage.gdd_supabase_storage import get_gdd_top_chunks_supabase

load_dotenv()

# Initialize Supabase
supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_ANON_KEY")
supabase = create_client(supabase_url, supabase_key)


def read_markdown_file(doc_id: str) -> str:
    """Find and read the actual markdown file."""
    # Search in gdd_data/markdown_output
    markdown_dir = os.path.join(os.path.dirname(__file__), 'gdd_data', 'markdown_output')
    
    # Try to find file matching doc_id
    for root, dirs, files in os.walk(markdown_dir):
        for file in files:
            if file.endswith('.md'):
                # Normalize filename to match doc_id format
                filename_no_ext = file.replace('.md', '')
                if doc_id in file or filename_no_ext.replace(' ', '_') in doc_id:
                    filepath = os.path.join(root, file)
                    print(f"📄 Found markdown file: {filepath}")
                    with open(filepath, 'r', encoding='utf-8') as f:
                        return f.read()
    
    print(f"❌ Could not find markdown file for doc_id: {doc_id}")
    return None


def extract_section_from_markdown(markdown_content: str, section_name: str) -> str:
    """Extract a specific section from markdown content."""
    lines = markdown_content.split('\n')
    section_lines = []
    capturing = False
    
    for line in lines:
        # Check if this is the target section header
        if line.strip().startswith('#') and section_name.lower() in line.lower():
            capturing = True
            section_lines.append(line)
            continue
        
        # Stop if we hit another section header of same or higher level
        if capturing and line.strip().startswith('#'):
            break
        
        if capturing:
            section_lines.append(line)
    
    return '\n'.join(section_lines)


def get_chunks_from_supabase(doc_id: str, section_name: str = None):
    """Query Supabase directly for chunks."""
    print(f"\n🔍 Querying Supabase for doc_id: {doc_id}")
    if section_name:
        print(f"   Section filter: {section_name}")
    
    # Query all chunks for this document
    query = supabase.table('gdd_chunks').select('*').eq('doc_id', doc_id)
    
    response = query.execute()
    
    print(f"✅ Found {len(response.data)} total chunks for this doc_id")
    
    if section_name:
        # Filter by section
        section_chunks = []
        for chunk in response.data:
            metadata = chunk.get('metadata', {})
            numbered_header = metadata.get('numbered_header', '')
            section_path = chunk.get('section_path', '')
            
            # Check if section matches
            if section_name.lower() in numbered_header.lower() or \
               section_name.lower() in section_path.lower():
                section_chunks.append(chunk)
        
        print(f"📊 Filtered to {len(section_chunks)} chunks matching section: {section_name}")
        return section_chunks
    
    return response.data


def test_query(query_text: str):
    """Test the full query pipeline."""
    print(f"\n{'='*80}")
    print(f"🧪 Testing query: {query_text}")
    print(f"{'='*80}")
    
    # Parse the query
    pure_query, filters = parse_section_targets(query_text)
    
    print(f"\n📝 Parsed Query:")
    print(f"   Pure query: {pure_query}")
    print(f"   Filters: {json.dumps(filters, indent=2, ensure_ascii=False)}")
    
    # Get the doc_id from filters
    doc_ids = filters.get('doc_id_filter', [])
    section_paths = filters.get('section_path_filter', [])
    
    if not doc_ids:
        print("❌ No doc_id found in query!")
        return
    
    doc_id = doc_ids[0]
    section_name = section_paths[0] if section_paths else None
    
    # 1. Read actual markdown
    print(f"\n{'='*80}")
    print("1️⃣  ACTUAL MARKDOWN CONTENT")
    print(f"{'='*80}")
    markdown_content = read_markdown_file(doc_id)
    if markdown_content and section_name:
        section_content = extract_section_from_markdown(markdown_content, section_name)
        print(f"\n📄 Section '{section_name}' from markdown:")
        print(f"{'-'*80}")
        print(section_content[:500] + "..." if len(section_content) > 500 else section_content)
        print(f"{'-'*80}")
    
    # 2. Check Supabase chunks
    print(f"\n{'='*80}")
    print("2️⃣  SUPABASE CHUNKS")
    print(f"{'='*80}")
    chunks = get_chunks_from_supabase(doc_id, section_name)
    
    for i, chunk in enumerate(chunks[:3], 1):  # Show first 3 chunks
        print(f"\n📦 Chunk {i}:")
        print(f"   chunk_id: {chunk.get('chunk_id')}")
        print(f"   doc_id: {chunk.get('doc_id')}")
        print(f"   section_path: {chunk.get('section_path')}")
        metadata = chunk.get('metadata', {})
        print(f"   numbered_header: {metadata.get('numbered_header')}")
        print(f"   Content preview:")
        content = chunk.get('content', '')
        print(f"   {content[:300]}...")
    
    # 3. Test actual retrieval
    print(f"\n{'='*80}")
    print("3️⃣  ACTUAL RETRIEVAL (via get_gdd_top_chunks_supabase)")
    print(f"{'='*80}")
    
    # This would require embedding, so let's just show what would be retrieved
    print(f"   Would call get_gdd_top_chunks_supabase with:")
    print(f"   - query_embedding: [generated from '{pure_query}']")
    print(f"   - filters: {filters}")
    

def main():
    """Run diagnostics."""
    print("="*80)
    print("🔧 GDD SECTION FILTERING DIAGNOSTIC TOOL")
    print("="*80)
    
    # Test cases
    test_queries = [
        "@[Asset,_UI]_[Tank_War]_Mode_Selection_Design.md @1. Mụcđíchthiếtkế extract this",
        "@[Asset,_UI]_[Tank_War]_Mode_Selection_Design.md @4. Thànhphần what are the components",
        "@[Asset,_UI]_[Tank_War]_Mode_Selection_Design.md @6. Notes extract this",
    ]
    
    for query in test_queries:
        test_query(query)
        print("\n")


if __name__ == "__main__":
    main()

