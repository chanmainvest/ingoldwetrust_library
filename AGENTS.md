# AGENTS.md — In Gold We Trust Library

## Project Purpose

This repository converts the annual **In Gold We Trust** reports (PDF) published by
Incrementum AG into structured Markdown files suitable for AI/LLM consumption,
research, and full-text search.

## Repository Layout

```
ingoldwetrust_library/
├── pdfs/                        # Source PDFs (git-ignored, ~225 MB total)
│   ├── in-gold-we-trust-2007-extended-version-e.pdf
│   └── ...
├── markdown/                    # Converted Markdown output
│   ├── README.md                # Master index linking all years
│   ├── 2007/
│   │   ├── README.md            # Year-level table of contents
│   │   ├── images/              # Extracted images for this year
│   │   ├── 01_introduction.md
│   │   └── ...
│   └── 2026/
│       └── ...
├── scripts/
│   └── convert_pdfs.py          # Main conversion script
├── requirements.txt             # Python dependencies
├── AGENTS.md                    # This file
├── README.md                    # Project overview
└── .gitignore
```

## Running the Conversion

```bash
# Install dependencies
pip install -r requirements.txt

# Run the converter (processes all PDFs in pdfs/)
python scripts/convert_pdfs.py
```

## Conventions

- **File naming**: Article filenames are `{nn}_{sanitized_title}.md` (e.g., `01_introduction.md`).
  Names are lowercase with underscores, max 80 characters.
- **Image references**: Images are saved to `markdown/{year}/images/` and referenced
  with relative paths (`images/img-XXXX.png`) in the Markdown files.
- **Chapter splitting**: The script uses PDF bookmarks/Table of Contents (TOC) to identify
  chapter boundaries. If no TOC is found, the entire report is saved as a single file.
- **Year folders**: One folder per year under `markdown/`, named by the 4-digit year.
- **README per year**: Each year folder contains a `README.md` that serves as the
  table of contents, linking to all extracted articles.

## Key Dependencies

| Package        | Purpose                              |
|---------------|--------------------------------------|
| `pymupdf4llm` | PDF → Markdown conversion engine     |
| `pymupdf`     | Low-level PDF handling (TOC, pages)  |

## Notes for AI Agents

- PDFs are **not** committed to git. They must be placed in `pdfs/` manually before running the script.
- The `markdown/` folder **is** committed and is the primary output of this project.
- When modifying the conversion script, always re-run on at least one small PDF (e.g., 2007)
  and one large PDF (e.g., 2026) to verify correctness.
