"""
Script to fix file_path in keyword_documents to match actual filenames in storage bucket.
This updates existing records to use the storage filename instead of local file paths.
"""
from backend.storage.supabase_client import get_supabase_client
from werkzeug.utils import secure_filename

def fix_storage_paths():
    """Update file_path in keyword_documents to match storage filenames."""
    print("=" * 60)
    print("Fixing Storage Paths in Database")
    print("=" * 60)
    
    bucket_name = "gdd_pdfs"
    
    try:
        # Get service client for admin access
        service_client = get_supabase_client(use_service_key=True)
        anon_client = get_supabase_client(use_service_key=False)
        
        # Get all files in bucket
        print(f"\n1. Listing files in '{bucket_name}' bucket...")
        files = service_client.storage.from_(bucket_name).list()
        file_names = {f.get('name', '') for f in files}
        print(f"   ✅ Found {len(file_names)} files in bucket")
        
        # Get all documents
        print(f"\n2. Fetching documents from database...")
        result = anon_client.table('keyword_documents').select('doc_id, name, file_path').execute()
        documents = result.data if result.data else []
        print(f"   ✅ Found {len(documents)} documents in database")
        
        # Update each document
        print(f"\n3. Updating file_path for each document...")
        updated_count = 0
        not_found_count = 0
        
        for doc in documents:
            doc_id = doc.get('doc_id', '')
            name = doc.get('name', '')
            current_file_path = doc.get('file_path', '')
            
            # Try multiple matching strategies
            matched_filename = None
            
            # Strategy 1: Try doc_id-based filename
            doc_id_filename = f"{doc_id}.pdf"
            if doc_id_filename in file_names:
                matched_filename = doc_id_filename
            
            # Strategy 2: Try with name (secure_filename format)
            if not matched_filename and name:
                expected_filename = secure_filename(name).replace(" ", "_")
                if expected_filename in file_names:
                    matched_filename = expected_filename
            
            # Strategy 3: Fuzzy matching - normalize and compare
            if not matched_filename:
                # Normalize doc_id for comparison (remove underscores, dashes, case-insensitive)
                doc_id_normalized = doc_id.lower().replace('_', '').replace('-', '').replace(' ', '')
                
                for file_name in file_names:
                    # Remove .pdf extension and normalize
                    file_base = file_name.replace('.pdf', '').lower().replace('_', '').replace('-', '').replace(' ', '')
                    
                    # Check if they match (allowing for some differences)
                    if doc_id_normalized == file_base or doc_id_normalized in file_base or file_base in doc_id_normalized:
                        # Additional check: they should be similar length
                        if abs(len(doc_id_normalized) - len(file_base)) <= 5:
                            matched_filename = file_name
                            break
            
            # Update if we found a match
            if matched_filename:
                try:
                    service_client.table('keyword_documents').update({
                        'file_path': matched_filename
                    }).eq('doc_id', doc_id).execute()
                    print(f"   ✅ Updated {doc_id}")
                    print(f"      Old: {current_file_path[:60]}...")
                    print(f"      New: {matched_filename}")
                    updated_count += 1
                except Exception as e:
                    print(f"   ❌ Failed to update {doc_id}: {e}")
            else:
                print(f"   ⚠️  No matching file found for {doc_id}")
                print(f"      Tried: {doc_id_filename}")
                if name:
                    print(f"      Tried: {secure_filename(name).replace(' ', '_')}")
                not_found_count += 1
        
        print(f"\n" + "=" * 60)
        print(f"✅ Update complete!")
        print(f"   Updated: {updated_count} documents")
        print(f"   Not found: {not_found_count} documents")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    fix_storage_paths()

