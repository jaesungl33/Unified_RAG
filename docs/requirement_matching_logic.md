# Requirement Matching Logic

## Overview

The requirement matching system determines whether game design requirements are implemented in the codebase. It uses a **two-stage approach**: semantic search to find relevant code, then LLM-based classification to determine implementation status.

## Process Flow

```
┌─────────────────────────────────────────────────────────────┐
│ 1. REQUIREMENT EXTRACTION (from GDD documents)              │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│ Extract requirements from GDD using LLM                    │
│ - Searches GDD chunks for requirement descriptions          │
│ - LLM extracts structured requirements (title, description, │
│   acceptance criteria, etc.)                                │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│ 2. CODE SEARCH (for each requirement)                       │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│ Generate Query Variations                                   │
│ - From requirement: description, summary, acceptance       │
│   criteria, title                                           │
│ - Creates multiple semantic queries                        │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│ Vector Similarity Search                                    │
│ - Embed each query using Qwen embeddings                    │
│ - Search code chunks in Supabase using cosine similarity   │
│ - Threshold: 0.2 (low for broad search)                    │
│ - Returns top 12 code chunks per query                      │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│ Merge & Rank Results                                        │
│ - Deduplicate chunks by ID                                   │
│ - Sort by similarity score (highest first)                 │
│ - Return top 12 chunks                                      │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│ 3. LLM CLASSIFICATION                                       │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│ Build Context for LLM                                       │
│ - Requirement: full JSON with all fields                     │
│ - Code: top 8 chunks with file paths, class/method names,   │
│   similarity scores, and code content (truncated to 1500    │
│   chars per chunk)                                           │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│ LLM Evaluation                                              │
│ System Prompt: "You are a senior gameplay engineer.        │
│ Evaluate whether the provided code implements the           │
│ requirement. Do NOT guess. If there is insufficient         │
│ evidence, respond with 'not_implemented'."                   │
│                                                              │
│ Temperature: 0.1 (low for consistent results)               │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│ Classification Decision                                      │
│ Returns one of three statuses:                              │
│                                                              │
│ 1. "implemented" - Code fully satisfies the requirement      │
│ 2. "partially_implemented" - Code partially satisfies       │
│    (some features missing or incomplete)                    │
│ 3. "not_implemented" - No code found or insufficient        │
│    evidence                                                  │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│ Return Result with Evidence                                 │
│ - Status classification                                     │
│ - Confidence score (0.0-1.0)                                │
│ - Evidence array with file paths and reasons                │
│ - Matched code chunks (top 5)                               │
└─────────────────────────────────────────────────────────────┘
```

## Key Components

### 1. Query Generation

The system extracts multiple query variations from a requirement:

```python
queries = [
    requirement.description,      # Main description
    requirement.summary,          # Short summary
    requirement.acceptance_criteria,  # Acceptance criteria
    requirement.title            # Title
]
```

**Why multiple queries?**
- Different parts of the requirement may match different code patterns
- Increases recall (finds more relevant code)
- Handles cases where code uses different terminology

### 2. Vector Search

**Embedding Model**: Qwen `text-embedding-v4` (1024 dimensions)

**Search Process**:
1. Embed each query into a 1024-dimensional vector
2. Search Supabase `code_chunks` table using cosine similarity
3. Filter by similarity threshold (0.2 = very permissive)
4. Return top 12 chunks per query

**Why low threshold (0.2)?**
- Requirements are often written in natural language
- Code uses technical terminology
- Semantic gap between design docs and code
- LLM will filter false positives later

### 3. LLM Classification Logic

The LLM receives:

**Input**:
- Full requirement JSON (title, description, acceptance criteria, etc.)
- Top 8 code chunks with:
  - File path
  - Class and method names
  - Similarity score
  - Code content (truncated)

**Decision Criteria** (implicit in the prompt):

1. **"implemented"** when:
   - Code directly implements the requirement
   - All acceptance criteria are met
   - Functionality matches requirement description

2. **"partially_implemented"** when:
   - Some functionality exists but incomplete
   - Missing some acceptance criteria
   - Core feature present but details missing
   - Related code exists but doesn't fully satisfy requirement

3. **"not_implemented"** when:
   - No relevant code found
   - Code is unrelated to requirement
   - Insufficient evidence to determine implementation

**Why LLM instead of simple matching?**
- Understands semantic meaning, not just keywords
- Can reason about partial implementations
- Handles complex requirements with multiple criteria
- Provides explanations (evidence) for decisions

## Example Flow

### Requirement:
```json
{
  "id": "req_001",
  "title": "Player Movement System",
  "description": "The game should have a player movement system that allows players to move using WASD keys. The movement should be smooth and responsive.",
  "acceptance_criteria": "Player can move using WASD keys, movement is smooth"
}
```

### Step 1: Query Generation
- Query 1: "The game should have a player movement system that allows players to move using WASD keys..."
- Query 2: "Player Movement System"
- Query 3: "Player can move using WASD keys, movement is smooth"

### Step 2: Vector Search
- Searches codebase for chunks related to:
  - Player movement
  - WASD input
  - Movement controllers
- Returns chunks like:
  - `PlayerController.cs` - `Move()` method
  - `InputHandler.cs` - `HandleWASD()` method
  - `MovementSystem.cs` - Movement logic

### Step 3: LLM Classification
LLM analyzes:
- Does `PlayerController.Move()` implement WASD movement? ✓
- Is movement smooth? (checks for interpolation, deltaTime usage)
- Are all acceptance criteria met?

**Result**: 
- Status: "implemented" or "partially_implemented"
- Evidence: Points to specific files and methods
- Confidence: 0.85

## Edge Cases Handled

1. **No code found** → Returns "not_implemented" immediately (no LLM call)

2. **Multiple implementations** → LLM evaluates all and determines if any fully satisfy

3. **Partial matches** → LLM distinguishes between "partially_implemented" and "not_implemented"

4. **Unrelated code** → Low similarity scores + LLM filtering removes false positives

5. **Ambiguous requirements** → LLM uses context to make best judgment

## Performance Optimizations

1. **Query limiting**: Only uses top 3 query variations to avoid API rate limits
2. **Chunk truncation**: Limits code content to 1500 chars per chunk
3. **Top-K retrieval**: Only retrieves top 12 chunks (reduces LLM context size)
4. **Early exit**: If no chunks found, skips LLM call
5. **Caching**: Embeddings are cached for repeated queries

## Limitations

1. **Depends on code indexing**: Only finds indexed code chunks
2. **Semantic gap**: Natural language requirements vs. code terminology
3. **LLM accuracy**: Classification depends on LLM understanding
4. **Partial implementations**: Hard to quantify "how partial"
5. **False positives**: Code might match semantically but not functionally

## Future Improvements

1. **Two-tier matching**: Fast symbol matching (exact class/method names) before semantic search
2. **Confidence thresholds**: Use confidence scores to filter uncertain classifications
3. **Incremental evaluation**: Cache results and only re-evaluate when code changes
4. **Multi-file analysis**: Consider related files when evaluating requirements
5. **Requirement dependencies**: Track which requirements depend on others


