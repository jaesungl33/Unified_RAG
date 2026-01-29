"""
Shared utilities for running Marker (PDF → Markdown + images).

Used by index_pdf_with_marker and convert_pdf_to_markdown.
"""

import logging
import shutil
import subprocess
from pathlib import Path
from typing import Optional, Tuple

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
logger = logging.getLogger(__name__)


def run_marker(pdf_path: Path, output_dir: Path, debug: bool = False) -> Tuple[bool, str]:
    """
    Run Marker CLI: marker_single <pdf_path> --output_format markdown --output_dir <output_dir>.
    Image extraction is enabled by default (do not pass --disable_image_extraction).
    On success, output is output_dir/<stem>/<stem>.md and output_dir/<stem>/images/.
    If debug=True, passes --debug to Marker (saves per-page layout images and extra JSON).
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
        if debug:
            cmd.append("--debug")
        logger.info("Running: %s", " ".join(cmd))
        r = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=900,
            cwd=str(PROJECT_ROOT),
        )
        if r.stdout and r.stdout.strip():
            logger.info("[Marker stdout] %s", r.stdout.strip()[:2000])
        if r.stderr and r.stderr.strip():
            logger.info("[Marker stderr] %s", r.stderr.strip()[:2000])
        if r.returncode != 0:
            return False, (r.stderr or r.stdout or f"exit code {r.returncode}")
        return True, ""
    except subprocess.TimeoutExpired:
        return False, "Marker timed out (900s)"
    except Exception as e:
        return False, str(e)


def find_marker_output_dir(output_dir: Path, pdf_stem: str) -> Optional[Path]:
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
    stem_dir = output_dir / pdf_stem
    if stem_dir.exists() and stem_dir.is_dir():
        return stem_dir
    return None
