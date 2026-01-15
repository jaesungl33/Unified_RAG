"""
Search service for keyword extractor - shared by Tab 1 and Tab 2.
Uses keyword_search_documents RPC function.
"""
from typing import List, Dict, Optional, Any
from backend.storage.supabase_client import get_supabase_client


def keyword_search(
    keyword: str,
    limit: int = 100,
    doc_id_filter: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Search keyword documents using PostgreSQL full-text search.
    This is shared by both Tab 1 (GDD RAG) and Tab 2 (Document Explainer).
    
    Args:
        keyword: Search keyword
        limit: Maximum number of results
        doc_id_filter: Optional document ID to filter by
    
    Returns:
        List of search results with doc_id, doc_name, content, section_heading, relevance
    """
    import logging
    logger = logging.getLogger(__name__)
    
    logger.info("=" * 80)
    logger.info(f"[KEYWORD SEARCH] Function called")
    logger.info(f"[KEYWORD SEARCH] keyword: '{keyword}' (type: {type(keyword)}, length: {len(keyword) if keyword else 0})")
    logger.info(f"[KEYWORD SEARCH] limit: {limit}")
    logger.info(f"[KEYWORD SEARCH] doc_id_filter: {doc_id_filter}")
    
    if not keyword or not keyword.strip():
        logger.warning("[KEYWORD SEARCH] Empty keyword, returning empty list")
        return []
    
    keyword_stripped = keyword.strip()
    logger.info(f"[KEYWORD SEARCH] Stripped keyword: '{keyword_stripped}'")
    
    try:
        logger.info("[KEYWORD SEARCH] Getting Supabase client")
        client = get_supabase_client()
        logger.info(f"[KEYWORD SEARCH] Supabase client obtained: {client is not None}")
        
        logger.info("[KEYWORD SEARCH] Preparing RPC call parameters")
        rpc_params = {
            'search_query': keyword_stripped,
            'match_count': limit,
            'doc_id_filter': doc_id_filter
        }
        logger.info(f"[KEYWORD SEARCH] RPC params: {rpc_params}")
        
        logger.info("[KEYWORD SEARCH] Calling Supabase RPC: keyword_search_documents")
        logger.info(f"[KEYWORD SEARCH] Client type: {type(client)}")
        logger.info(f"[KEYWORD SEARCH] Client URL: {getattr(client, 'supabase_url', 'N/A')}")
        
        try:
            import time
            start_time = time.time()
            logger.info("[KEYWORD SEARCH] Executing RPC call...")
            result = client.rpc(
                'keyword_search_documents',
                rpc_params
            ).execute()
            elapsed_time = time.time() - start_time
            logger.info(f"[KEYWORD SEARCH] RPC call completed in {elapsed_time:.2f} seconds")
        except Exception as rpc_error:
            logger.error(f"[KEYWORD SEARCH] RPC call failed: {rpc_error}")
            logger.error(f"[KEYWORD SEARCH] RPC error type: {type(rpc_error).__name__}")
            logger.error(f"[KEYWORD SEARCH] RPC error args: {rpc_error.args if hasattr(rpc_error, 'args') else 'N/A'}")
            import traceback
            logger.error(f"[KEYWORD SEARCH] RPC traceback:\n{traceback.format_exc()}")
            raise
        logger.info(f"[KEYWORD SEARCH] Result type: {type(result)}")
        logger.info(f"[KEYWORD SEARCH] Result.data type: {type(result.data) if hasattr(result, 'data') else 'No data attr'}")
        logger.info(f"[KEYWORD SEARCH] Result.data is None: {result.data is None if hasattr(result, 'data') else 'N/A'}")
        
        if hasattr(result, 'data'):
            data_length = len(result.data) if result.data else 0
            logger.info(f"[KEYWORD SEARCH] Result.data length: {data_length}")
            if data_length > 0:
                logger.info(f"[KEYWORD SEARCH] First result keys: {list(result.data[0].keys()) if isinstance(result.data[0], dict) else 'Not a dict'}")
        
        final_result = result.data if result.data else []
        logger.info(f"[KEYWORD SEARCH] Returning {len(final_result)} results")
        logger.info("=" * 80)
        return final_result
        
    except Exception as e:
        logger.error("=" * 80)
        logger.error(f"[KEYWORD SEARCH] EXCEPTION: {str(e)}")
        logger.error(f"[KEYWORD SEARCH] Exception type: {type(e).__name__}")
        logger.error(f"[KEYWORD SEARCH] Exception args: {e.args if hasattr(e, 'args') else 'N/A'}")
        import traceback
        logger.error(f"[KEYWORD SEARCH] Full traceback:\n{traceback.format_exc()}")
        logger.error("=" * 80)
        # Return empty list instead of crashing
        return []






