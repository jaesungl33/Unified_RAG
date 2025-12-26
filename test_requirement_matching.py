"""
Test script for requirement matching functionality.
Run this to test the requirement-to-code matching feature.
"""

import asyncio
import json
import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.requirement_matching_service import (
    evaluate_all_requirements_from_doc,
    evaluate_requirement_coverage
)
from gdd_rag_backbone.gdd.schemas import GddRequirement
from gdd_rag_backbone.llm_providers import QwenProvider


async def test_single_requirement():
    """Test evaluating a single requirement"""
    print("=" * 60)
    print("Testing Single Requirement Evaluation")
    print("=" * 60)
    
    # Create a sample requirement
    requirement = GddRequirement(
        id="test_req_1",
        title="Player Movement System",
        description="The game should have a player movement system that allows players to move using WASD keys. The movement should be smooth and responsive.",
        summary="Player movement with WASD controls",
        category="combat",
        priority="high",
        acceptance_criteria="Player can move using WASD keys, movement is smooth"
    )
    
    print(f"\nRequirement: {requirement.title}")
    print(f"Description: {requirement.description[:100]}...")
    
    provider = QwenProvider()
    
    try:
        result = await evaluate_requirement_coverage(
            requirement=requirement,
            provider=provider,
            top_k=10
        )
        
        print("\n" + "=" * 60)
        print("Evaluation Result:")
        print("=" * 60)
        print(json.dumps(result, indent=2, ensure_ascii=False))
        
        print(f"\nStatus: {result.get('status')}")
        print(f"Confidence: {result.get('confidence', 0.0)}")
        print(f"Matched Chunks: {len(result.get('matched_chunks', []))}")
        
        if result.get('evidence'):
            print("\nEvidence:")
            for ev in result.get('evidence', [])[:3]:
                print(f"  - {ev.get('file', 'unknown')}: {ev.get('reason', '')[:100]}")
        
        return result
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
        return None


async def test_all_requirements(doc_id: str):
    """Test evaluating all requirements from a document"""
    print("=" * 60)
    print(f"Testing All Requirements Evaluation for doc_id: {doc_id}")
    print("=" * 60)
    
    provider = QwenProvider()
    
    try:
        result = await evaluate_all_requirements_from_doc(
            doc_id=doc_id,
            provider=provider,
            top_k=10
        )
        
        print("\n" + "=" * 60)
        print("Evaluation Results:")
        print("=" * 60)
        
        summary = result.get('summary', {})
        print(f"\nSummary:")
        print(f"  Total Requirements: {result.get('total_requirements', 0)}")
        print(f"  Implemented: {summary.get('implemented', 0)}")
        print(f"  Partially Implemented: {summary.get('partially_implemented', 0)}")
        print(f"  Not Implemented: {summary.get('not_implemented', 0)}")
        print(f"  Errors: {summary.get('error', 0)}")
        
        # Show first few results
        results = result.get('results', [])
        print(f"\nFirst 3 Results:")
        for idx, item in enumerate(results[:3], 1):
            req = item.get('requirement', {})
            eval_result = item.get('evaluation', {})
            print(f"\n  {idx}. {req.get('title', 'Unknown')}")
            print(f"     Status: {eval_result.get('status', 'unknown')}")
            print(f"     Confidence: {eval_result.get('confidence', 0.0)}")
        
        # Save full results to file
        output_file = Path("requirement_evaluation_results.json")
        output_file.write_text(
            json.dumps(result, indent=2, ensure_ascii=False),
            encoding='utf-8'
        )
        print(f"\nFull results saved to: {output_file}")
        
        return result
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
        return None


async def main():
    """Main test function"""
    print("\n" + "=" * 60)
    print("Requirement Matching Test Script")
    print("=" * 60)
    print("\nThis script tests the requirement-to-code matching functionality.")
    print("Make sure you have:")
    print("  1. Supabase configured (SUPABASE_URL and SUPABASE_KEY in .env)")
    print("  2. DASHSCOPE_API_KEY configured in .env")
    print("  3. At least one GDD document indexed")
    print("  4. At least some code files indexed")
    print()
    
    # Test 1: Single requirement
    print("\n[Test 1] Testing single requirement evaluation...")
    single_result = await test_single_requirement()
    
    if single_result:
        print("\n✓ Single requirement test completed")
    else:
        print("\n✗ Single requirement test failed")
    
    # Test 2: All requirements (if doc_id provided)
    import sys
    if len(sys.argv) > 1:
        doc_id = sys.argv[1]
        print(f"\n[Test 2] Testing all requirements for doc_id: {doc_id}...")
        all_results = await test_all_requirements(doc_id)
        
        if all_results:
            print("\n✓ All requirements test completed")
        else:
            print("\n✗ All requirements test failed")
    else:
        print("\n[Test 2] Skipped - provide a doc_id as argument to test all requirements")
        print("  Example: python test_requirement_matching.py your_doc_id")
    
    print("\n" + "=" * 60)
    print("Testing complete!")
    print("=" * 60)


if __name__ == '__main__':
    asyncio.run(main())






