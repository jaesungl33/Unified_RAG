"""
Index a single PDF using Marker (PDF → Markdown + images), then chunk and index to Supabase.

Images extracted by Marker are uploaded to gdd_pdfs/{doc_id}/images/ and referenced in markdown.

Usage (from project root with venv activated):
    python -m gdd_rag_backbone.scripts.index_pdf_with_marker --file "path/to/document.pdf" [--dry-run]
"""

from werkzeug.utils import secure_filename
from backend.storage.supabase_client import (
    upload_gdd_image_to_storage,
    get_supabase_client,
)
from backend.storage.gdd_supabase_storage import index_gdd_chunks_to_supabase, USE_SUPABASE
from gdd_rag_backbone.markdown_chunking import MarkdownChunker
from gdd_rag_backbone.scripts.chunk_markdown_files import generate_doc_id
import argparse
import logging
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any, Callable

# Add project root for imports
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in __import__("sys").path:
    __import__("sys").path.insert(0, str(PROJECT_ROOT))


logger = logging.getLogger(__name__)


def _run_marker(pdf_path: Path, output_dir: Path) -> Tuple[bool, str]:
    """
    Run Marker CLI: marker_single <pdf_path> --output_format markdown --output_dir <output_dir>.
    On success, output is output_dir/<stem>/<stem>.md and output_dir/<stem>/images/.
    """
    exe = shutil.which("marker_single")
    if not exe:
        return False, "marker_single CLI not found (pip install marker-pdf)"
    try:
        cmd = [
            exe,
            str(pdf_path),
            "--output_format",
            "markdown",
            "--output_dir",
            str(output_dir),
        ]
        logger.info("Running: %s", " ".join(cmd))
        r = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=900,
            cwd=str(PROJECT_ROOT),
        )
        if r.returncode != 0:
            return False, (r.stderr or r.stdout or f"exit code {r.returncode}")
        return True, ""
    except subprocess.TimeoutExpired:
        return False, "Marker timed out (900s)"
    except Exception as e:
        return False, str(e)


def _find_marker_output_dir(output_dir: Path, pdf_stem: str) -> Optional[Path]:
    """
    Marker writes to output_dir/<name>/ where <name> is derived from the PDF.
    Return the single subfolder that contains a .md file, or the one matching pdf_stem.
    """
    if not output_dir.exists():
        return None
    subs = [p for p in output_dir.iterdir() if p.is_dir()]
    for sub in subs:
        md_candidates = list(sub.glob("*.md"))
        if md_candidates:
            return sub
    # Try exact stem
    stem_dir = output_dir / pdf_stem
    if stem_dir.exists() and stem_dir.is_dir():
        return stem_dir
    return None


def _replace_markdown_image_refs(markdown: str, filename_to_url: Dict[str, str]) -> str:
    """
    Replace image refs in markdown: ![alt](filename) -> ![alt](url).
    Matches both ![alt](file.webp) and ![alt](path/file.webp); replace by basename match.
    """
    if not filename_to_url:
        return markdown

    def repl(match: re.Match) -> str:
        alt, url_part = match.group(1), match.group(2)
        base = url_part.split("/")[-1].split("?")[0]
        if base in filename_to_url:
            return f"![{alt}]({filename_to_url[base]})"
        return match.group(0)

    pattern = re.compile(r"!\[([^\]]*)\]\(([^)]+)\)")
    return pattern.sub(repl, markdown)


def _get_embedding_provider():
    """Resolve embedding provider: Ollama → OpenAI → Qwen (same logic as gdd_service)."""
    from gdd_rag_backbone.llm_providers import QwenProvider

    provider = None
    provider_errors = []

    # Ollama
    openai_base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
    if "localhost:11434" in openai_base_url or "127.0.0.1:11434" in openai_base_url:
        try:
            embedding_model = os.getenv("EMBEDDING_MODEL", "mxbai-embed-large")
            provider = QwenProvider(
                api_key=os.getenv("OPENAI_API_KEY", "ollama"),
                base_url=openai_base_url,
                embedding_model=embedding_model,
            )
            if "mxbai-embed-large" in embedding_model:
                provider.embedding_dim = 1024
            elif "nomic-embed-text" in embedding_model:
                provider.embedding_dim = 768
            else:
                provider.embedding_dim = 768
            logger.info("Using Ollama embeddings: %s", embedding_model)
            return provider
        except Exception as e:
            provider_errors.append(f"Ollama: {e}")

    # OpenAI
    openai_key = os.getenv("OPENAI_API_KEY")
    if openai_key and "openai.com" in openai_base_url.lower():
        try:
            embedding_model = os.getenv(
                "EMBEDDING_MODEL", "text-embedding-3-small")
            provider = QwenProvider(
                api_key=openai_key,
                base_url=openai_base_url,
                embedding_model=embedding_model,
            )
            if "3-small" in embedding_model:
                provider.embedding_dim = 1536
            elif "3-large" in embedding_model:
                provider.embedding_dim = 3072
            elif "ada-002" in embedding_model:
                provider.embedding_dim = 1536
            else:
                provider.embedding_dim = 1536
            logger.info("Using OpenAI embeddings: %s", embedding_model)
            return provider
        except Exception as e:
            provider_errors.append(f"OpenAI: {e}")

    # Qwen/DashScope
    try:
        provider = QwenProvider()
        if provider.api_key:
            logger.info("Using Qwen/DashScope embeddings")
            return provider
        raise ValueError("Qwen API key not configured")
    except Exception as e:
        provider_errors.append(f"Qwen: {e}")

    raise RuntimeError(
        "No embedding provider available. Configure OPENAI_BASE_URL + OPENAI_API_KEY (Ollama) or "
        "OPENAI_API_KEY (OpenAI) or DASHSCOPE_API_KEY (Qwen). Errors: " +
        "; ".join(provider_errors)
    )


def index_pdf_with_marker(
    pdf_path: Path,
    dry_run: bool = False,
    progress_cb: Optional[Callable[[str], None]] = None,
) -> Dict[str, Any]:
    """
    Convert a PDF to Markdown with Marker, upload images to gdd_pdfs/{doc_id}/images/,
    update markdown refs to public URLs, chunk, and index to Supabase.

    progress_cb: optional callable(step_text: str) for UI progress (e.g. "Converting with Marker").
    """
    def bump(step: str) -> None:
        if callable(progress_cb):
            progress_cb(step)

    if not pdf_path.is_file() or pdf_path.suffix.lower() != ".pdf":
        return {"status": "error", "message": f"Not a PDF file: {pdf_path}"}

    if not USE_SUPABASE:
        return {"status": "error", "message": "Supabase is not configured"}

    original_filename = pdf_path.name
    doc_id = generate_doc_id(Path(original_filename))
    pdf_filename = secure_filename(original_filename).replace(" ", "_")

    if dry_run:
        return {
            "status": "dry_run",
            "message": f"Would index {original_filename} as doc_id={doc_id} (Marker + images + chunk + Supabase)",
            "doc_id": doc_id,
        }

    with tempfile.TemporaryDirectory(prefix="marker_out_") as temp_dir:
        out_dir = Path(temp_dir)

        # 1) Run Marker
        bump("Converting PDF with Marker")
        ok, err = _run_marker(pdf_path, out_dir)
        if not ok:
            return {"status": "error", "message": f"Marker failed: {err}"}

        # 2) Locate output folder and files
        bump("Reading Marker output")
        pdf_stem = pdf_path.stem
        marker_dir = _find_marker_output_dir(out_dir, pdf_stem)
        if not marker_dir:
            return {"status": "error", "message": "Marker did not produce expected output folder with .md file"}

        md_files = list(marker_dir.glob("*.md"))
        if not md_files:
            return {"status": "error", "message": "No .md file in Marker output"}
        md_path = md_files[0]
        markdown_content = md_path.read_text(
            encoding="utf-8", errors="replace")

        images_dir = marker_dir / "images"
        image_paths = list(images_dir.glob("*")) if images_dir.exists() else []
        image_paths = [p for p in image_paths if p.is_file()]

        # 3) Upload images to gdd_pdfs/{doc_id}/images/ and build metadata + URL map
        bump("Uploading images to storage")
        filename_to_url: Dict[str, str] = {}
        images_metadata: List[Dict[str, str]] = []
        bucket_path_prefix = f"{doc_id}/images"

        for img_path in image_paths:
            name = img_path.name
            try:
                raw = img_path.read_bytes()
            except Exception as e:
                logger.warning("Skip image %s: %s", name, e)
                continue
            content_type = "image/webp" if name.lower().endswith(".webp") else "image/png"
            url = upload_gdd_image_to_storage(
                doc_id, name, raw, content_type=content_type)
            if url:
                filename_to_url[name] = url
                images_metadata.append(
                    {
                        "filename": name,
                        "url": url,
                        "path": f"{bucket_path_prefix}/{name}",
                    }
                )
            else:
                logger.warning("Upload failed for image %s", name)

        # 4) Update markdown: replace image refs with public URLs (before chunking)
        markdown_with_urls = _replace_markdown_image_refs(
            markdown_content, filename_to_url)

        # 5) Upload PDF to gdd_pdfs
        bump("Uploading PDF to storage")
        try:
            client = get_supabase_client(use_service_key=True)
            pdf_bytes = pdf_path.read_bytes()
            client.storage.from_("gdd_pdfs").upload(
                path=pdf_filename,
                file=pdf_bytes,
                file_options={
                    "content-type": "application/pdf",
                    "cache-control": "3600",
                    "upsert": "true",
                },
            )
            logger.info("Uploaded PDF to gdd_pdfs: %s", pdf_filename)
        except Exception as e:
            logger.warning("PDF upload to storage failed: %s", e)

        # 6) Chunk markdown (same as current pipeline)
        bump("Chunking Markdown")
        chunker = MarkdownChunker()
        chunks = chunker.chunk_document(
            markdown_content=markdown_with_urls,
            doc_id=doc_id,
            filename=original_filename,
        )

        if not chunks:
            return {"status": "error", "message": "Chunker produced no chunks"}

        # 7) Embedding provider
        bump("Generating embeddings")
        provider = _get_embedding_provider()

        # 8) Index to Supabase (markdown with URLs, pdf_storage_path, images JSONB)
        bump("Indexing into Supabase")
        index_gdd_chunks_to_supabase(
            doc_id=doc_id,
            chunks=chunks,
            provider=provider,
            markdown_content=markdown_with_urls,
            pdf_storage_path=pdf_filename,
            images=images_metadata if images_metadata else None,
        )

    bump("Completed")
    return {
        "status": "success",
        "message": f"Indexed {original_filename} as {doc_id} (markdown + {len(images_metadata)} images)",
        "doc_id": doc_id,
    }


def main():
    logging.basicConfig(level=logging.INFO,
                        format="%(levelname)s: %(message)s")
    parser = argparse.ArgumentParser(
        description="Index a PDF using Marker (PDF → Markdown + images), upload images to Supabase, chunk and index."
    )
    parser.add_argument(
        "--file",
        type=Path,
        required=True,
        help="Path to the PDF file",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Only print what would be done",
    )
    args = parser.parse_args()
    result = index_pdf_with_marker(args.file, dry_run=args.dry_run)
    print(result.get("message", result))
    if result.get("status") == "error":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
