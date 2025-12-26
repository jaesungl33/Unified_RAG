# Requirement Matching Improvements for Functional Equivalence

## Problem Identified

The current system was marking requirements as "not implemented" even when the code had the same functionality, just described differently:

- **GDD says**: "Player can move with WASD keys"
- **Code has**: `Input.GetKey(KeyCode.W)` 
- **Result**: "not_implemented" ❌ (False negative!)

This happens because:
1. Design documents use user-facing language
2. Code uses technical/implementation language
3. Vector search might not bridge this terminology gap
4. LLM might be too strict in matching

## Improvements Made

### 1. Enhanced Query Generation

**Before**: Only used requirement text as-is
```python
queries = [requirement.description, requirement.summary, ...]
```

**After**: Adds technical keywords to bridge terminology gap
```python
if "move" in description:
    queries.append(description + " Input.GetKey transform.position velocity")
if "display" in description:
    queries.append(description + " UI Canvas Text Image Sprite")
```

This helps vector search find code that uses technical terms even when requirement uses design language.

### 2. Improved LLM Prompt

**Before**: 
```
"Evaluate whether the provided code implements the requirement."
```

**After**:
```
"Look for FUNCTIONAL EQUIVALENCE, not exact text matches.
The requirement may be written in design language, while code uses technical terms.
If the code achieves the same functionality (even with different terminology),
classify it as 'implemented' or 'partially_implemented'."
```

**Added examples**:
- Requirement: "Player can move with WASD" → Code: `Input.GetKey(KeyCode.W)` → **IMPLEMENTED**
- Requirement: "Smooth movement" → Code: `velocity * Time.deltaTime` → **IMPLEMENTED**

### 3. Broader Search Parameters

**Before**:
- Threshold: 0.2
- Top-K: 12 chunks
- 3 query variations

**After**:
- Threshold: 0.15 (lower = more permissive)
- Top-K: 24 chunks (more candidates)
- 5 query variations (better coverage)

### 4. Better Evidence Formatting

Evidence now focuses on **functional equivalence**:
```
"reason": "Code uses Input.GetKey to detect WASD input, which functionally 
implements player movement with WASD keys as described in requirement"
```

Instead of:
```
"reason": "Code doesn't mention 'WASD' explicitly" ❌
```

## How It Works Now

### Example: "Player Movement with WASD"

**Requirement**:
```json
{
  "title": "Player Movement with WASD",
  "description": "Player can move using WASD keys"
}
```

**Step 1: Query Generation**
- Query 1: "Player can move using WASD keys"
- Query 2: "Player can move using WASD keys Input.GetKey transform.position velocity"
- Query 3: "Player Movement with WASD"

**Step 2: Vector Search**
- Finds: `PlayerController.cs` with `Input.GetKey(KeyCode.W)`
- Finds: `MovementSystem.cs` with `transform.position += direction * speed`
- Similarity might be 0.3-0.4 (lower than before, but still relevant)

**Step 3: LLM Classification**
- LLM sees: Requirement says "WASD keys", Code has `Input.GetKey(KeyCode.W)`
- LLM reasons: "These are functionally equivalent - both detect keyboard input for movement"
- Result: **"implemented"** ✅

## Expected Impact

### Before Improvements:
- Many false negatives (marked as not implemented when they are)
- Strict text matching
- Missed functional equivalents

### After Improvements:
- Better detection of functional equivalence
- More accurate classification
- Fewer false negatives
- Still maintains accuracy (won't create false positives)

## Testing Recommendations

1. **Re-run evaluation** on the same documents to see improved results
2. **Compare before/after** to measure improvement
3. **Review evidence** to verify LLM is correctly identifying functional equivalence
4. **Adjust thresholds** if needed (0.15 might be too low/high for your codebase)

## Fine-Tuning

If you still see false negatives:

1. **Lower threshold further** (0.1 or 0.12) - catches more potential matches
2. **Increase top_k** (16-20) - more code chunks for LLM to evaluate
3. **Add more query variations** - expand technical keyword matching
4. **Improve prompt** - add more examples specific to your game's terminology

## Example: What Should Change

### Before:
```
Requirement: "Hiển thị rõ ràng thông tin chức năng trên màn hình chính"
Status: not_implemented
```

### After (with improvements):
```
Requirement: "Hiển thị rõ ràng thông tin chức năng trên màn hình chính"
Status: implemented (if code has UI elements displaying information)
Evidence: "UI Canvas displays player info, tank info, and game functions"
```

The system should now recognize that:
- "Hiển thị" (display/show) = UI elements, Canvas, Text components
- "Thông tin chức năng" (function information) = UI buttons, menus, info panels
- Even if code doesn't use exact Vietnamese terms, it's functionally the same


