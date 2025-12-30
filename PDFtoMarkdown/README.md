# PDF to Markdown with Docling

This folder provides a CLI to convert PDFs to Markdown. By default it writes outputs to the local `markdown/` folder.

## Setup
- Python 3.9+.
- Install Docling: `pip install docling`.
- For OCR languages beyond English, ensure Tesseract and language packs are installed on your system.

## Usage
Convert a single PDF:
```
python pdf_to_markdown.py --input docs/example.pdf
```

Convert all PDFs under `docs/` (recursive) to `markdown/`:
```
python pdf_to_markdown.py --input docs
```

Enable OCR with specific languages (comma-separated):
```
python pdf_to_markdown.py --input docs --ocr-langs en,fr
```

Override output directory:
```
python pdf_to_markdown.py --input docs --output /path/to/outdir
```

Overwrite existing Markdown outputs:
```
python pdf_to_markdown.py --input docs --overwrite
```

Outputs are saved as `<pdf_stem>.md` in the chosen output directory (defaults to `markdown/`).

