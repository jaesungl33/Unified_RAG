"""
Requirement-to-code matching service using Supabase storage.
Adapts gdd_rag_backbone/gdd/requirement_matching.py for Supabase.
"""

import asyncio
import json
import logging
from typing import List, Dict, Optional, Any
from pathlib import Path

# Project imports
from gdd_rag_backbone.gdd.schemas import GddRequirement
from backend.storage.supabase_client import vector_search_code_chunks, vector_search_gdd_chunks
from backend.storage.gdd_supabase_storage import get_gdd_top_chunks_supabase
from gdd_rag_backbone.llm_providers import QwenProvider, make_llm_model_func, make_embedding_func

logger = logging.getLogger(__name__)


async def search_code_for_requirement_supabase(
    requirement: GddRequirement,
    provider: QwenProvider,
    top_k: int = 12
) -> List[Dict[str, Any]]:
    """
    Search code chunks in Supabase that might implement the requirement.
    Uses requirement description/summary/acceptance_criteria as queries.
    
    Args:
        requirement: The GDD requirement to search for
        provider: LLM provider for embeddings
        top_k: Maximum number of results to return
    
    Returns:
        List of matching code chunks with similarity scores
    """
    # Generate multiple query variations from requirement
    # Also create technical variations to bridge design-to-code terminology gap
    queries = []
    
    # Vietnamese technical terms - both Vietnamese and English equivalents
    # Qwen embedding model supports Vietnamese natively, so we can use both
    vietnamese_technical_terms = {
        # UI/Display terms
        "hiển thị": ["hiển thị", "display", "show", "UI", "Canvas", "Text", "Image", "Sprite"],
        "giao diện": ["giao diện", "UI", "interface", "screen", "Canvas", "Panel"],
        "màn hình": ["màn hình", "screen", "UI", "Canvas", "Panel"],
        "thông tin": ["thông tin", "info", "information", "data", "display"],
        
        # Interaction terms
        "nút": ["nút", "button", "click", "OnClick", "Event", "Button"],
        "nhấn": ["nhấn", "press", "click", "tap", "OnClick"],
        "tương tác": ["tương tác", "interact", "interaction", "button", "click"],
        "chọn": ["chọn", "select", "choose", "selection", "Select", "Choose"],
        "khóa": ["khóa", "lock", "confirm", "Lock", "Confirm"],
        
        # Game-specific terms
        "tank": ["tank", "vehicle", "character", "Tank", "Vehicle"],
        "garage": ["garage", "customization", "Garage", "Customization"],
        "trận đấu": ["trận đấu", "match", "battle", "game", "Match", "Battle"],
        "phần thưởng": ["phần thưởng", "reward", "prize", "Reward", "Prize"],
        "nhận": ["nhận", "collect", "receive", "get", "Collect", "Receive"],
        "mua": ["mua", "purchase", "buy", "shop", "store", "Purchase", "Buy"],
        "mặc định": ["mặc định", "default", "selected", "Default", "Selected"],
        
        # Stats/Data terms
        "thống kê": ["thống kê", "stats", "statistics", "display", "Stats", "Statistics"],
        "thông số": ["thông số", "stats", "parameters", "data", "Stats"],
        "chi tiết": ["chi tiết", "detail", "info", "information", "Detail"],
        "xem": ["xem", "view", "show", "display", "View", "Show"],
    }
    
    def add_technical_variations(text: str) -> list:
        """Add technical keyword variations for Vietnamese/design terms.
        Qwen embedding model supports Vietnamese natively, so we use both Vietnamese and English terms."""
        variations = [text]  # Always include original text
        text_lower = text.lower()
        
        # Add technical terms based on Vietnamese keywords
        # Include both Vietnamese and English terms since Qwen supports both
        for vn_term, tech_terms_list in vietnamese_technical_terms.items():
            if vn_term in text_lower:
                # Create variations with both Vietnamese and English technical terms
                tech_terms_str = " ".join(tech_terms_list)
                variations.append(f"{text} {tech_terms_str}")
                # Also add English-only version for code that uses English
                english_terms = [t for t in tech_terms_list if not any(c in 'àáảãạăằắẳẵặâầấẩẫậèéẻẽẹêềếểễệìíỉĩịòóỏõọôồốổỗộơờớởỡợùúủũụưừứửữựỳýỷỹỵđ' for c in t)]
                if english_terms:
                    variations.append(f"{text} {' '.join(english_terms)}")
        
        # Add technical terms based on English keywords (for English requirements)
        if "move" in text_lower or "movement" in text_lower:
            variations.append(f"{text} Input.GetKey transform.position velocity")
        if "display" in text_lower or "show" in text_lower or "ui" in text_lower:
            variations.append(f"{text} UI Canvas Text Image Sprite")
        if "button" in text_lower or "click" in text_lower or "press" in text_lower:
            variations.append(f"{text} Button OnClick Event")
        if "select" in text_lower or "choose" in text_lower:
            variations.append(f"{text} Selection Choose Select")
        if "stats" in text_lower or "statistics" in text_lower:
            variations.append(f"{text} Stats Statistics Display UI")
        if "reward" in text_lower:
            variations.append(f"{text} Reward Prize Collect")
        if "garage" in text_lower:
            variations.append(f"{text} Garage Customization Tank")
        if "tank" in text_lower:
            variations.append(f"{text} Tank Vehicle Character")
        
        return variations
    
    if requirement.description:
        queries.extend(add_technical_variations(requirement.description))
    if requirement.summary:
        queries.extend(add_technical_variations(requirement.summary))
    if requirement.acceptance_criteria:
        queries.extend(add_technical_variations(requirement.acceptance_criteria))
    if requirement.title:
        queries.extend(add_technical_variations(requirement.title))
    
    # Deduplicate while preserving order
    seen = set()
    unique_queries = []
    for q in queries:
        if q not in seen:
            seen.add(q)
            unique_queries.append(q)
    queries = unique_queries
    
    if not queries:
        logger.warning(f"No query text available for requirement {requirement.id}")
        return []
    
    # Get embedding function
    embedding_func = make_embedding_func(provider)
    
    # Search for each query and merge results
    all_results = []
    seen_chunk_ids = set()
    
    # Use more queries but limit to avoid rate limits
    for query in queries[:5]:  # Increased from 3 to 5 to get better coverage
        try:
            # Generate embedding for query
            query_embedding = embedding_func([query])[0]
            
            # Search code chunks with lower threshold to catch more potential matches
            # Lower threshold helps find code that uses different terminology
            chunks = vector_search_code_chunks(
                query_embedding=query_embedding,
                limit=top_k * 3,  # Get even more candidates for better coverage
                threshold=0.12,  # Very low threshold (0.12) to catch all semantic equivalents
            )
            
            # Filter out editor scripts and test files - focus on game code
            filtered_chunks = []
            for chunk in chunks:
                file_path = chunk.get('file_path', '')
                # Skip editor scripts, test files, and plugin demos
                if any(skip in file_path.lower() for skip in ['/editor/', '/test/', '/demo/', 'plugins/', 'editor/', 'findandreplace']):
                    continue
                # Prefer game code paths
                if any(game_path in file_path.lower() for game_path in ['_gameui', '_gamemodules', '_gameassets']):
                    filtered_chunks.append(chunk)
                else:
                    # Include other code but with lower priority
                    filtered_chunks.append(chunk)
            
            chunks = filtered_chunks
            
            for chunk in chunks:
                # Create unique ID for chunk
                chunk_id = str(chunk.get('id', '')) or (
                    chunk.get('file_path', '') + ':' + 
                    chunk.get('class_name', '') + '.' + 
                    chunk.get('method_name', '')
                )
                
                if chunk_id not in seen_chunk_ids:
                    seen_chunk_ids.add(chunk_id)
                    # Normalize chunk format to match expected structure
                    normalized = {
                        'chunk_id': chunk_id,
                        'file_path': chunk.get('file_path'),
                        'class_name': chunk.get('class_name'),
                        'method_name': chunk.get('method_name'),
                        'content': chunk.get('source_code', '') or chunk.get('code', ''),
                        'code': chunk.get('code', ''),
                        'score': chunk.get('similarity', 0.0),
                        'chunk_type': chunk.get('chunk_type'),
                        'metadata': chunk.get('metadata', {})
                    }
                    all_results.append(normalized)
        except Exception as e:
            logger.error(f"Error searching for query '{query[:50]}...': {e}")
            continue
    
    # Sort by score and return top_k
    all_results.sort(key=lambda x: x.get('score', 0), reverse=True)
    return all_results[:top_k]


async def classify_requirement_implementation(
    requirement: GddRequirement,
    code_chunks: List[Dict[str, Any]],
    llm_func
) -> Dict[str, Any]:
    """
    Use LLM to classify if code chunks implement the requirement.
    
    Args:
        requirement: The GDD requirement
        code_chunks: List of candidate code chunks
        llm_func: Async LLM function
    
    Returns:
        {
            "requirement_id": "...",
            "status": "implemented|partially_implemented|not_implemented",
            "confidence": 0.0-1.0,
            "evidence": [...]
        }
    """
    system_prompt = (
        "You are a senior gameplay engineer evaluating if game code implements a design requirement. "
        "You understand both Vietnamese and English natively. "
        "CRITICAL: Look for FUNCTIONAL EQUIVALENCE, not exact text matches. "
        "Requirements are written in design/user language (often Vietnamese), while code uses technical terms (often English). "
        "If the code achieves the SAME FUNCTIONALITY as the requirement (even with completely different terminology or language), "
        "classify it as 'implemented' or 'partially_implemented'. "
        "Be VERY GENEROUS in recognizing functional equivalence. "
        "IMPORTANT: If this is a fully implemented game, most requirements should be 'implemented' or 'partially_implemented'. "
        "Only use 'not_implemented' if the functionality is ABSOLUTELY missing or the code is completely unrelated. "
        "Vietnamese-English equivalence examples: "
        "- 'Hiển thị thông tin' = display information = UI Canvas, Text components, info panels → IMPLEMENTED "
        "- 'Nút nhấn' = button press = Button.OnClick, Event handlers → IMPLEMENTED "
        "- 'Chọn tank' = select tank = Selection logic, ChooseTank methods → IMPLEMENTED "
        "- 'Giao diện dễ hiểu' = easy-to-use interface = ANY UI code, buttons, menus → IMPLEMENTED "
        "- 'Mua vật phẩm' = purchase item = Shop.Buy(), Purchase(), any shop/buy code → IMPLEMENTED "
        "- 'Phần thưởng' = reward = Reward, Prize, any reward-related code → IMPLEMENTED "
        "- 'Hiển thị rõ ràng' = clear display = ANY UI display code → IMPLEMENTED "
        "- 'Nút Back hoạt động' = back button works = ANY button/back navigation code → IMPLEMENTED "
        "When in doubt, prefer 'partially_implemented' or 'implemented' over 'not_implemented'. "
        "If code exists that could reasonably implement the requirement, mark it as at least 'partially_implemented'."
    )
    
    requirement_json = json.dumps(requirement.to_dict(), indent=2)
    
    if code_chunks:
        code_context = "\n\n".join([
            f"[File: {chunk.get('file_path', 'unknown')}]\n"
            f"[Class: {chunk.get('class_name', 'N/A')}.{chunk.get('method_name', 'N/A')}]\n"
            f"Score: {chunk.get('score', 0.0):.3f}\n"
            f"{chunk.get('content', chunk.get('code', ''))[:1500]}"
            for chunk in code_chunks[:8]
        ])
    else:
        code_context = "No relevant code chunks were retrieved."
    
    user_prompt = f"""
Requirement (from Game Design Document):
{requirement_json}

Candidate Code (from actual implementation):
{code_context}

Evaluate if the code implements the requirement. Consider:
1. FUNCTIONAL EQUIVALENCE: Does the code achieve the same goal as the requirement?
2. Language difference: Requirements may be in Vietnamese, code in English - they can still match functionally
3. Terminology difference: Design docs use user-facing language, code uses technical terms
4. Implementation approach: Code might implement it differently but achieve the same result
5. Partial implementation: Some features might be present but not all acceptance criteria met

Vietnamese-English equivalence examples:
- Requirement: "Hiển thị thông tin" (display information)
  Code: "Canvas", "Text.text = info", "UI elements" → IMPLEMENTED
- Requirement: "Nút nhấn" (button press)
  Code: "Button.OnClick", "Event handlers" → IMPLEMENTED
- Requirement: "Chọn tank" (select tank)
  Code: "ChooseTank()", "Selection logic" → IMPLEMENTED
- Requirement: "Mua vật phẩm" (purchase item)
  Code: "Shop.Buy()", "Purchase()" → IMPLEMENTED

English-only examples:
- Requirement: "Player can move with WASD keys" 
  Code: "Input.GetKey(KeyCode.W)" → IMPLEMENTED
- Requirement: "Smooth movement"
  Code: "transform.position += velocity * Time.deltaTime" → IMPLEMENTED
- Requirement: "Display player health"
  Code: "healthBar.value = currentHealth" → IMPLEMENTED

Classify the implementation status:
- "implemented": Code fully achieves the requirement's functionality (use this generously if code clearly does what the requirement asks)
- "partially_implemented": Code achieves some but not all aspects of the requirement (use this if code is related but might be incomplete)
- "not_implemented": Functionality is ABSOLUTELY missing or code is completely unrelated (use this sparingly - only if there's NO related code at all)

IMPORTANT: If you find ANY code that could reasonably implement the requirement, prefer 'implemented' or 'partially_implemented' over 'not_implemented'.

Return ONLY JSON:
{{
  "requirement_id": "{requirement.id}",
  "status": "implemented|partially_implemented|not_implemented",
  "confidence": 0.0-1.0,
  "evidence": [
    {{
      "file": "path/to/file.ext",
      "class": "ClassName",
      "method": "MethodName",
      "reason": "How this code functionally satisfies or fails the requirement (focus on functionality, not terminology)"
    }}
  ]
}}
"""
    
    try:
        response = await llm_func(
            prompt=user_prompt,
            system_prompt=system_prompt,
            temperature=0.1
        )
        text = response.strip()
        if text.startswith("```"):
            lines = text.split("\n")
            text = "\n".join(lines[1:-1]) if lines[-1].strip() == "```" else "\n".join(lines[1:])
        
        result = json.loads(text)
        result.setdefault("requirement_id", requirement.id)
        result.setdefault("evidence", [])
        result.setdefault("confidence", 0.5)
        return result
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse LLM response: {e}")
        return {
            "requirement_id": requirement.id,
            "status": "error",
            "confidence": 0.0,
            "evidence": [{"reason": f"LLM response parsing error: {str(e)[:100]}"}]
        }
    except Exception as e:
        logger.error(f"Error in LLM classification: {e}")
        return {
            "requirement_id": requirement.id,
            "status": "error",
            "confidence": 0.0,
            "evidence": [{"reason": f"LLM error: {str(e)[:100]}"}]
        }


async def evaluate_requirement_coverage(
    requirement: GddRequirement,
    provider: Optional[QwenProvider] = None,
    top_k: int = 12
) -> Dict[str, Any]:
    """
    Main function: Evaluate if a requirement is implemented in code.
    
    Args:
        requirement: The GDD requirement to evaluate
        provider: Optional LLM provider (defaults to QwenProvider)
        top_k: Number of code chunks to retrieve
    
    Returns:
        {
            "requirement_id": "...",
            "status": "implemented|partially_implemented|not_implemented",
            "confidence": 0.0-1.0,
            "evidence": [...],
            "matched_chunks": [...]
        }
    """
    active_provider = provider or QwenProvider()
    
    logger.info(f"Evaluating requirement: {requirement.id} - {requirement.title[:50]}")
    
    # Step 1: Search for relevant code chunks
    code_chunks = await search_code_for_requirement_supabase(
        requirement,
        active_provider,
        top_k=top_k
    )
    
    logger.info(f"Found {len(code_chunks)} candidate code chunks for requirement {requirement.id}")
    
    # Step 2: Classify implementation status
    if not code_chunks:
        return {
            "requirement_id": requirement.id,
            "status": "not_implemented",
            "confidence": 0.0,
            "evidence": [{"reason": "No relevant code found"}],
            "matched_chunks": []
        }
    
    llm_func = make_llm_model_func(active_provider)
    classification = await classify_requirement_implementation(
        requirement,
        code_chunks,
        llm_func
    )
    
    classification["matched_chunks"] = code_chunks[:5]  # Include top 5 chunks
    return classification


async def extract_requirements_from_doc_supabase(
    doc_id: str,
    provider: QwenProvider,
    llm_func,
    max_retries: int = 3
) -> Dict[str, List[dict]]:
    """
    Extract requirements from GDD document using Supabase storage.
    This is a Supabase-compatible version of extract_all_requirements.
    """
    # Use Supabase-compatible chunk retrieval
    query = "Extract ALL objects, systems, rules, and requirements described in this document."
    
    last_error = None
    for attempt in range(max_retries):
        try:
            # Get chunks from Supabase - use more chunks for better extraction
            chunks = get_gdd_top_chunks_supabase(
                doc_ids=[doc_id],
                question=query,
                provider=provider,
                top_k=20,  # Get more chunks for better context
            )
            
            if not chunks:
                raise ValueError(f"No chunks found for document {doc_id}")
            
            # Build context from chunks (limit total length to avoid token limits)
            context_parts = []
            total_length = 0
            max_length = 15000  # Limit context to avoid token limits
            
            for chunk in chunks:
                content = chunk.get("content", "")
                if total_length + len(content) > max_length:
                    # Add partial content if we're close to limit
                    remaining = max_length - total_length
                    if remaining > 500:  # Only add if we have meaningful space
                        context_parts.append(content[:remaining])
                    break
                context_parts.append(content)
                total_length += len(content)
            
            context = "\n\n".join(context_parts)
            
            if not context.strip():
                raise ValueError("No context available for extraction")
            
            # Use the same extraction template as the original function
            from gdd_rag_backbone.gdd.extraction import MASTER_EXTRACTION_TEMPLATE
            
            system_prompt = (
                "You convert Game Design Documents into structured technical data. "
                "Return ONLY JSON. Do NOT invent anything. Use null for missing values."
            )
            prompt = MASTER_EXTRACTION_TEMPLATE.replace("{{CONTEXT}}", context)
            
            # Call LLM with timeout - increase for large documents
            # Use longer timeout for extraction (can be slow for large docs)
            response_text = await asyncio.wait_for(
                llm_func(prompt=prompt, system_prompt=system_prompt, temperature=0.05),
                timeout=120.0  # 120 second timeout for extraction
            )
            
            # Clean response
            text = response_text.strip()
            if text.startswith("```"):
                lines = text.split("\n")
                text = "\n".join(lines[1:-1]) if lines[-1].strip() == "```" else "\n".join(lines[1:])
            
            payload = json.loads(text)
            
            # Convert to expected format with error handling
            from gdd_rag_backbone.gdd.schemas import GddObject, GddSystem, GddInteraction, GddRequirement
            
            objects = []
            for item in payload.get("objects", []):
                if isinstance(item, dict):
                    try:
                        objects.append(GddObject(**item).to_dict())
                    except Exception as e:
                        logger.warning(f"Error parsing object: {e}, item: {item}")
                        objects.append(item)
            
            systems = []
            for item in payload.get("systems", []):
                if isinstance(item, dict):
                    try:
                        systems.append(GddSystem(**item).to_dict())
                    except Exception as e:
                        logger.warning(f"Error parsing system: {e}, item: {item}")
                        systems.append(item)
            
            logic_rules = []
            for item in payload.get("logic_rules", []):
                if isinstance(item, dict):
                    try:
                        logic_rules.append(GddInteraction(**item).to_dict())
                    except Exception as e:
                        logger.warning(f"Error parsing logic rule: {e}, item: {item}")
                        logic_rules.append(item)
            
            requirements = []
            for item in payload.get("requirements", []):
                if isinstance(item, dict):
                    try:
                        requirements.append(GddRequirement(**item).to_dict())
                    except Exception as e:
                        logger.warning(f"Error parsing requirement: {e}, item: {item}")
                        requirements.append(item)
            
            return {
                "objects": objects,
                "systems": systems,
                "logic_rules": logic_rules,
                "requirements": requirements,
            }
        except asyncio.TimeoutError:
            last_error = Exception("LLM call timed out after 120 seconds")
            if attempt < max_retries - 1:
                wait_time = (attempt + 1) * 3  # Longer wait between retries
                logger.warning(f"Attempt {attempt + 1} timed out for doc {doc_id}. Retrying in {wait_time}s...")
                await asyncio.sleep(wait_time)
            else:
                # On final timeout, give up
                raise Exception(f"Failed to extract requirements after {max_retries} attempts: LLM timeout (document may be too large)")
        except (ConnectionError, Exception) as e:
            last_error = e
            error_str = str(e).lower()
            # Check if it's a network/DNS error
            if "dns" in error_str or "resolve" in error_str or "connection" in error_str:
                if attempt < max_retries - 1:
                    wait_time = (attempt + 1) * 5  # Longer wait for network issues: 5s, 10s, 15s
                    logger.warning(f"Network error on attempt {attempt + 1} for doc {doc_id}: {e}. Retrying in {wait_time}s...")
                    await asyncio.sleep(wait_time)
                else:
                    logger.error(f"Network error after {max_retries} attempts: {e}")
                    raise Exception(f"Network error: Failed to connect to API after {max_retries} attempts. Check your internet connection.")
            else:
                if attempt < max_retries - 1:
                    wait_time = (attempt + 1) * 2  # Exponential backoff: 2s, 4s, 6s
                    logger.warning(f"Attempt {attempt + 1} failed for doc {doc_id}: {e}. Retrying in {wait_time}s...")
                    await asyncio.sleep(wait_time)
                else:
                    logger.error(f"Error extracting requirements from Supabase after {max_retries} attempts: {e}")
                    raise Exception(f"Failed to extract requirements after {max_retries} attempts: {str(e)}")
    
    raise Exception(f"Failed to extract requirements: {last_error}")


async def evaluate_all_requirements_from_doc(
    doc_id: str,
    provider: Optional[QwenProvider] = None,
    top_k: int = 12
) -> Dict[str, Any]:
    """
    Extract all requirements from a GDD document and evaluate their implementation status.
    
    Args:
        doc_id: The GDD document ID
        provider: Optional LLM provider
        top_k: Number of code chunks to retrieve per requirement
    
    Returns:
        {
            "doc_id": "...",
            "total_requirements": N,
            "results": [
                {
                    "requirement": {...},
                    "evaluation": {...}
                }
            ],
            "summary": {
                "implemented": N,
                "partially_implemented": N,
                "not_implemented": N
            }
        }
    """
    active_provider = provider or QwenProvider()
    llm_func = make_llm_model_func(active_provider)
    
    # Check if document has chunks before attempting extraction
    from backend.storage.supabase_client import get_supabase_client
    try:
        client = get_supabase_client()
        chunk_check = client.table('gdd_chunks').select('id', count='exact').eq('doc_id', doc_id).limit(1).execute()
        chunk_count = chunk_check.count if hasattr(chunk_check, 'count') else len(chunk_check.data) if chunk_check.data else 0
        
        if chunk_count == 0:
            logger.warning(f"Document {doc_id} has no chunks in Supabase. Skipping extraction.")
            return {
                "doc_id": doc_id,
                "warning": f"Document has no chunks indexed in Supabase. Please index this document first.",
                "total_requirements": 0,
                "results": [],
                "summary": {"implemented": 0, "partially_implemented": 0, "not_implemented": 0, "error": 0}
            }
    except Exception as e:
        logger.warning(f"Could not check chunks for {doc_id}: {e}")
    
    # Extract requirements from GDD using Supabase-compatible extraction
    logger.info(f"Extracting requirements from doc_id: {doc_id}")
    try:
        extracted = await extract_requirements_from_doc_supabase(
            doc_id=doc_id,
            provider=active_provider,
            llm_func=llm_func
        )
    except Exception as e:
        logger.error(f"Error extracting requirements: {e}")
        return {
            "doc_id": doc_id,
            "error": f"Failed to extract requirements: {str(e)}",
            "total_requirements": 0,
            "results": [],
            "summary": {"implemented": 0, "partially_implemented": 0, "not_implemented": 0, "error": 0}
        }
    
    requirements_data = extracted.get("requirements", [])
    
    # Convert to GddRequirement objects
    requirements = []
    for req_dict in requirements_data:
        try:
            # Ensure required fields have defaults
            req_id = req_dict.get("id") or f"req_{len(requirements) + 1}"
            req_title = req_dict.get("title") or req_dict.get("summary") or "Untitled Requirement"
            req_description = req_dict.get("description") or req_dict.get("details") or ""
            
            # Skip if no meaningful content
            if not req_description and not req_title:
                continue
            
            req = GddRequirement(
                id=req_id,
                title=req_title,
                description=req_description,
                summary=req_dict.get("summary"),
                category=req_dict.get("category"),
                priority=req_dict.get("priority"),
                status=req_dict.get("status"),
                acceptance_criteria=req_dict.get("acceptance_criteria"),
                related_objects=req_dict.get("related_objects", []) or [],
                related_systems=req_dict.get("related_systems", []) or [],
                source_note=req_dict.get("source_note"),
                triggers=req_dict.get("triggers", []) or [],
                effects=req_dict.get("effects", []) or [],
                entities_involved=req_dict.get("entities_involved", []) or [],
                expected_code_anchors=req_dict.get("expected_code_anchors", []) or [],
            )
            requirements.append(req)
        except Exception as e:
            logger.warning(f"Error parsing requirement: {e}, dict: {req_dict}")
            continue
    
    logger.info(f"Found {len(requirements)} requirements. Evaluating implementation...")
    
    # Evaluate each requirement
    results = []
    summary = {"implemented": 0, "partially_implemented": 0, "not_implemented": 0, "error": 0}
    
    for idx, req in enumerate(requirements, 1):
        logger.info(f"Evaluating requirement {idx}/{len(requirements)}: {req.title[:50]}")
        try:
            # Add small delay between requirements to avoid rate limiting
            if idx > 1:
                await asyncio.sleep(1)  # 1 second delay between requirements
            
            evaluation = await asyncio.wait_for(
                evaluate_requirement_coverage(
                    req,
                    provider=active_provider,
                    top_k=top_k
                ),
                timeout=120.0  # 2 minute timeout per requirement
            )
            status = evaluation.get("status", "unknown")
            summary[status] = summary.get(status, 0) + 1
            
            results.append({
                "requirement": req.to_dict(),
                "evaluation": evaluation
            })
        except asyncio.TimeoutError:
            logger.error(f"Timeout evaluating requirement {req.id}")
            summary["error"] += 1
            results.append({
                "requirement": req.to_dict(),
                "evaluation": {
                    "status": "error",
                    "error": "Evaluation timed out after 2 minutes",
                    "requirement_id": req.id
                }
            })
        except Exception as e:
            logger.error(f"Error evaluating requirement {req.id}: {e}", exc_info=True)
            summary["error"] += 1
            results.append({
                "requirement": req.to_dict(),
                "evaluation": {
                    "status": "error",
                    "error": str(e)[:200],
                    "requirement_id": req.id
                }
            })
    
    return {
        "doc_id": doc_id,
        "total_requirements": len(requirements),
        "results": results,
        "summary": summary
    }

