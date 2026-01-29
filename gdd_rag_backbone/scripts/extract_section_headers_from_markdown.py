"""
Extract section headers from a markdown file using the exact pipeline logic:

  1. MarkdownParser.parse() — document-level sections (numbered regex)
  2. MarkdownChunker._split_by_subheaders() — sub-headers inside oversized sections

Same logic as upload/indexing; outputs every header that would become section_heading on chunks.

Usage (from project root with venv activated):
    python -m gdd_rag_backbone.scripts.extract_section_headers_from_markdown path/to/doc.md
    python -m gdd_rag_backbone.scripts.extract_section_headers_from_markdown --file "gdd_rag_backbone/scripts/[MONETIZATION] - BATTLE PASS SYSTEM.md"
    cat path/to/doc.md | python -m gdd_rag_backbone.scripts.extract_section_headers_from_markdown
"""

from gdd_rag_backbone.markdown_chunking.chunker import MarkdownChunker
from gdd_rag_backbone.markdown_chunking.markdown_parser import MarkdownParser
import argparse
import sys
from pathlib import Path

# Add project root for imports
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def collect_headers(markdown_content: str) -> list[tuple[int, str, str | None]]:
    """
    Extract all section headers using the same two steps as the pipeline.

    Step 1: MarkdownParser.parse() — document-level sections (numbered lines only).
    Step 2: For each section, MarkdownChunker._split_by_subheaders() — if the section
            would be split by sub-headers, use those sub-section headers; else use the
            top-level section header.

    Returns list of (level, header_text, parent_header).
    """
    parser = MarkdownParser()
    chunker = MarkdownChunker()
    sections = parser.parse(markdown_content)
    out: list[tuple[int, str, str | None]] = []

    for section in sections:
        sub_sections = chunker._split_by_subheaders(section)
        if len(sub_sections) > 1:
            for sub in sub_sections:
                out.append((sub.level, sub.header, sub.parent_header))
        else:
            out.append((section.level, section.header, section.parent_header))

    return out


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Extract section headers from markdown (same logic as pipeline: parse + _split_by_subheaders)."
    )
    parser.add_argument(
        "markdown_file",
        nargs="?",
        type=Path,
        default=None,
        help="Path to markdown file (omit to read from stdin)",
    )
    parser.add_argument(
        "--file", "-f",
        type=Path,
        default=None,
        dest="file_path",
        help="Path to markdown file (alternative to positional)",
    )
    args = parser.parse_args()

    path = args.file_path or args.markdown_file
    if path is not None:
        path = path.resolve()
        if not path.exists():
            sys.exit(f"File not found: {path}")
        markdown_content = path.read_text(encoding="utf-8", errors="replace")
        source_label = str(path)
    else:
        markdown_content = sys.stdin.read()
        source_label = "<stdin>"

    headers = collect_headers(markdown_content)

    print(f"# Section headers (pipeline logic: MarkdownParser.parse + _split_by_subheaders)")
    print(f"# Source: {source_label}")
    print(f"# Total: {len(headers)}\n")

    for i, (level, header, parent) in enumerate(headers, 1):
        indent = "  " * (level - 1) if level else ""
        parent_str = f"  [parent: {parent}]" if parent else ""
        print(f"{i:4d}  L{level}  {indent}{header}{parent_str}")


if __name__ == "__main__":
    main()
