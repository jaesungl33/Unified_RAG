"""
CLI helper to convert PDF files to Markdown using Docling.

Default output directory is the sibling `markdown/` folder in this directory.

Example:
    python pdf_to_markdown.py --input docs --ocr-langs en
"""
from __future__ import annotations

import argparse
import logging
import string
from pathlib import Path
from typing import Iterable, List, Sequence

from docling.document_converter import DocumentConverter

logger = logging.getLogger(__name__)


_CONTROL_CHARS = {
    # ASCII control chars 0x00–0x1F, excluding tab/newline/carriage-return
    *[c for c in map(chr, range(0x00, 0x20)) if c not in ("\t", "\n", "\r")],
    # DEL
    chr(0x7F),
    # Common replacement characters seen in bad PDF exports
    "\uFFFD",  # �
}
_CONTROL_TRANSLATION = {ord(c): None for c in _CONTROL_CHARS}


def clean_markdown(text: str) -> str:
    """Remove non-printable/control artifacts while preserving content & layout.

    - Strips control chars (except tab/newline/CR) and typical replacement chars.
    - Leaves headings, tables, and ordering unchanged.
    """
    cleaned = text.translate(_CONTROL_TRANSLATION)
    # Ensure the string is cleanly encodable as UTF-8; drop any remaining bad codepoints.
    return cleaned.encode("utf-8", "ignore").decode("utf-8")


def find_pdfs(path: Path) -> List[Path]:
    """Return a sorted list of PDF files under the given path."""
    if path.is_file():
        if path.suffix.lower() != ".pdf":
            raise ValueError(f"Input file is not a PDF: {path}")
        return [path]

    if not path.exists():
        raise FileNotFoundError(f"Input path does not exist: {path}")

    pdfs = sorted(p for p in path.rglob("*.pdf") if p.is_file())
    if not pdfs:
        raise FileNotFoundError(f"No PDF files found under {path}")
    return pdfs


def convert_pdf(
    converter: DocumentConverter,
    pdf_path: Path,
    output_dir: Path,
    ocr_langs: Sequence[str] | None = None,
    overwrite: bool = False,
) -> Path:
    """Convert a single PDF to Markdown and save it to output_dir."""
    output_dir.mkdir(parents=True, exist_ok=True)
    md_path = output_dir / f"{pdf_path.stem}.md"
    if md_path.exists() and not overwrite:
        logger.info("Skipping existing file (use --overwrite to replace): %s", md_path)
        return md_path

    convert_kwargs = {}
    # Docling expects "languages" (not ocr_langs) when providing OCR languages.
    if ocr_langs:
        convert_kwargs["languages"] = ocr_langs

    result = converter.convert(str(pdf_path), **convert_kwargs)
    markdown = result.document.export_to_markdown()
    markdown = clean_markdown(markdown)
    md_path.write_text(markdown, encoding="utf-8")
    logger.info("Wrote %s", md_path)
    return md_path


def convert_all(
    input_path: Path,
    output_dir: Path,
    ocr_langs: Sequence[str] | None = None,
    overwrite: bool = False,
) -> List[Path]:
    """Convert one or more PDFs to Markdown."""
    converter = DocumentConverter()
    pdfs = find_pdfs(input_path)
    outputs: List[Path] = []
    for pdf in pdfs:
        try:
            outputs.append(
                convert_pdf(
                    converter=converter,
                    pdf_path=pdf,
                    output_dir=output_dir,
                    ocr_langs=ocr_langs,
                    overwrite=overwrite,
                )
            )
        except Exception as exc:  # noqa: BLE001
            logger.error("Failed to convert %s: %s", pdf, exc)
    return outputs


def parse_args(argv: Iterable[str] | None = None) -> argparse.Namespace:
    default_output = Path(__file__).parent / "markdown"
    parser = argparse.ArgumentParser(
        description="Convert PDF files to Markdown using Docling.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--input",
        "-i",
        required=True,
        help="Path to a single PDF file or a directory containing PDFs.",
    )
    parser.add_argument(
        "--output",
        "-o",
        default=str(default_output),
        help="Directory where Markdown files will be written.",
    )
    parser.add_argument(
        "--ocr-langs",
        type=lambda s: [lang.strip() for lang in s.split(",") if lang.strip()],
        default=None,
        help="Comma-separated list of language codes for OCR (e.g., 'en,fr').",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite existing Markdown files.",
    )
    return parser.parse_args(argv)


def main(argv: Iterable[str] | None = None) -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
    args = parse_args(argv)
    input_path = Path(args.input)
    output_dir = Path(args.output)
    convert_all(
        input_path=input_path,
        output_dir=output_dir,
        ocr_langs=args.ocr_langs,
        overwrite=args.overwrite,
    )


if __name__ == "__main__":
    main()

