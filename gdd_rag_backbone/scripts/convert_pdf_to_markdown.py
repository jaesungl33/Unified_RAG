"""
Convert a PDF to Markdown using Marker (same as the indexing pipeline).

Writes the generated .md file and copies the images folder so relative refs work.

Usage (from project root with venv activated):
    python -m gdd_rag_backbone.scripts.convert_pdf_to_markdown --file "path/to/document.pdf"
    python -m gdd_rag_backbone.scripts.convert_pdf_to_markdown --file "path/to/document.pdf" --output "path/to/output.md"
"""

from gdd_rag_backbone.scripts.marker_utils import run_marker, find_marker_output_dir
import argparse
import logging
import shutil
import tempfile
from pathlib import Path

# Add project root for imports
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in __import__("sys").path:
    __import__("sys").path.insert(0, str(PROJECT_ROOT))


logger = logging.getLogger(__name__)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Convert PDF to Markdown using Marker (same as pipeline)."
    )
    parser.add_argument("--file", type=Path, required=True,
                        help="Path to PDF file")
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Output .md file or directory (default: same dir as PDF, <stem>.md)",
    )
    parser.add_argument("-v", "--verbose",
                        action="store_true", help="Verbose logging")
    args = parser.parse_args()

    if args.verbose:
        logging.basicConfig(level=logging.INFO)

    pdf_path = args.file.resolve()
    if not pdf_path.exists():
        raise SystemExit(f"PDF not found: {pdf_path}")
    if pdf_path.suffix.lower() != ".pdf":
        raise SystemExit("--file must be a .pdf file")

    stem = pdf_path.stem
    if args.output is not None:
        out = args.output.resolve()
        if out.suffix.lower() == ".md":
            output_md = out
            output_dir = out.parent
        else:
            output_dir = out
            output_md = output_dir / f"{stem}.md"
    else:
        output_dir = pdf_path.parent
        output_md = output_dir / f"{stem}.md"

    output_dir.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="pdf2md_") as tmp:
        ok, err = run_marker(pdf_path, Path(tmp))
        if not ok:
            raise SystemExit(f"Marker failed: {err}")
        marker_dir = find_marker_output_dir(Path(tmp), pdf_path.stem)
        if not marker_dir:
            raise SystemExit(
                "Marker did not produce expected output folder with .md file")
        md_files = list(marker_dir.glob("*.md"))
        if not md_files:
            raise SystemExit("No .md file in Marker output")
        src_md = md_files[0]
        src_images = marker_dir / "images"

        markdown_content = src_md.read_text(encoding="utf-8", errors="replace")
        output_md.write_text(markdown_content, encoding="utf-8")
        print(f"Wrote: {output_md}")

        if src_images.exists():
            dest_images = output_dir / "images"
            if dest_images.exists():
                shutil.rmtree(dest_images)
            shutil.copytree(src_images, dest_images)
            print(
                f"Wrote: {dest_images}/ ({len(list(dest_images.iterdir()))} files)")

    print("Done.")


if __name__ == "__main__":
    main()
