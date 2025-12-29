"""
Fix pdf_storage_path in database to match actual filenames in Supabase Storage.

This script:
1. Lists all PDFs in gdd_pdfs bucket
2. For each document, finds the best matching PDF file
3. Updates pdf_storage_path in database to match the actual filename
"""

import sys
from pathlib import Path
import re

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from backend.storage.supabase_client import get_supabase_client
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def normalize_for_matching(text):
    """Normalize text for fuzzy matching."""
    if not text:
        return ""
    # Remove .pdf extension
    text = text.replace('.pdf', '')
    # Replace variations: `_-_` -> `_`, `-` -> `_`, multiple underscores -> single
    text = text.replace('_-_', '_').replace('-', '_')
    text = re.sub(r'_+', '_', text)  # Multiple underscores to single
    text = text.strip('_').lower()
    return text


def find_best_match(doc_id, stored_path, files_in_storage):
    """Find the best matching PDF file for a document."""
    file_names = [f.get('name', '') for f in files_in_storage if f.get('name', '').endswith('.pdf')]
    
    # Strategy 1: Exact match with stored path
    if stored_path and stored_path in file_names:
        return stored_path, "EXACT (stored path)"
    
    # Strategy 2: Exact match with doc_id.pdf
    doc_id_filename = f"{doc_id}.pdf"
    if doc_id_filename in file_names:
        return doc_id_filename, "EXACT (doc_id)"
    
    # Strategy 3: Normalized matching
    stored_normalized = normalize_for_matching(stored_path) if stored_path else ""
    doc_id_normalized = normalize_for_matching(doc_id)
    
    best_match = None
    best_score = 0
    
    for file_name in file_names:
        file_normalized = normalize_for_matching(file_name)
        
        # Check if stored path matches
        if stored_normalized and stored_normalized == file_normalized:
            return file_name, "FUZZY (stored path normalized)"
        
        # Check if doc_id matches file name
        if doc_id_normalized:
            # Calculate similarity (length of common normalized string)
            if doc_id_normalized == file_normalized:
                return file_name, "FUZZY (doc_id normalized exact)"
            
            # Check if one contains the other
            if doc_id_normalized in file_normalized or file_normalized in doc_id_normalized:
                common_length = len(set(doc_id_normalized) & set(file_normalized))
                if common_length > best_score:
                    best_score = common_length
                    best_match = file_name
    
    if best_match:
        return best_match, "FUZZY (best match)"
    
    return None, None


def fix_pdf_storage_paths():
    """Fix pdf_storage_path in database to match actual filenames."""
    
    try:
        client = get_supabase_client(use_service_key=True)
    except Exception as e:
        logger.error(f"Failed to get Supabase client: {e}")
        return
    
    logger.info("="*80)
    logger.info("FIXING PDF STORAGE PATHS")
    logger.info("="*80)
    
    # 1. Get all documents
    logger.info("\n📄 Fetching all documents from database...")
    try:
        result = client.table('gdd_documents').select('doc_id, name, pdf_storage_path').execute()
        documents = result.data or []
        logger.info(f"✓ Found {len(documents)} documents")
    except Exception as e:
        logger.error(f"❌ Error fetching documents: {e}")
        return
    
    # 2. List all PDFs in storage
    logger.info("\n📦 Listing all PDFs in gdd_pdfs bucket...")
    try:
        files_in_storage = client.storage.from_('gdd_pdfs').list()
        logger.info(f"✓ Found {len(files_in_storage)} PDF files in storage")
    except Exception as e:
        logger.error(f"❌ Error listing files from storage: {e}")
        return
    
    # 3. Match and update
    logger.info("\n🔗 Matching and updating pdf_storage_path...")
    logger.info("="*80)
    
    updated_count = 0
    no_match_count = 0
    already_correct_count = 0
    
    for doc in documents:
        doc_id = doc.get('doc_id', '')
        stored_path = doc.get('pdf_storage_path', '')
        
        # Find best match
        matched_file, match_type = find_best_match(doc_id, stored_path, files_in_storage)
        
        if not matched_file:
            logger.warning(f"❌ No match found for: {doc_id}")
            logger.warning(f"   Stored path: {stored_path}")
            no_match_count += 1
            continue
        
        # Check if already correct
        if stored_path == matched_file:
            logger.info(f"✓ Already correct: {doc_id} → {matched_file}")
            already_correct_count += 1
            continue
        
        # Update database
        logger.info(f"\n📝 Updating: {doc_id}")
        logger.info(f"   Old path: {stored_path or '(none)'}")
        logger.info(f"   New path: {matched_file} ({match_type})")
        
        try:
            client.table('gdd_documents').update({
                'pdf_storage_path': matched_file
            }).eq('doc_id', doc_id).execute()
            
            logger.info(f"   ✅ Updated successfully")
            updated_count += 1
        except Exception as e:
            logger.error(f"   ❌ Error updating: {e}")
    
    # Summary
    logger.info("\n" + "="*80)
    logger.info("UPDATE SUMMARY")
    logger.info("="*80)
    logger.info(f"Total documents:      {len(documents)}")
    logger.info(f"Updated:               {updated_count}")
    logger.info(f"Already correct:       {already_correct_count}")
    logger.info(f"No match found:        {no_match_count}")
    logger.info("="*80)
    
    # Verify
    logger.info("\n🔍 Verifying updates...")
    try:
        result = client.table('gdd_documents').select('doc_id, pdf_storage_path').execute()
        docs_with_pdf = [d for d in result.data if d.get('pdf_storage_path')]
        
        logger.info(f"✓ Documents with PDF path: {len(docs_with_pdf)}")
        
        if docs_with_pdf:
            logger.info("\nUpdated documents:")
            for doc in docs_with_pdf:
                logger.info(f"  - {doc['doc_id']}: {doc['pdf_storage_path']}")
    except Exception as e:
        logger.error(f"Error verifying: {e}")


if __name__ == "__main__":
    logger.info("Starting PDF storage path fix...")
    logger.info(f"Project root: {PROJECT_ROOT}")
    fix_pdf_storage_paths()
    logger.info("\n✅ Done!")
