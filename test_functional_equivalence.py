"""
Test to demonstrate functional equivalence matching.
Shows how the system handles requirements written in design language
vs code written in technical language.
"""

import asyncio
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.requirement_matching_service import evaluate_requirement_coverage
from gdd_rag_backbone.gdd.schemas import GddRequirement
from gdd_rag_backbone.llm_providers import QwenProvider

async def test_functional_equivalence():
    """Test that the system recognizes functional equivalence"""
    
    print("=" * 80)
    print("Testing Functional Equivalence Matching")
    print("=" * 80)
    print("\nThis test demonstrates how the system handles:")
    print("  - Requirements written in design/user language")
    print("  - Code written in technical/implementation language")
    print("  - Same functionality, different terminology\n")
    
    # Example requirement written in design language
    requirement = GddRequirement(
        id="test_func_equiv_1",
        title="Player Movement with WASD",
        description="Player can move using WASD keys. Movement should be smooth and responsive.",
        summary="WASD movement controls",
        acceptance_criteria="Player can move in all directions using WASD keys"
    )
    
    print(f"Requirement: {requirement.title}")
    print(f"Description: {requirement.description}")
    print("\nThis requirement is written in design language.")
    print("The code might use technical terms like:")
    print("  - Input.GetKey(KeyCode.W)")
    print("  - transform.position += direction * speed")
    print("  - Time.deltaTime for smooth movement")
    print("\nThese are FUNCTIONALLY EQUIVALENT but use different terminology.\n")
    
    provider = QwenProvider()
    
    print("Evaluating requirement against codebase...")
    print("-" * 80)
    
    result = await evaluate_requirement_coverage(
        requirement=requirement,
        provider=provider,
        top_k=15  # Get more chunks for better matching
    )
    
    print("\n" + "=" * 80)
    print("RESULT")
    print("=" * 80)
    print(f"\nStatus: {result.get('status')}")
    print(f"Confidence: {result.get('confidence', 0.0):.2f}")
    print(f"Matched Chunks: {len(result.get('matched_chunks', []))}")
    
    if result.get('evidence'):
        print("\nEvidence:")
        for ev in result.get('evidence', [])[:3]:
            print(f"  File: {ev.get('file', 'unknown')}")
            print(f"  Class: {ev.get('class', 'N/A')}.{ev.get('method', 'N/A')}")
            print(f"  Reason: {ev.get('reason', '')[:100]}...")
            print()
    
    if result.get('matched_chunks'):
        print("\nTop Matched Code Chunks:")
        for idx, chunk in enumerate(result.get('matched_chunks', [])[:3], 1):
            print(f"\n  {idx}. {chunk.get('file_path', 'unknown')}")
            print(f"     Class: {chunk.get('class_name', 'N/A')}.{chunk.get('method_name', 'N/A')}")
            print(f"     Similarity: {chunk.get('score', 0.0):.3f}")
            code_preview = chunk.get('content', '')[:200]
            print(f"     Code: {code_preview}...")
    
    print("\n" + "=" * 80)
    print("INTERPRETATION")
    print("=" * 80)
    
    status = result.get('status')
    if status == 'implemented':
        print("\n✓ SUCCESS: System correctly identified functional equivalence!")
        print("  The code implements the requirement, even though it uses")
        print("  different terminology than the GDD.")
    elif status == 'partially_implemented':
        print("\n~ PARTIAL: System found some implementation but may need review.")
        print("  Check if all acceptance criteria are met.")
    else:
        print("\n✗ NOT FOUND: System didn't find matching code.")
        print("  This could mean:")
        print("  1. Code truly doesn't implement this feature")
        print("  2. Terminology gap is too large (may need more query variations)")
        print("  3. Code is in a different location than expected")
    
    print("\n" + "=" * 80)

if __name__ == '__main__':
    asyncio.run(test_functional_equivalence())


