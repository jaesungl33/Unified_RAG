"""
Script 1: Enhanced GDD Markdown Chunking (v2)
=============================================
Re-chunks markdown files with section-first metadata for better retrieval.

Key enhancements:
- Section path tracking (e.g., "5. Interface / 5.2 Result Screen")
- Section and paragraph indices
- Enhanced content type detection
- Preserves semantic blocks (lists, tables, flows)
- Avoids sentence-level splitting unless absolutely required

Output: Saves to gdd_data_v2/chunks/
"""

import argparse
import json
import re
import sys
from pathlib import Path
from typing import List, Dict, Optional, Tuple

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Import from gdd_rag_backbone
try:
    from gdd_rag_backbone.markdown_chunking import MarkdownChunker, MarkdownChunk
    from gdd_rag_backbone.markdown_chunking.markdown_parser import MarkdownParser, MarkdownSection
    from gdd_rag_backbone.markdown_chunking.tokenizer_utils import count_tokens
except ImportError:
    # Fallback: try relative import
    sys.path.insert(0, str(PROJECT_ROOT / "gdd_rag_backbone"))
    from markdown_chunking import MarkdownChunker, MarkdownChunk
    from markdown_chunking.markdown_parser import MarkdownParser, MarkdownSection
    from markdown_chunking.tokenizer_utils import count_tokens


class EnhancedMarkdownChunker:
    """
    Enhanced chunker with section-first metadata tracking.
    
    Tracks:
    - section_path: Hierarchical path (e.g., "5. Interface / 5.2 Result Screen")
    - section_index: Numeric index within document
    - paragraph_index: Index within section
    - content_type: ui, logic, flow, table, monetization, etc.
    """
    
    def __init__(
        self,
        chunk_size_tokens: int = 800,
        chunk_overlap_tokens: int = 80,
        max_chunk_size: int = 1000
    ):
        self.chunk_size_tokens = chunk_size_tokens
        self.chunk_overlap_tokens = chunk_overlap_tokens
        self.max_chunk_size = max_chunk_size
        self.parser = MarkdownParser()
        self.chunk_counter = 0
        self.section_counter = 0  # Track section index globally
        
        # Section hierarchy tracking
        self.section_hierarchy: List[Tuple[int, str]] = []  # [(level, header), ...]
        self.section_paths: Dict[str, str] = {}  # section_header -> full_path
        
    def chunk_document(
        self,
        markdown_content: str,
        doc_id: str,
        filename: str = ""
    ) -> List[Dict]:
        """
        Chunk a markdown document with enhanced section tracking.
        
        Returns:
            List of chunk dictionaries with enhanced metadata
        """
        self.chunk_counter = 0
        self.section_counter = 0
        self.section_hierarchy = []
        self.section_paths = {}
        
        chunks: List[Dict] = []
        
        # Parse markdown into sections
        sections = self.parser.parse(markdown_content)
        
        # Build section hierarchy and paths
        for section in sections:
            self._update_section_hierarchy(section)
        
        # Process each section
        for section in sections:
            section_chunks = self._chunk_section_enhanced(
                section=section,
                doc_id=doc_id,
                filename=filename
            )
            chunks.extend(section_chunks)
        
        return chunks
    
    def _update_section_hierarchy(self, section: MarkdownSection):
        """Update section hierarchy and build section paths."""
        if not section.header:
            return
        
        level = section.level
        
        # Remove sections at same or deeper level
        self.section_hierarchy = [
            (lvl, hdr) for lvl, hdr in self.section_hierarchy 
            if lvl < level
        ]
        
        # Add current section
        self.section_hierarchy.append((level, section.header))
        
        # Build section path
        if len(self.section_hierarchy) == 1:
            section_path = section.header
        else:
            # Join all parent sections with " / "
            section_path = " / ".join([hdr for _, hdr in self.section_hierarchy])
        
        self.section_paths[section.header] = section_path
    
    def _chunk_section_enhanced(
        self,
        section: MarkdownSection,
        doc_id: str,
        filename: str
    ) -> List[Dict]:
        """
        Chunk a section with enhanced metadata.
        
        Returns:
            List of chunk dictionaries with full metadata
        """
        if not section.content.strip():
            return []
        
        # Extract numbered header pattern (e.g., "1. Mụcđíchthiếtkế", "4.1 DanhsáchTanks", "7.3 Tankhạngnặng")
        numbered_header = self._extract_numbered_header(section.header)
        
        # Get section path
        section_path = self.section_paths.get(section.header, section.header)
        section_title = section.header
        subsection_title = None
        
        # If we have a numbered header, use it as the primary identifier
        if numbered_header:
            # Update section_path to include numbered header
            if " / " in section_path:
                # Replace the last part with numbered header if it matches
                parts = section_path.split(" / ")
                parts[-1] = numbered_header
                section_path = " / ".join(parts)
            else:
                section_path = numbered_header
            
            section_title = numbered_header
        
        # Split section_path to get subsection if exists
        if " / " in section_path:
            parts = section_path.split(" / ")
            section_title = parts[0] if len(parts) > 0 else section.header
            subsection_title = parts[-1] if len(parts) > 1 else None
        
        # Increment section counter
        self.section_counter += 1
        section_index = self.section_counter
        
        # Build full content with header
        if section.header:
            full_content = f"## {section.header}\n\n{section.content}"
        else:
            full_content = section.content
        
        token_count = count_tokens(full_content)
        
        # Extract numbered header for this section (will be preserved in all chunks)
        numbered_header = self._extract_numbered_header(section.header)
        if numbered_header:
            # Update section_path to use numbered header
            if " / " in section_path:
                parts = section_path.split(" / ")
                parts[-1] = numbered_header
                section_path = " / ".join(parts)
            else:
                section_path = numbered_header
            section_title = numbered_header
        
        # If section fits in one chunk, return it
        if token_count <= self.chunk_size_tokens:
            return [self._create_enhanced_chunk(
                content=full_content,
                doc_id=doc_id,
                section=section,
                section_path=section_path,
                section_title=section_title,
                subsection_title=subsection_title,
                section_index=section_index,
                paragraph_index=1,
                part_number=None
            )]
        
        # Section is too long - need to split
        # First, try splitting by sub-headers
        sub_sections = self._split_by_subheaders(section)
        
        if len(sub_sections) > 1:
            # Successfully split by sub-headers
            chunks = []
            for sub_section in sub_sections:
                # Update hierarchy for sub-section
                self._update_section_hierarchy(sub_section)
                sub_path = self.section_paths.get(sub_section.header, section_path)
                sub_chunks = self._chunk_section_enhanced(
                    section=sub_section,
                    doc_id=doc_id,
                    filename=filename
                )
                chunks.extend(sub_chunks)
            return chunks
        
        # No sub-headers - use recursive chunking with paragraph tracking
        return self._chunk_recursive_enhanced(
            section=section,
            doc_id=doc_id,
            section_path=section_path,
            section_title=section_title,
            subsection_title=subsection_title,
            section_index=section_index,
            filename=filename
        )
    
    def _split_by_subheaders(self, section: MarkdownSection) -> List[MarkdownSection]:
        """Try to split section by sub-headers (### or numbered)."""
        content = section.content
        lines = content.split('\n')
        
        sub_sections: List[MarkdownSection] = []
        current_sub_content: List[str] = []
        current_sub_header: Optional[str] = None
        line_start = section.line_start
        
        for i, line in enumerate(lines):
            # Check for ### header or numbered section
            h3_match = re.match(r'^###\s+(.+)$', line)
            numbered_match = re.match(r'^#{2,}\s+(\d+\.\d+[\.\d]*)\s+(.+)$', line)
            
            if h3_match or numbered_match:
                # Save previous sub-section
                if current_sub_header is not None or current_sub_content:
                    sub_content = '\n'.join(current_sub_content).strip()
                    if sub_content:
                        sub_sections.append(MarkdownSection(
                            level=3,
                            header=current_sub_header or "",
                            content=sub_content,
                            line_start=line_start,
                            line_end=section.line_start + i - 1,
                            parent_header=section.header
                        ))
                
                # Start new sub-section
                if h3_match:
                    current_sub_header = h3_match.group(1).strip()
                else:
                    current_sub_header = numbered_match.group(2).strip()
                current_sub_content = []
                line_start = section.line_start + i
            else:
                current_sub_content.append(line)
        
        # Save last sub-section
        if current_sub_header is not None or current_sub_content:
            sub_content = '\n'.join(current_sub_content).strip()
            if sub_content:
                sub_sections.append(MarkdownSection(
                    level=3,
                    header=current_sub_header or "",
                    content=sub_content,
                    line_start=line_start,
                    line_end=section.line_end,
                    parent_header=section.header
                ))
        
        return sub_sections if len(sub_sections) > 1 else [section]
    
    def _chunk_recursive_enhanced(
        self,
        section: MarkdownSection,
        doc_id: str,
        section_path: str,
        section_title: str,
        subsection_title: Optional[str],
        section_index: int,
        filename: str
    ) -> List[Dict]:
        """Recursively chunk a long section with paragraph tracking."""
        chunks: List[Dict] = []
        content = section.content
        
        # Try splitting by paragraphs first
        paragraphs = self.parser.split_by_paragraphs(content)
        
        if len(paragraphs) > 1:
            current_chunk_parts: List[str] = []
            current_tokens = 0
            paragraph_index = 1
            
            for para in paragraphs:
                para_tokens = count_tokens(para)
                
                if current_tokens + para_tokens > self.chunk_size_tokens and current_chunk_parts:
                    # Save current chunk
                    chunk_content = '\n\n'.join(current_chunk_parts)
                    if section.header:
                        chunk_content = f"## {section.header} (Part {paragraph_index})\n\n{chunk_content}"
                    
                    # Create chunk with preserved numbered header
                    chunks.append(self._create_enhanced_chunk(
                        content=chunk_content,
                        doc_id=doc_id,
                        section=section,  # Original section with numbered header
                        section_path=section_path,
                        section_title=section_title,
                        subsection_title=subsection_title,
                        section_index=section_index,
                        paragraph_index=paragraph_index,
                        part_number=paragraph_index
                    ))
                    
                    # Start new chunk with overlap
                    overlap_text = self._get_overlap_text(current_chunk_parts[-1] if current_chunk_parts else "")
                    current_chunk_parts = [overlap_text, para] if overlap_text else [para]
                    current_tokens = count_tokens('\n\n'.join(current_chunk_parts))
                    paragraph_index += 1
                else:
                    current_chunk_parts.append(para)
                    current_tokens += para_tokens
            
            # Save last chunk
            if current_chunk_parts:
                chunk_content = '\n\n'.join(current_chunk_parts)
                if section.header:
                    chunk_content = f"## {section.header} (Part {paragraph_index})\n\n{chunk_content}"
                
                chunks.append(self._create_enhanced_chunk(
                    content=chunk_content,
                    doc_id=doc_id,
                    section=section,
                    section_path=section_path,
                    section_title=section_title,
                    subsection_title=subsection_title,
                    section_index=section_index,
                    paragraph_index=paragraph_index,
                    part_number=paragraph_index
                ))
            
            return chunks
        
        # If paragraphs didn't work, try list items
        list_items = self.parser.split_by_list_items(content)
        
        if len(list_items) > 1:
            current_chunk_parts: List[str] = []
            current_tokens = 0
            paragraph_index = 1
            
            for item in list_items:
                item_tokens = count_tokens(item)
                
                if current_tokens + item_tokens > self.chunk_size_tokens and current_chunk_parts:
                    chunk_content = '\n'.join(current_chunk_parts)
                    if section.header:
                        chunk_content = f"## {section.header} (Part {paragraph_index})\n\n{chunk_content}"
                    
                    # Create chunk with preserved numbered header
                    chunks.append(self._create_enhanced_chunk(
                        content=chunk_content,
                        doc_id=doc_id,
                        section=section,  # Original section with numbered header
                        section_path=section_path,
                        section_title=section_title,
                        subsection_title=subsection_title,
                        section_index=section_index,
                        paragraph_index=paragraph_index,
                        part_number=paragraph_index
                    ))
                    
                    current_chunk_parts = [item]
                    current_tokens = item_tokens
                    paragraph_index += 1
                else:
                    current_chunk_parts.append(item)
                    current_tokens += item_tokens
            
            if current_chunk_parts:
                chunk_content = '\n'.join(current_chunk_parts)
                if section.header:
                    chunk_content = f"## {section.header} (Part {paragraph_index})\n\n{chunk_content}"
                
                chunks.append(self._create_enhanced_chunk(
                    content=chunk_content,
                    doc_id=doc_id,
                    section=section,
                    section_path=section_path,
                    section_title=section_title,
                    subsection_title=subsection_title,
                    section_index=section_index,
                    paragraph_index=paragraph_index,
                    part_number=paragraph_index
                ))
            
            return chunks
        
        # Last resort: split by sentences (but avoid if possible)
        sentences = self.parser.split_by_sentences(content)
        current_chunk_parts: List[str] = []
        current_tokens = 0
        paragraph_index = 1
        
        for sentence in sentences:
            sentence_tokens = count_tokens(sentence)
            
            if current_tokens + sentence_tokens > self.chunk_size_tokens and current_chunk_parts:
                chunk_content = ' '.join(current_chunk_parts)
                if section.header:
                    chunk_content = f"## {section.header} (Part {paragraph_index})\n\n{chunk_content}"
                
                chunks.append(self._create_enhanced_chunk(
                    content=chunk_content,
                    doc_id=doc_id,
                    section=section,
                    section_path=section_path,
                    section_title=section_title,
                    subsection_title=subsection_title,
                    section_index=section_index,
                    paragraph_index=paragraph_index,
                    part_number=paragraph_index
                ))
                
                overlap_sentences = self._get_overlap_sentences(current_chunk_parts)
                current_chunk_parts = overlap_sentences + [sentence]
                current_tokens = count_tokens(' '.join(current_chunk_parts))
                paragraph_index += 1
            else:
                current_chunk_parts.append(sentence)
                current_tokens += sentence_tokens
        
        if current_chunk_parts:
            chunk_content = ' '.join(current_chunk_parts)
            if section.header:
                chunk_content = f"## {section.header} (Part {paragraph_index})\n\n{chunk_content}"
            
            chunks.append(self._create_enhanced_chunk(
                content=chunk_content,
                doc_id=doc_id,
                section=section,
                section_path=section_path,
                section_title=section_title,
                subsection_title=subsection_title,
                section_index=section_index,
                paragraph_index=paragraph_index,
                part_number=paragraph_index
            ))
        
        return chunks
    
    def _get_overlap_text(self, text: str) -> str:
        """Get overlap text from end of previous chunk."""
        if not text:
            return ""
        sentences = self.parser.split_by_sentences(text)
        overlap_sentences = []
        overlap_tokens = 0
        for sentence in reversed(sentences):
            sentence_tokens = count_tokens(sentence)
            if overlap_tokens + sentence_tokens <= self.chunk_overlap_tokens:
                overlap_sentences.insert(0, sentence)
                overlap_tokens += sentence_tokens
            else:
                break
        return ' '.join(overlap_sentences)
    
    def _get_overlap_sentences(self, sentences: List[str]) -> List[str]:
        """Get overlap sentences from end of previous chunk."""
        overlap_sentences = []
        overlap_tokens = 0
        for sentence in reversed(sentences):
            sentence_tokens = count_tokens(sentence)
            if overlap_tokens + sentence_tokens <= self.chunk_overlap_tokens:
                overlap_sentences.insert(0, sentence)
                overlap_tokens += sentence_tokens
            else:
                break
        return overlap_sentences
    
    def _extract_numbered_header(self, header: str) -> Optional[str]:
        """
        Extract numbered section header pattern.
        
        Examples:
        - "1. Mụcđíchthiếtkế" -> "1. Mụcđíchthiếtkế"
        - "4.1 DanhsáchTanks&Artifacts" -> "4.1 DanhsáchTanks&Artifacts"
        - "7.3 Tankhạngnặng(HeavyTank)" -> "7.3 Tankhạngnặng(HeavyTank)"
        - "4.GiaodiệnTankGarage" -> "4. GiaodiệnTankGarage" (normalize spacing)
        
        Returns:
            Numbered header string or None if not found
        """
        if not header:
            return None
        
        # Pattern: starts with digits, optional dot, optional space, then text
        # Matches: "1. Text", "4.1 Text", "7.3 Text", "4.Text" (no space)
        pattern = r'^(\d+(?:\.\d+)*)\.?\s*(.+)$'
        match = re.match(pattern, header.strip())
        
        if match:
            number_part = match.group(1)
            text_part = match.group(2).strip()
            # Normalize: ensure space after number if missing
            if not header.startswith(f"{number_part}. "):
                return f"{number_part}. {text_part}"
            return header.strip()
        
        return None
    
    def _create_enhanced_chunk(
        self,
        content: str,
        doc_id: str,
        section: MarkdownSection,
        section_path: str,
        section_title: str,
        subsection_title: Optional[str],
        section_index: int,
        paragraph_index: int,
        part_number: Optional[int]
    ) -> Dict:
        """Create a chunk dictionary with enhanced metadata."""
        self.chunk_counter += 1
        chunk_id = f"chunk_{self.chunk_counter:03d}"
        
        # Extract numbered header from section header (preserve even in split chunks)
        numbered_header = self._extract_numbered_header(section.header)
        if not numbered_header:
            numbered_header = section.header  # Fallback to original header
        
        # Detect content type
        content_type = self._detect_content_type(content, section.header)
        
        # Extract doc category from filename or document title
        doc_category = self._extract_doc_category(section.header, content)
        
        # Extract tags (simple keyword extraction)
        tags = self._extract_tags(content, section.header)
        
        token_count = count_tokens(content)
        
        # Build metadata with numbered header prominently featured
        metadata = {
            "section_header": section.header,
            "numbered_header": numbered_header,  # Key field for retrieval
            "content_type": content_type,
            "doc_category": doc_category,
            "tags": tags,
            "parent_header": section.parent_header,
            "part_number": part_number,
            "token_count": token_count
        }
        
        return {
            "chunk_id": chunk_id,
            "doc_id": doc_id,
            "content": content,
            "section_path": section_path,
            "section_title": section_title,
            "subsection_title": subsection_title,
            "section_index": section_index,
            "paragraph_index": paragraph_index,
            "content_type": content_type,
            "doc_category": doc_category,
            "tags": tags,
            "parent_header": section.parent_header,
            "part_number": part_number,
            "token_count": token_count,
            "metadata": metadata,
            # Add numbered_header at top level for easy retrieval
            "numbered_header": numbered_header
        }
    
    def _detect_content_type(self, content: str, header: str = "") -> str:
        """Detect content type: ui, logic, flow, table, monetization, etc."""
        combined = (header + " " + content).lower()
        
        # Check in order of specificity
        if re.search(r'\|.*\|', content, re.MULTILINE):
            return "table"
        elif re.search(r'userflow|flow|user\s+flow', combined, re.IGNORECASE):
            return "flow"
        elif re.search(r'logic|sort|algorithm|calculation', combined, re.IGNORECASE):
            return "logic"
        elif re.search(r'price|cost|purchase|buy|sell|monet|revenue', combined, re.IGNORECASE):
            return "monetization"
        elif re.search(r'note:|note\s*:', combined, re.IGNORECASE):
            return "note"
        else:
            return "ui"
    
    def _extract_doc_category(self, header: str, content: str) -> str:
        """Extract document category from header and content."""
        combined = (header + " " + content).lower()
        
        if "character" in combined or "tank" in combined or "class" in combined:
            return "Character System"
        elif "ui" in combined or "interface" in combined or "screen" in combined:
            return "UI Design"
        elif "gameplay" in combined or "mechanic" in combined or "system" in combined:
            return "Gameplay System"
        elif "asset" in combined:
            return "Asset Design"
        else:
            return "General"
    
    def _extract_tags(self, content: str, header: str = "") -> List[str]:
        """Extract tags from content (simple keyword extraction)."""
        combined = (header + " " + content).lower()
        tags = []
        
        # Common GDD keywords
        keywords = [
            "garage", "tank", "decor", "custom", "result", "reward",
            "selection", "mode", "battle", "upgrade", "skill", "ability"
        ]
        
        for keyword in keywords:
            if keyword in combined:
                tags.append(keyword)
        
        return tags


def generate_doc_id(filename: Path) -> str:
    """Generate document ID from filename."""
    doc_id = filename.stem
    doc_id = doc_id.replace(" ", "_").replace("[", "").replace("]", "")
    doc_id = doc_id.replace("-", "_").replace(",", "_")
    while "__" in doc_id:
        doc_id = doc_id.replace("__", "_")
    return doc_id.strip("_")


def save_chunks_v2(chunks: List[Dict], doc_id: str, output_dir: Path) -> None:
    """Save enhanced chunks to JSON file."""
    output_dir.mkdir(parents=True, exist_ok=True)
    chunks_file = output_dir / f"{doc_id}_chunks.json"
    with open(chunks_file, 'w', encoding='utf-8') as f:
        json.dump(chunks, f, ensure_ascii=False, indent=2)
    print(f"  ✓ Saved {len(chunks)} chunks to {chunks_file}")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Enhanced GDD markdown chunking (v2) with section-first metadata"
    )
    parser.add_argument(
        "--markdown-dir",
        type=Path,
        default=PROJECT_ROOT / "gdd_data" / "markdown",
        help="Directory containing markdown files"
    )
    parser.add_argument(
        "--file",
        type=Path,
        help="Path to a single markdown file"
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=PROJECT_ROOT / "gdd_data_v2" / "chunks",
        help="Output directory for chunks (default: gdd_data_v2/chunks)"
    )
    parser.add_argument(
        "--chunk-size",
        type=int,
        default=800,
        help="Target chunk size in tokens (default: 800)"
    )
    parser.add_argument(
        "--chunk-overlap",
        type=int,
        default=80,
        help="Chunk overlap in tokens (default: 80)"
    )
    parser.add_argument(
        "--max-chunk-size",
        type=int,
        default=1000,
        help="Maximum chunk size before forcing split (default: 1000)"
    )
    parser.add_argument(
        "--limit",
        type=int,
        help="Limit number of files to process (for testing, e.g., --limit 10)"
    )
    parser.add_argument(
        "--translate",
        action="store_true",
        help="Translate English content in chunks to Vietnamese before saving"
    )
    args = parser.parse_args()
    
    # Determine files to process
    if args.file:
        markdown_files = [args.file]
    else:
        markdown_dir = Path(args.markdown_dir)
        if not markdown_dir.exists():
            print(f"ERROR: Markdown directory not found: {markdown_dir}")
            return 1
        markdown_files = sorted(markdown_dir.glob("*.md"))
        
        # Apply limit if specified
        if args.limit and args.limit > 0:
            markdown_files = markdown_files[:args.limit]
            print(f"[LIMIT MODE] Processing only first {args.limit} files for testing")
    
    if not markdown_files:
        print("No markdown files found!")
        return 1
    
    print("=" * 70)
    print("ENHANCED GDD MARKDOWN CHUNKING (v2)")
    print("=" * 70)
    print(f"Markdown directory: {args.markdown_dir}")
    print(f"Output directory: {args.output_dir}")
    print(f"Found {len(markdown_files)} markdown file(s)")
    print("=" * 70)
    print()
    
    chunker = EnhancedMarkdownChunker(
        chunk_size_tokens=args.chunk_size,
        chunk_overlap_tokens=args.chunk_overlap,
        max_chunk_size=args.max_chunk_size
    )
    
    total_chunks = 0
    for i, md_file in enumerate(markdown_files, 1):
        print(f"[{i}/{len(markdown_files)}] Processing: {md_file.name}")
        
        try:
            with open(md_file, 'r', encoding='utf-8') as f:
                markdown_content = f.read()
        except Exception as e:
            print(f"  ✗ ERROR reading file: {e}")
            continue
        
        doc_id = generate_doc_id(md_file)
        
        try:
            chunks = chunker.chunk_document(
                markdown_content=markdown_content,
                doc_id=doc_id,
                filename=str(md_file)
            )
            
            # Translate chunks if flag is enabled
            if args.translate:
                try:
                    # Import translation functions
                    sys.path.insert(0, str(PROJECT_ROOT))
                    from backend.gdd_hyde import detect_language, translate_to_vietnamese
                    
                    translated_count = 0
                    for chunk in chunks:
                        content = chunk.get('content', '')
                        detected_lang = detect_language(content)
                        
                        if detected_lang == 'en':
                            # Translate English content to Vietnamese
                            translated_content, _ = translate_to_vietnamese(content, preserve_technical_terms=True)
                            chunk['content'] = translated_content
                            translated_count += 1
                    
                    if translated_count > 0:
                        print(f"  ✓ Translated {translated_count}/{len(chunks)} chunks to Vietnamese")
                except Exception as e:
                    print(f"  ⚠ Translation failed: {e}")
            
            print(f"  ✓ Generated {len(chunks)} chunks")
            
            if chunks:
                token_counts = [c['token_count'] for c in chunks]
                avg_tokens = sum(token_counts) / len(token_counts)
                max_tokens = max(token_counts)
                min_tokens = min(token_counts)
                print(f"  Token stats: avg={avg_tokens:.0f}, min={min_tokens}, max={max_tokens}")
                
                # Show section path examples
                section_paths = [c.get('section_path', '') for c in chunks[:3]]
                if section_paths:
                    print(f"  Sample section paths: {section_paths[0]}")
            
            # Save chunks
            output_dir = args.output_dir / doc_id
            save_chunks_v2(chunks, doc_id, output_dir)
            
            total_chunks += len(chunks)
        except Exception as e:
            print(f"  ✗ ERROR chunking: {e}")
            import traceback
            traceback.print_exc()
            continue
        
        print()
    
    print("=" * 70)
    print(f"COMPLETE: Processed {len(markdown_files)} file(s), generated {total_chunks} total chunks")
    print("=" * 70)
    
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
