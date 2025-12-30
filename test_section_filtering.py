"""
Test script to check section filtering logic
"""
from backend.gdd_query_parser import parse_section_targets, extract_numbered_section_from_query
from backend.storage.gdd_supabase_storage import _strip_section_number

# Test queries
test_queries = [
    "@6. Notes extract this",
    "@4. Thànhphần extract this",
    "@Notes extract this",
    "@Thànhphần what are the components",
]

print("=" * 80)
print("Testing Section Filtering Logic")
print("=" * 80)

for query in test_queries:
    print(f"\nQuery: {query}")
    cleaned, filters = parse_section_targets(query)
    print(f"  Cleaned query: {cleaned}")
    print(f"  Filters: {filters}")
    
    if 'section_path_filter' in filters:
        raw = filters['section_path_filter']
        stripped = _strip_section_number(raw)
        print(f"  Section filter: '{raw}' -> stripped: '{stripped}'")
    
    # Also test numbered section extraction
    numbered = extract_numbered_section_from_query(cleaned)
    if numbered:
        stripped_numbered = _strip_section_number(numbered)
        print(f"  Extracted numbered section: '{numbered}' -> stripped: '{stripped_numbered}'")

print("\n" + "=" * 80)
print("Testing _strip_section_number function")
print("=" * 80)

test_sections = [
    "6. Notes",
    "4. Thànhphần",
    "Notes",
    "Thànhphần",
    "1. Mụcđíchthiếtkế",
    "4.1 Subsection",
]

for section in test_sections:
    stripped = _strip_section_number(section)
    print(f"  '{section}' -> '{stripped}'")

print("\n" + "=" * 80)

