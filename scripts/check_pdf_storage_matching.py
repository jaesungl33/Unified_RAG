"""
Script to check indexed markdown documents and match them with PDFs in Supabase Storage.

This script:
1. Lists all indexed documents from gdd_documents table
2. Lists all PDFs in the gdd_pdfs bucket
3. Matches documents with PDFs and shows mismatches
"""

import sys
import os
from pathlib import Path
import requests

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from backend.storage.supabase_client import get_supabase_client, get_gdd_document_pdf_url
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def normalize_filename(filename: str) -> str:
    """Normalize filename for comparison (remove spaces, underscores, dashes, case-insensitive)"""
    return filename.lower().replace('_', '').replace('-', '').replace(' ', '').replace('.pdf', '')


def check_pdf_storage_matching():
    """Check all indexed documents and their PDF storage status"""
    try:
        client = get_supabase_client()  # Anon key for database queries
        storage_client = get_supabase_client(use_service_key=True)  # Service key for storage operations
    except Exception as e:
        logger.error(f"Failed to get Supabase client: {e}")
        return
    
    logger.info("=" * 80)
    logger.info("PDF STORAGE MATCHING DIAGNOSTIC")
    logger.info("=" * 80)
    
    # 1. Get all documents from database
    logger.info("\n📄 Fetching all indexed documents from database...")
    try:
        docs_result = client.table('gdd_documents').select('doc_id, name, file_path, pdf_storage_path').order('doc_id').execute()
        documents = docs_result.data if docs_result.data else []
        logger.info(f"✓ Found {len(documents)} indexed document(s)")
    except Exception as e:
        logger.error(f"❌ Error fetching documents: {e}")
        return
    
    # 2. List all PDFs in storage bucket (use service key for admin access)
    logger.info("\n📦 Listing all PDFs in gdd_pdfs bucket...")
    try:
        files = storage_client.storage.from_('gdd_pdfs').list()
        storage_files = [f.get('name', '') for f in files] if files else []
        logger.info(f"✓ Found {len(storage_files)} PDF file(s) in storage")
        
        if storage_files:
            logger.info("\n  Files in storage:")
            for i, filename in enumerate(storage_files[:10], 1):
                logger.info(f"    {i}. {filename}")
            if len(storage_files) > 10:
                logger.info(f"    ... and {len(storage_files) - 10} more")
    except Exception as e:
        logger.error(f"❌ Error listing storage files: {e}")
        storage_files = []
    
    # 3. Match documents with PDFs
    logger.info("\n" + "=" * 80)
    logger.info("🔍 MATCHING DOCUMENTS WITH PDFs")
    logger.info("=" * 80)
    
    matches = []
    mismatches = []
    no_pdf_storage_path = []
    
    for doc in documents:
        doc_id = doc.get('doc_id', 'N/A')
        stored_path = doc.get('pdf_storage_path')
        doc_name = doc.get('name', 'N/A')
        
        # Normalize doc_id for matching
        doc_id_normalized = normalize_filename(doc_id)
        
        # Try to find matching PDF
        matched_file = None
        match_type = None
        
        if stored_path:
            # Check exact match with stored path
            if stored_path in storage_files:
                matched_file = stored_path
                match_type = "EXACT (stored path)"
            else:
                # Try fuzzy match
                stored_normalized = normalize_filename(stored_path)
                for file_name in storage_files:
                    file_normalized = normalize_filename(file_name)
                    if stored_normalized == file_normalized:
                        matched_file = file_name
                        match_type = "FUZZY (stored path)"
                        break
        else:
            # No stored path, try doc_id-based matching
            doc_id_filename = f"{doc_id}.pdf"
            if doc_id_filename in storage_files:
                matched_file = doc_id_filename
                match_type = "EXACT (doc_id)"
            else:
                # Try fuzzy match with doc_id
                for file_name in storage_files:
                    file_normalized = normalize_filename(file_name)
                    if doc_id_normalized == file_normalized:
                        matched_file = file_name
                        match_type = "FUZZY (doc_id)"
                        break
        
        # Test URL generation (use anon key for public URLs)
        pdf_url = None
        if matched_file:
            try:
                pdf_url = client.storage.from_('gdd_pdfs').get_public_url(matched_file)
                # Verify URL is accessible
                response = requests.head(pdf_url, timeout=5)
                if response.status_code != 200:
                    pdf_url = None  # URL doesn't work
            except Exception as e:
                logger.debug(f"Error generating/verifying URL for {matched_file}: {e}")
                pdf_url = None
        
        # Categorize result
        if matched_file and pdf_url:
            matches.append({
                'doc_id': doc_id,
                'name': doc_name,
                'stored_path': stored_path,
                'matched_file': matched_file,
                'match_type': match_type,
                'url': pdf_url
            })
        elif stored_path:
            mismatches.append({
                'doc_id': doc_id,
                'name': doc_name,
                'stored_path': stored_path,
                'reason': 'Stored path does not match any file in storage'
            })
        else:
            no_pdf_storage_path.append({
                'doc_id': doc_id,
                'name': doc_name,
                'reason': 'No pdf_storage_path stored in database'
            })
    
    # 4. Display results
    logger.info(f"\n✅ MATCHES: {len(matches)} document(s) with working PDFs")
    if matches:
        for match in matches:
            logger.info(f"\n  ✓ {match['doc_id']}")
            logger.info(f"    Name: {match['name']}")
            logger.info(f"    Stored path: {match['stored_path']}")
            logger.info(f"    Matched file: {match['matched_file']} ({match['match_type']})")
            logger.info(f"    URL: {match['url']}")
    
    logger.info(f"\n⚠️  MISMATCHES: {len(mismatches)} document(s) with stored path but no matching file")
    if mismatches:
        for mismatch in mismatches:
            logger.info(f"\n  ⚠ {mismatch['doc_id']}")
            logger.info(f"    Name: {mismatch['name']}")
            logger.info(f"    Stored path: {mismatch['stored_path']}")
            logger.info(f"    Reason: {mismatch['reason']}")
    
    logger.info(f"\n❌ NO PDF STORAGE PATH: {len(no_pdf_storage_path)} document(s) without pdf_storage_path")
    if no_pdf_storage_path:
        for doc in no_pdf_storage_path:
            logger.info(f"\n  ❌ {doc['doc_id']}")
            logger.info(f"    Name: {doc['name']}")
            logger.info(f"    Reason: {doc['reason']}")
    
    # 5. Test get_gdd_document_pdf_url function
    logger.info("\n" + "=" * 80)
    logger.info("🧪 TESTING get_gdd_document_pdf_url() FUNCTION")
    logger.info("=" * 80)
    
    test_docs = documents[:5]  # Test first 5 documents
    for doc in test_docs:
        doc_id = doc.get('doc_id')
        logger.info(f"\n  Testing: {doc_id}")
        try:
            url = get_gdd_document_pdf_url(doc_id)
            if url:
                logger.info(f"    ✓ URL generated: {url}")
            else:
                logger.info(f"    ✗ No URL returned")
        except Exception as e:
            logger.info(f"    ✗ Error: {e}")
    
    # 6. Summary
    logger.info("\n" + "=" * 80)
    logger.info("📊 SUMMARY")
    logger.info("=" * 80)
    logger.info(f"Total indexed documents: {len(documents)}")
    logger.info(f"Documents with working PDFs: {len(matches)}")
    logger.info(f"Documents with mismatched paths: {len(mismatches)}")
    logger.info(f"Documents without pdf_storage_path: {len(no_pdf_storage_path)}")
    logger.info(f"Total PDFs in storage: {len(storage_files)}")
    
    # 7. Recommendations
    logger.info("\n" + "=" * 80)
    logger.info("💡 RECOMMENDATIONS")
    logger.info("=" * 80)
    
    if mismatches:
        logger.info(f"\n⚠️  {len(mismatches)} document(s) have pdf_storage_path but file doesn't exist:")
        logger.info("   - Re-upload the PDFs to storage with the correct filenames")
        logger.info("   - Or update pdf_storage_path in database to match actual filenames")
    
    if no_pdf_storage_path:
        logger.info(f"\n❌ {len(no_pdf_storage_path)} document(s) are missing pdf_storage_path:")
        logger.info("   - Re-index these documents to store pdf_storage_path")
        logger.info("   - Or manually update the database with correct pdf_storage_path")
    
    if len(matches) == len(documents):
        logger.info("\n✅ All documents have working PDFs!")
    else:
        logger.info(f"\n⚠️  {len(documents) - len(matches)} document(s) need attention")
    
    logger.info("\n" + "=" * 80)


if __name__ == '__main__':
    check_pdf_storage_matching()

