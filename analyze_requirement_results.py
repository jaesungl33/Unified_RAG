"""
Analyze requirement evaluation results and provide insights.
"""

import json
from pathlib import Path
from collections import defaultdict

def analyze_results():
    """Analyze the requirement evaluation results"""
    results_file = Path("all_docs_requirement_evaluation.json")
    
    if not results_file.exists():
        print("Results file not found. Run test_all_docs_requirements.py first.")
        return
    
    with results_file.open('r', encoding='utf-8') as f:
        data = json.load(f)
    
    print("=" * 80)
    print("REQUIREMENT EVALUATION ANALYSIS")
    print("=" * 80)
    
    summary = data.get('summary', {})
    results = data.get('results', [])
    
    print(f"\nDocuments Processed: {summary.get('total_documents', 0)}")
    print(f"Successful: {summary.get('successful', 0)}")
    print(f"Failed: {summary.get('failed', 0)}")
    
    # Collect all requirements
    all_requirements = []
    by_status = defaultdict(list)
    by_category = defaultdict(lambda: {'implemented': 0, 'partial': 0, 'not_impl': 0})
    
    for item in results:
        result = item.get('result', {})
        doc_name = item.get('doc_name', 'Unknown')
        
        if 'error' in result:
            print(f"\n[ERROR] {doc_name}: {result.get('error', 'Unknown error')}")
            continue
        
        reqs = result.get('results', [])
        for req_item in reqs:
            req = req_item.get('requirement', {})
            eval_result = req_item.get('evaluation', {})
            status = eval_result.get('status', 'unknown')
            
            all_requirements.append({
                'doc': doc_name,
                'title': req.get('title', 'Unknown'),
                'category': req.get('category', 'uncategorized'),
                'status': status,
                'confidence': eval_result.get('confidence', 0.0),
                'evidence': eval_result.get('evidence', [])
            })
            
            by_status[status].append(req.get('title', 'Unknown'))
            
            category = req.get('category', 'uncategorized')
            if status == 'implemented':
                by_category[category]['implemented'] += 1
            elif status == 'partially_implemented':
                by_category[category]['partial'] += 1
            else:
                by_category[category]['not_impl'] += 1
    
    print(f"\n{'='*80}")
    print("OVERALL STATISTICS")
    print(f"{'='*80}")
    print(f"\nTotal Requirements: {len(all_requirements)}")
    print(f"  Implemented: {len(by_status.get('implemented', []))} ({len(by_status.get('implemented', []))/len(all_requirements)*100:.1f}%)")
    print(f"  Partially Implemented: {len(by_status.get('partially_implemented', []))} ({len(by_status.get('partially_implemented', []))/len(all_requirements)*100:.1f}%)")
    print(f"  Not Implemented: {len(by_status.get('not_implemented', []))} ({len(by_status.get('not_implemented', []))/len(all_requirements)*100:.1f}%)")
    
    # Show implemented requirements
    if by_status.get('implemented'):
        print(f"\n{'='*80}")
        print("FULLY IMPLEMENTED REQUIREMENTS")
        print(f"{'='*80}")
        for req_title in by_status.get('implemented', []):
            print(f"  ✓ {req_title}")
    
    # Show partially implemented
    if by_status.get('partially_implemented'):
        print(f"\n{'='*80}")
        print("PARTIALLY IMPLEMENTED REQUIREMENTS")
        print(f"{'='*80}")
        for req_title in by_status.get('partially_implemented', []):
            print(f"  ~ {req_title}")
    
    # Show top not implemented
    if by_status.get('not_implemented'):
        print(f"\n{'='*80}")
        print("NOT IMPLEMENTED REQUIREMENTS (Top 10)")
        print(f"{'='*80}")
        for req_title in by_status.get('not_implemented', [])[:10]:
            print(f"  ✗ {req_title}")
        if len(by_status.get('not_implemented', [])) > 10:
            print(f"  ... and {len(by_status.get('not_implemented', [])) - 10} more")
    
    # Category breakdown
    if by_category:
        print(f"\n{'='*80}")
        print("BREAKDOWN BY CATEGORY")
        print(f"{'='*80}")
        for category, counts in sorted(by_category.items()):
            total = counts['implemented'] + counts['partial'] + counts['not_impl']
            if total > 0:
                impl_pct = (counts['implemented'] / total) * 100
                partial_pct = (counts['partial'] / total) * 100
                print(f"\n{category}:")
                print(f"  Total: {total}")
                print(f"  Implemented: {counts['implemented']} ({impl_pct:.1f}%)")
                print(f"  Partial: {counts['partial']} ({partial_pct:.1f}%)")
                print(f"  Not Implemented: {counts['not_impl']} ({100-impl_pct-partial_pct:.1f}%)")
    
    # Requirements with evidence
    print(f"\n{'='*80}")
    print("REQUIREMENTS WITH CODE EVIDENCE")
    print(f"{'='*80}")
    reqs_with_evidence = [r for r in all_requirements if r.get('evidence')]
    print(f"\n{len(reqs_with_evidence)} requirements have code evidence:")
    for req in reqs_with_evidence[:5]:
        print(f"\n  {req['title']} ({req['status']})")
        for ev in req.get('evidence', [])[:2]:
            file = ev.get('file', 'unknown')
            reason = ev.get('reason', '')[:80]
            print(f"    - {file}: {reason}...")
    
    print(f"\n{'='*80}")
    print("Analysis Complete!")
    print(f"{'='*80}")

if __name__ == '__main__':
    analyze_results()


