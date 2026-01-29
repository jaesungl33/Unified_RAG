"""
List section headers from markdown using a stricter, more robust rule inspired by
`pdf_image_extractor/extract_images.py` (its `extract_headers_from_page`).

We treat a line as a section header if:
  1) It is a markdown header line of level 2+ (starts with ##, ###, ####, ...)
  2) After the hashes, the text begins with a numbered section pattern AND the
     first non-space character after the numbering is a letter (not a digit/_).

This matches headers like:
  - ## 1. Meta System
  - ### 4.1 Detect Emotional State
  - #### 2.3.1 Edge cases
  - ## 1.Meta

and ignores:
  - # Title                        (level 1; by design)
  - ## Overview                    (not numbered)
  - ### 1. 2025 Roadmap            (starts with digit after numbering -> rejected)

Usage:
  # From file
  python -m gdd_rag_backbone.scripts.list_section_headers_strict --file "path/to/doc.md"

  # From stdin
  cat "path/to/doc.md" | python -m gdd_rag_backbone.scripts.list_section_headers_strict
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import Iterable, List, Tuple


# Markdown header line (level 2+ only): "## Header" / "### Header" / ...
MD_HEADER_PATTERN = re.compile(r"^(#{2,})\s+(.+)$")

# Inspired by pdf_image_extractor's header heuristic:
#   ^\d+(?:\.\d+)*\.?\s*[^\W\d_]
# Meaning:
# - Start with digits, optionally ".digits" repeats, optional trailing dot, optional spaces,
# - then a unicode "word" char that is NOT a digit or underscore (i.e., a letter in most cases).
NUMBERED_LETTER_START = re.compile(r"^\d+(?:\.\d+)*\.?\s*[^\W\d_]", re.UNICODE)


def iter_lines(markdown_text: str) -> Iterable[Tuple[int, str]]:
    for idx, line in enumerate(markdown_text.splitlines(), start=1):
        yield idx, line


def extract_strict_headers(markdown_text: str) -> List[Tuple[int, str, str, str]]:
    """
    Returns a list of matches:
      (line_number, raw_line, numbering, title)
    """
    out: List[Tuple[int, str, str, str]] = []
    for line_no, line in iter_lines(markdown_text):
        m = MD_HEADER_PATTERN.match(line)
        if not m:
            continue
        header_marks = m.group(1)
        header_text = m.group(2).strip()

        # Only treat level 2+ as sections; '# ' is ignored on purpose.
        if len(header_marks) < 2:
            continue

        # Apply the improved rule: must start with numbered section AND then a letter.
        if not NUMBERED_LETTER_START.match(header_text):
            continue

        # Extract a normalized "numbering" and "title" for display.
        # We split at the first whitespace after the numbering segment if possible.
        # Example: "4.1 Detect" -> numbering="4.1", title="Detect"
        #          "1.Meta" -> numbering="1", title="Meta" (best-effort)
        num_match = re.match(r"^(\d+(?:\.\d+)*)(?:\.)?\s*(.*)$", header_text)
        if not num_match:
            continue
        numbering = num_match.group(1).strip()
        title = (num_match.group(2) or "").strip()
        out.append((line_no, line, numbering, title))
    return out


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Print section headers (markdown level 2+) that begin with numbered section + letter (strict)."
    )
    parser.add_argument(
        "--file",
        type=Path,
        default=None,
        help="Optional markdown file path. If omitted, reads markdown from stdin.",
    )
    parser.add_argument(
        "--raw",
        action="store_true",
        help="Print raw matching header lines (default prints normalized: '<number> <title>').",
    )
    args = parser.parse_args()

    if args.file is not None:
        text = args.file.read_text(encoding="utf-8", errors="replace")
    else:
        # Read from stdin (supports piping)
        text = sys.stdin.read()

    matches = extract_strict_headers(text)
    if not matches:
        return

    for line_no, raw_line, numbering, title in matches:
        if args.raw:
            print(raw_line)
        else:
            print(f"{numbering} {title}")


if __name__ == "__main__":
    main()

