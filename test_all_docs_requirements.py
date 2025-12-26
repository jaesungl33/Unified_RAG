"""
Test requirement matching for all available GDD documents.
"""

import asyncio
import json
import sys
from pathlib import Path
from typing import List, Dict

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.requirement_matching_service import evaluate_all_requirements_from_doc
from backend.gdd_service import list_documents
from gdd_rag_backbone.llm_providers import QwenProvider


async def test_all_documents():
    """Test requirement matching for all available documents"""
    print("=" * 80)
    print("Testing Requirement Matching for All Available Documents")
    print("=" * 80)
    
    # Get all available documents
    print("\n[Step 1] Fetching available documents...")
    try:
        documents = list_documents()
        print(f"Found {len(documents)} documents")
        
        if not documents:
            print("\n[ERROR] No documents found. Please index at least one GDD document first.")
            return
        
        print("\nAvailable documents:")
        for idx, doc in enumerate(documents, 1):
            doc_id = doc.get('doc_id') or doc.get('id') or doc.get('name', 'unknown')
            name = doc.get('name', 'Unknown')
            print(f"  {idx}. {name} (doc_id: {doc_id})")
        
    except Exception as e:
        print(f"\n[ERROR] Error fetching documents: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # Initialize provider
    print("\n[Step 2] Initializing LLM provider...")
    try:
        provider = QwenProvider()
        print("[OK] Provider initialized")
    except Exception as e:
        print(f"\n[ERROR] Error initializing provider: {e}")
        return
    
    # Evaluate requirements for each document
    print("\n[Step 3] Evaluating requirements for each document...")
    print("=" * 80)
    
    all_results = []
    
    for idx, doc in enumerate(documents, 1):
        doc_id = doc.get('doc_id') or doc.get('id') or doc.get('name', 'unknown')
        name = doc.get('name', 'Unknown')
        
        print(f"\n[{idx}/{len(documents)}] Processing: {name}")
        print(f"  doc_id: {doc_id}")
        print("-" * 80)
        
        try:
            # Add delay between documents to avoid rate limiting
            if idx > 1:
                print(f"  Waiting 3 seconds before processing next document...")
                await asyncio.sleep(3)
            
            result = await asyncio.wait_for(
                evaluate_all_requirements_from_doc(
                    doc_id=doc_id,
                    provider=provider,
                    top_k=12
                ),
                timeout=600.0  # 10 minute timeout per document
            )
            
            summary = result.get('summary', {})
            total = result.get('total_requirements', 0)
            
            print(f"  [OK] Evaluation complete")
            print(f"  Total Requirements: {total}")
            print(f"  Implemented: {summary.get('implemented', 0)}")
            print(f"  Partially Implemented: {summary.get('partially_implemented', 0)}")
            print(f"  Not Implemented: {summary.get('not_implemented', 0)}")
            print(f"  Errors: {summary.get('error', 0)}")
            
            # Calculate percentage
            if total > 0:
                implemented_pct = (summary.get('implemented', 0) / total) * 100
                partial_pct = (summary.get('partially_implemented', 0) / total) * 100
                not_impl_pct = (summary.get('not_implemented', 0) / total) * 100
                
                print(f"\n  Coverage:")
                print(f"    Implemented: {implemented_pct:.1f}%")
                print(f"    Partially: {partial_pct:.1f}%")
                print(f"    Not Implemented: {not_impl_pct:.1f}%")
            
            all_results.append({
                'doc_id': doc_id,
                'doc_name': name,
                'result': result
            })
            
            # Save progress after each document
            progress_file = Path("requirement_evaluation_progress.json")
            progress_file.write_text(
                json.dumps({
                    'processed': idx,
                    'total': len(documents),
                    'results': all_results
                }, indent=2, ensure_ascii=False),
                encoding='utf-8'
            )
            print(f"  [OK] Progress saved (processed {idx}/{len(documents)})")
            
        except asyncio.TimeoutError:
            print(f"  [ERROR] Timeout evaluating document (exceeded 10 minutes)")
            all_results.append({
                'doc_id': doc_id,
                'doc_name': name,
                'error': 'Timeout: exceeded 10 minutes'
            })
        except Exception as e:
            print(f"  [ERROR] Error evaluating document: {e}")
            import traceback
            traceback.print_exc()
            all_results.append({
                'doc_id': doc_id,
                'doc_name': name,
                'error': str(e)
            })
            
            # Save progress even on error
            progress_file = Path("requirement_evaluation_progress.json")
            progress_file.write_text(
                json.dumps({
                    'processed': idx,
                    'total': len(documents),
                    'results': all_results
                }, indent=2, ensure_ascii=False),
                encoding='utf-8'
            )
    
    # Generate summary report
    print("\n" + "=" * 80)
    print("SUMMARY REPORT")
    print("=" * 80)
    
    total_docs = len(all_results)
    successful_docs = len([r for r in all_results if 'result' in r])
    failed_docs = total_docs - successful_docs
    
    print(f"\nDocuments Processed: {total_docs}")
    print(f"  [OK] Successful: {successful_docs}")
    print(f"  [FAILED] Failed: {failed_docs}")
    
    if successful_docs > 0:
        total_reqs = sum(
            r['result'].get('total_requirements', 0) 
            for r in all_results if 'result' in r
        )
        total_implemented = sum(
            r['result'].get('summary', {}).get('implemented', 0)
            for r in all_results if 'result' in r
        )
        total_partial = sum(
            r['result'].get('summary', {}).get('partially_implemented', 0)
            for r in all_results if 'result' in r
        )
        total_not_impl = sum(
            r['result'].get('summary', {}).get('not_implemented', 0)
            for r in all_results if 'result' in r
        )
        
        print(f"\nOverall Statistics:")
        print(f"  Total Requirements Evaluated: {total_reqs}")
        print(f"  Implemented: {total_implemented} ({total_implemented/total_reqs*100:.1f}%)" if total_reqs > 0 else "  Implemented: 0")
        print(f"  Partially Implemented: {total_partial} ({total_partial/total_reqs*100:.1f}%)" if total_reqs > 0 else "  Partially Implemented: 0")
        print(f"  Not Implemented: {total_not_impl} ({total_not_impl/total_reqs*100:.1f}%)" if total_reqs > 0 else "  Not Implemented: 0")
    
    # Save detailed results
    output_file = Path("all_docs_requirement_evaluation.json")
    output_file.write_text(
        json.dumps({
            'summary': {
                'total_documents': total_docs,
                'successful': successful_docs,
                'failed': failed_docs
            },
            'results': all_results
        }, indent=2, ensure_ascii=False),
        encoding='utf-8'
    )
    print(f"\n[OK] Detailed results saved to: {output_file}")
    
    # Save a human-readable report
    report_file = Path("requirement_evaluation_report.txt")
    with report_file.open('w', encoding='utf-8') as f:
        f.write("=" * 80 + "\n")
        f.write("REQUIREMENT EVALUATION REPORT\n")
        f.write("=" * 80 + "\n\n")
        
        for item in all_results:
            f.write(f"Document: {item.get('doc_name', 'Unknown')}\n")
            f.write(f"doc_id: {item.get('doc_id', 'unknown')}\n")
            f.write("-" * 80 + "\n")
            
            if 'result' in item:
                result = item['result']
                summary = result.get('summary', {})
                total = result.get('total_requirements', 0)
                
                f.write(f"Total Requirements: {total}\n")
                f.write(f"Implemented: {summary.get('implemented', 0)}\n")
                f.write(f"Partially Implemented: {summary.get('partially_implemented', 0)}\n")
                f.write(f"Not Implemented: {summary.get('not_implemented', 0)}\n")
                f.write(f"Errors: {summary.get('error', 0)}\n\n")
                
                # List top requirements
                results_list = result.get('results', [])
                if results_list:
                    f.write("Top Requirements:\n")
                    for req_item in results_list[:10]:  # First 10
                        req = req_item.get('requirement', {})
                        eval_result = req_item.get('evaluation', {})
                        f.write(f"  - {req.get('title', 'Unknown')}: {eval_result.get('status', 'unknown')}\n")
            else:
                f.write(f"Error: {item.get('error', 'Unknown error')}\n")
            
            f.write("\n" + "=" * 80 + "\n\n")
    
    print(f"[OK] Human-readable report saved to: {report_file}")
    
    print("\n" + "=" * 80)
    print("Testing Complete!")
    print("=" * 80)


if __name__ == '__main__':
    asyncio.run(test_all_documents())

