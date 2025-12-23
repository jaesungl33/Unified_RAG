## RAG Pipeline Comparison: Codebase vs GDD

### 1. Codebase RAG (C# Code Q&A)

#### Chunking
- **Parser**: Uses Tree-sitter to parse C#.
- **Chunk types**: 
  - Methods (function bodies)
  - Classes
- **Metadata per chunk**:
  - `file_path`
  - `class_name`
  - `method_name`
  - `chunk_type` (`method` / `class`)
  - `source_code`
  - `doc_comment`, `constructor_declaration`, `method_declarations`, `references`

#### Embedding & Indexing
- **Embedding model**: Qwen embeddings (via `openai`-compatible client).
- **Storage**: Supabase Postgres with `pgvector`.
- **Tables**:
  - `code_files`: `file_path`, `file_name`, `normalized_path`, timestamps.
  - `code_chunks`: 
    - Core: `file_path`, `chunk_type`, `class_name`, `method_name`, `source_code`, `code`
    - Vector: `embedding vector(1024)`
    - Extra: `doc_comment`, `constructor_declaration`, `method_declarations`, `code_references`, `metadata`
- **Indexes**:
  - Vector index on `embedding`
  - B-tree on `file_path`, `chunk_type` etc. for fast filters.

#### Retrieval
- **Query processing**:
  - Parses `@filename.cs` filters from the question.
  - Normalizes paths and maps them to `code_files` / `code_chunks`.
- **HYDE v2**:
  - Generates a refined or “hypothetical” query using the LLM.
  - Uses the refined query text for vector search.
- **Vector search**:
  - Calls Supabase RPC (`match_code_chunks`) with optional filters:
    - `file_path_filter`
    - `chunk_type_filter`
  - Returns top‑K method and class chunks.
- **Reranking**:
  - Uses ColBERT-based reranker (`rerankers`) on retrieved chunks.
  - Reorders results by semantic relevance to the question.
- **Answer generation**:
  - Builds a strict prompt:
    - Answer **only** from provided code chunks.
    - If info is missing, say “There is no logic for this in the current codebase.”
  - Calls Qwen chat via the `openai` client.

**Strengths**
- Highly structured chunks (methods/classes) match how developers think.
- Rich metadata enables precise filters (by file, class, method).
- HYDE + reranking significantly improve relevance.
- Strict prompting keeps hallucinations low.

---

### 2. GDD RAG (Game Design Documents)

#### Chunking
- **Inputs**: Markdown / PDF converted to markdown.
- **Chunk strategy**:
  - Splits documents into textual chunks, loosely based on sections and length.
  - Less structural than C# parsing; closer to paragraphs + headings.
- **Metadata per chunk**:
  - `doc_id`
  - `content`
  - Basic metadata (e.g., document name, maybe simple tags).

#### Embedding & Indexing
- **Embedding model**: Qwen embeddings (same embedding family).
- **Storage**: Supabase Postgres with `pgvector`.
- **Tables**:
  - `gdd_documents`: document‑level metadata (title, id, path).
  - `gdd_chunks`:
    - Core: `doc_id`, `content`
    - Vector: `embedding vector(1024)`
    - Extra: `metadata` JSON.

#### Retrieval
- **Query processing**:
  - Optional filter by selected document from the sidebar.
  - Language detection to reply in English or Vietnamese to match the question.
- **Vector search**:
  - Simple similarity search on `gdd_chunks` (no HYDE yet).
  - Optionally constrained to a given `doc_id`.
- **Reranking**:
  - Currently not applied (or minimal), so results rely mostly on raw vector similarity.
- **Answer generation**:
  - Prompt is less strict than Code Q&A but still encourages grounding in retrieved chunks.
  - Tries to respond in the same language as the user.

**Current Limitations**
- Chunks are less semantically sharp than methods/classes.
- Metadata is lighter, making fine‑grained filters harder (e.g., by subsection).
- No HYDE and limited reranking → more variance in relevance.

---

### 3. Ideas to Bring Code RAG Strengths into GDD RAG

Even though GDD content is different from code, several design patterns transfer well.

#### 3.1 More Structured GDD Chunking
- Treat GDD as “code with sections”:
  - Parse markdown headings (`H1/H2/H3`) into **sections** and **subsections**.
  - Chunk within each section by paragraph or bullet groups.
- Store richer metadata per chunk:
  - `doc_id`
  - `section_title`, `subsection_title`
  - `section_path` (e.g., `"5. Interface / 5.2 Result Screen"`)
  - `section_index`, `paragraph_index`
- Benefit: analogous to `class_name` / `method_name` in Code RAG, enabling:
  - Section‑level filters.
  - Clearer context labels in answers.

#### 3.2 Richer Metadata in Supabase
- Extend `gdd_chunks.metadata` with:
  - `section_path`
  - `tags` (e.g., `["UI", "Tank War"]`, `["Combat", "Module"]`, `["Monetization", "Shop"]`)
  - `doc_category` (`Asset`, `Character`, `Combat`, `World`, etc.).
- Then you can:
  - Filter / prioritize chunks by tags or categories.
  - Group retrieved chunks by section in the answer.

#### 3.3 HYDE‑Style Query Refinement
- Reuse the HYDE v2 idea from Code RAG:
  - System prompt oriented to **game design sections** instead of code.
  - Given a user question and some context, ask the LLM to produce an improved search description, e.g.:
    - “Result screen components for Tank War: layout, feedback messages, reward display.”
- Use this refined query text for GDD vector search.
- Expected benefits:
  - Better alignment between user intent and chunk content.
  - More stable retrieval for vague or high‑level questions.

#### 3.4 Add Reranking on Top of GDD Vector Search
- Use the same ColBERT reranker you use in Code RAG:
  - Take top‑K chunks from Supabase (e.g., 20–40).
  - Rerank them by relevance to the user query.
  - Keep the top N (e.g., 6–10) for final context.
- Benefits:
  - Reduces off‑topic chunks when many sections mention similar terms.
  - Improves answer sharpness, especially for long documents.

#### 3.5 Better Document/Section Targeting from the UI
- Code RAG pattern: `@filename.cs` filters search to a given file.
- GDD analogue:
  - Support queries like `@Result Screen Design summarise the player feedback`.
  - Map `@...` tokens to specific `doc_id` or `section_title` filters.
  - Combine with the existing sidebar selection (document groups like `[Asset][UI Tank War]`).
- This lets users **steer** retrieval with lightweight syntax, just like in Code Q&A.

#### 3.6 Consistent Logging & Metrics
- Mirror the Code RAG timing logs for GDD:
  - HYDE time
  - Vector search time
  - Rerank time
  - Context length and number of chunks
- Use logs for:
  - Tuning thresholds (`match_threshold`, top‑K counts).
  - Spotting slow queries or poorly performing documents.

---

### 4. Suggested Implementation Order

To incrementally close the gap between GDD RAG and Code RAG quality:

1. **Add HYDE‑style refinement to GDD**  
   - Reuse HYDE helper with a new system prompt tuned for game design documents.
2. **Add reranking for GDD results**  
   - Call the same ColBERT reranker on the retrieved chunks before building context.
3. **Improve GDD chunk metadata**  
   - Introduce section‑aware chunking and store `section_path` + tags in Supabase.
4. **Introduce section targeting syntax**  
   - Implement `@Section Name` or `@[Asset][UI Tank War]` filters similar to `@filename.cs`.
5. **Refine prompts & UI**  
   - Show section titles in the context, highlight key phrases, and keep answers tightly grounded.

Taken together, these changes will make GDD RAG behave more like your Codebase RAG: structured, precise, and controllable, while still respecting the differences between game design docs and C# code.



