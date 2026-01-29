"""
Index a single document from an existing Marker output folder (Markdown + images),
then chunk and index to Supabase.

This script assumes **step 1 (PDF → Markdown with Marker)** is already done.
It starts from the folder that contains:
- One Markdown file (`*.md`)
- The original PDF (`*.pdf`) for storage
- Extracted images (either in the same folder or inside an `images/` subfolder)

Usage (from project root with venv activated):

    python -m gdd_rag_backbone.scripts.index_marker_markdown_folder \\
        --marker-dir "rag_storage/new markdown files/[MONETIZATION] - BATTLE PASS SYSTEM"
        [--dry-run]
"""

import argparse
import logging
import os
import re
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any

from werkzeug.utils import secure_filename

from backend.storage.supabase_client import (
    upload_gdd_image_to_storage,
    get_supabase_client,
)
from backend.storage.gdd_supabase_storage import index_gdd_chunks_to_supabase, USE_SUPABASE
from gdd_rag_backbone.markdown_chunking import MarkdownChunker
from gdd_rag_backbone.scripts.chunk_markdown_files import generate_doc_id


logger = logging.getLogger(__name__)


def _find_markdown_file(marker_dir: Path) -> Optional[Path]:
    """Return the single markdown file in the folder (or None if not found/ambiguous)."""
    md_files = list(marker_dir.glob("*.md"))
    if not md_files:
        return None
    if len(md_files) > 1:
        logger.warning(
            "Multiple markdown files found in %s, using the first one: %s", marker_dir, md_files[0])
    return md_files[0]


def _find_pdf_file(marker_dir: Path) -> Optional[Path]:
    """Return the single PDF file in the folder (or None if not found/ambiguous)."""
    pdf_files = list(marker_dir.glob("*.pdf"))
    if not pdf_files:
        return None
    if len(pdf_files) > 1:
        logger.warning(
            "Multiple PDF files found in %s, using the first one: %s", marker_dir, pdf_files[0])
    return pdf_files[0]


def _collect_image_files(marker_dir: Path) -> List[Path]:
    """
    Collect image files from a Marker output folder.

    Supports two patterns:
      1) Images in a dedicated `images/` subfolder.
      2) Images flat in the same folder as the markdown (alongside .md, .pdf, .json, etc.).
    """
    images: List[Path] = []

    images_subdir = marker_dir / "images"
    if images_subdir.exists() and images_subdir.is_dir():
        # Marker default layout: <dir>/<stem>.md and <dir>/images/*
        images = [p for p in images_subdir.glob("*") if p.is_file()]
    else:
        # Fallback: treat any non-md / non-pdf / non-json files in the folder as images
        for p in marker_dir.iterdir():
            if not p.is_file():
                continue
            suffix = p.suffix.lower()
            if suffix in {".md", ".pdf", ".json"}:
                continue
            images.append(p)

    return images


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


def index_marker_markdown_folder(
    marker_dir: Path,
    dry_run: bool = False,
) -> Dict[str, Any]:
    """
    Take an existing Marker output folder (Markdown + images + PDF),
    upload images and PDF to Supabase, chunk the markdown, and index everything.
    """
    if not marker_dir.is_dir():
        return {"status": "error", "message": f"Not a directory: {marker_dir}"}

    if not USE_SUPABASE:
        return {"status": "error", "message": "Supabase is not configured"}

    md_path = _find_markdown_file(marker_dir)
    if not md_path:
        return {"status": "error", "message": f"No markdown file (*.md) found in {marker_dir}"}

    pdf_path = _find_pdf_file(marker_dir)

    # Derive doc_id from the markdown filename (same logic as other scripts)
    original_filename = md_path.name
    doc_id = generate_doc_id(Path(original_filename))
    pdf_filename = None
    if pdf_path:
        pdf_filename = secure_filename(pdf_path.name).replace(" ", "_")

    if dry_run:
        return {
            "status": "dry_run",
            "message": f"Would index Marker folder {marker_dir} as doc_id={doc_id} (images + chunk + Supabase)",
            "doc_id": doc_id,
        }

    # 1) Read markdown and collect images
    markdown_content = md_path.read_text(encoding="utf-8", errors="replace")
    image_paths = _collect_image_files(marker_dir)

    # 2) Upload images to gdd_pdfs/{doc_id}/images/ and build metadata + URL map
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

        ext = name.lower().split(".")[-1]
        if ext in {"jpg", "jpeg"}:
            content_type = "image/jpeg"
        elif ext == "png":
            content_type = "image/png"
        elif ext == "webp":
            content_type = "image/webp"
        else:
            # Fallback; most browsers will still handle it
            content_type = "image/png"

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

    # 3) Update markdown: replace image refs with public URLs (before chunking)
    markdown_with_urls = _replace_markdown_image_refs(
        markdown_content, filename_to_url)

    # 4) Upload PDF to gdd_pdfs (if we have it)
    if pdf_path:
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

    # 5) Chunk markdown (same as current pipeline)
    chunker = MarkdownChunker()
    chunks = chunker.chunk_document(
        markdown_content=markdown_with_urls,
        doc_id=doc_id,
        filename=original_filename,
    )

    if not chunks:
        return {"status": "error", "message": "Chunker produced no chunks"}

    # 6) Embedding provider
    provider = _get_embedding_provider()

    # 7) Index to Supabase (markdown with URLs, pdf_storage_path, images JSONB)
    index_gdd_chunks_to_supabase(
        doc_id=doc_id,
        chunks=chunks,
        provider=provider,
        markdown_content=markdown_with_urls,
        pdf_storage_path=pdf_filename,
        images=images_metadata if images_metadata else None,
    )

    return {
        "status": "success",
        "message": f"Indexed Marker folder {marker_dir.name} as {doc_id} (markdown + {len(images_metadata)} images)",
        "doc_id": doc_id,
    }


def main():
    logging.basicConfig(level=logging.INFO,
                        format="%(levelname)s: %(message)s")
    parser = argparse.ArgumentParser(
        description="Index an existing Marker output folder (Markdown + images) into Supabase."
    )
    parser.add_argument(
        "--marker-dir",
        type=Path,
        required=True,
        help="Path to the Marker output folder containing .md, .pdf, and images.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Only print what would be done",
    )
    args = parser.parse_args()
    result = index_marker_markdown_folder(
        args.marker_dir, dry_run=args.dry_run)
    print(result.get("message", result))
    if result.get("status") == "error":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
