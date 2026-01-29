"""
Index one existing markdown folder to Supabase: upload images, replace refs with public URLs, chunk, index.
Use when you already have converted markdown + images (e.g. from Chandra or manual). Only .md and images are stored in Supabase (no PDF).

Usage (from project root with venv activated):
    python -m gdd_rag_backbone.scripts.index_markdown_folder_to_supabase --folder "rag_storage/new markdown files/[Combat Module] [Tank War] Match Flow Polish" [--dry-run]

Folder must contain:
  - One .md file (same base name as folder or any .md)
  - Image files (.webp, .png, .jpg, etc.) in the same folder
"""

import argparse
import logging
import os
import re
from pathlib import Path
from typing import Dict, List, Any

# Add project root for imports
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in __import__("sys").path:
    __import__("sys").path.insert(0, str(PROJECT_ROOT))

from gdd_rag_backbone.scripts.chunk_markdown_files import generate_doc_id
from gdd_rag_backbone.markdown_chunking import MarkdownChunker
from backend.storage.gdd_supabase_storage import index_gdd_chunks_to_supabase, USE_SUPABASE
from backend.storage.supabase_client import upload_gdd_image_to_storage

logger = logging.getLogger(__name__)

# Image extensions to upload from folder
IMAGE_EXTENSIONS = {".webp", ".png", ".jpg", ".jpeg", ".gif"}


def _replace_markdown_image_refs(markdown: str, filename_to_url: Dict[str, str]) -> str:
    """Replace image refs in markdown: ![alt](filename) -> ![alt](url). Uses basename match."""
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
    """Resolve embedding provider: Ollama -> OpenAI -> Qwen (same as gdd_service)."""
    from gdd_rag_backbone.llm_providers import QwenProvider

    provider = None
    provider_errors = []
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

    openai_key = os.getenv("OPENAI_API_KEY")
    if openai_key and "openai.com" in openai_base_url.lower():
        try:
            embedding_model = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
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

    try:
        provider = QwenProvider()
        if provider.api_key:
            logger.info("Using Qwen/DashScope embeddings")
            return provider
        raise ValueError("Qwen API key not configured")
    except Exception as e:
        provider_errors.append(f"Qwen: {e}")

    raise RuntimeError(
        "No embedding provider available. Errors: " + "; ".join(provider_errors)
    )


def index_markdown_folder_to_supabase(
    folder_path: Path,
    dry_run: bool = False,
) -> Dict[str, Any]:
    """
    Index one markdown folder: upload images to gdd_pdfs/{doc_id}/images/, replace image refs
    with public URLs in markdown, chunk, and index to Supabase. Only .md and images are stored (no PDF).
    """
    folder_path = folder_path.resolve()
    if not folder_path.is_dir():
        return {"status": "error", "message": f"Not a directory: {folder_path}"}

    if not USE_SUPABASE:
        return {"status": "error", "message": "Supabase is not configured"}

    # Find single .md file in folder
    md_files = list(folder_path.glob("*.md"))
    if not md_files:
        return {"status": "error", "message": f"No .md file in folder: {folder_path}"}
    if len(md_files) > 1:
        # Use the one that matches folder name, or first
        folder_stem = folder_path.name
        for m in md_files:
            if m.stem == folder_stem:
                md_path = m
                break
        else:
            md_path = md_files[0]
    else:
        md_path = md_files[0]

    doc_id = generate_doc_id(Path(md_path.stem))
    original_filename = md_path.name

    if dry_run:
        image_count = sum(
            1 for p in folder_path.iterdir()
            if p.is_file() and p.suffix.lower() in IMAGE_EXTENSIONS
        )
        return {
            "status": "dry_run",
            "message": f"Would index folder as doc_id={doc_id} (markdown + {image_count} images, no PDF)",
            "doc_id": doc_id,
        }

    markdown_content = md_path.read_text(encoding="utf-8", errors="replace")

    # Collect image files in same folder (no images/ subfolder)
    image_paths = [
        p for p in folder_path.iterdir()
        if p.is_file() and p.suffix.lower() in IMAGE_EXTENSIONS
    ]

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
        if name.lower().endswith((".jpg", ".jpeg")):
            content_type = "image/jpeg"
        url = upload_gdd_image_to_storage(doc_id, name, raw, content_type=content_type)
        if url:
            filename_to_url[name] = url
            images_metadata.append({
                "filename": name,
                "url": url,
                "path": f"{bucket_path_prefix}/{name}",
            })
        else:
            logger.warning("Upload failed for image %s", name)

    # Replace image refs in markdown with public URLs (before chunking)
    markdown_with_urls = _replace_markdown_image_refs(markdown_content, filename_to_url)

    # Chunk markdown
    chunker = MarkdownChunker()
    chunks = chunker.chunk_document(
        markdown_content=markdown_with_urls,
        doc_id=doc_id,
        filename=original_filename,
    )

    if not chunks:
        return {"status": "error", "message": "Chunker produced no chunks"}

    provider = _get_embedding_provider()

    # Index to Supabase: markdown + images only (no PDF: pdf_storage_path=None)
    index_gdd_chunks_to_supabase(
        doc_id=doc_id,
        chunks=chunks,
        provider=provider,
        markdown_content=markdown_with_urls,
        pdf_storage_path=None,
        images=images_metadata if images_metadata else None,
    )

    return {
        "status": "success",
        "message": f"Indexed {folder_path.name} as {doc_id} (markdown + {len(images_metadata)} images)",
        "doc_id": doc_id,
    }


def main():
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    parser = argparse.ArgumentParser(
        description="Index one existing markdown folder to Supabase (images + chunk + index; no PDF)."
    )
    parser.add_argument(
        "--folder",
        type=Path,
        required=True,
        help="Path to folder containing one .md file and image files (e.g. rag_storage/new markdown files/[Combat Module] [Tank War] Match Flow Polish)",
    )
    parser.add_argument("--dry-run", action="store_true", help="Only print what would be done")
    args = parser.parse_args()
    result = index_markdown_folder_to_supabase(args.folder, dry_run=args.dry_run)
    print(result.get("message", result))
    if result.get("status") == "error":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
