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
├── markdown/                    # Converted Markdown output (chronological)
│   ├── README.md                # Master index linking all years
│   ├── 2007/
│   │   ├── README.md            # Year-level table of contents
│   │   ├── images/              # Extracted images for this year
│   │   ├── 01_introduction.md
│   │   └── ...
│   └── 2026/
│       └── ...
├── llm-wiki/                    # LLM-Wiki (thematic), see "LLM-Wiki" below
│   ├── AGENTS.md                # Wiki schema & operating rules
│   ├── index.md                 # Wiki catalog (read this first)
│   ├── log.md                   # Append-only activity log
│   └── concepts/                # Cross-cutting concept pages
├── scripts/
│   ├── convert_pdfs.py          # PDF → Markdown conversion (bookmarks or printed TOC)
│   ├── extract_quotes.py        # Extract epigraph quotes → docs/quotes.json
│   └── fix_md_images.py         # One-off image-path fixer
├── docs/                        # Static GitHub-Pages site
│   ├── index.html               # Quote browser (reads quotes.json)
│   ├── quotes.json              # Extracted quotes (author + year + chapter), ~4,800 entries
│   └── README.md
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

# Resume an interrupted run without re-processing finished years
python scripts/convert_pdfs.py --resume
```

The converter splits each report into per-chapter Markdown files using **either**
of two signals, tried in order:

1. **PDF bookmarks** (embedded TOC) — used by 2012, 2013, 2015, 2026.
2. **Printed Table of Contents** — parsed from the TOC page via font-size geometry
   for the 16 reports without bookmarks. A per-PDF page-offset is calibrated from
   one matched title; the offset is constant within a year, which sidesteps the
   running-header false positives that break naive title search.

If neither yields ≥2 chapters (e.g. 2007, a 23-page special report with no TOC),
the report is written as a single `full_report.md`.

## Conventions

- **File naming**: Article filenames are `{nn}_{sanitized_title}.md` (e.g., `01_introduction.md`).
  Names are lowercase with underscores, max 80 characters.
- **Image references**: Images are saved to `markdown/{year}/images/` and referenced
  with relative paths (`images/img-XXXX.png`) in the Markdown files.
- **Chapter splitting**: The script splits on PDF bookmarks when present, otherwise
  falls back to parsing the report's printed Table of Contents (font-size based).
  If neither yields a usable structure, the entire report is saved as a single file.
- **Year folders**: One folder per year under `markdown/`, named by the 4-digit year.
- **README per year**: Each year folder contains a `README.md` that serves as the
  table of contents, linking to all extracted articles.

## Quote Extraction

`scripts/extract_quotes.py` scans `markdown/` and pulls every epigraph quote
into `docs/quotes.json` — a single JSON array of ~4,800 records, each with the
quote text, author, year, chapter title, and source filename. Duplicates across
years are preserved (each occurrence carries its own provenance).

```bash
python scripts/extract_quotes.py
```

The reports cite quotes in **five** layouts across the years; the extractor
matches all of them:

| Layout | Pattern | Years |
|--------|---------|-------|
| A | `_quote_ **Author**` (same line) | 2017–2025 |
| B | `_quote_` then `#### Author` / `**Author**` (next line) | 2017–2025 |
| C | `**_"quote"_ Author**` (author inside bold) | 2012–2016 |
| D | `**_"quote"_** Author` (author after bold) | 2026 |
| E | `<mark>`-wrapped variants of A/B | 2015–2017 |

Caption lines (`_Source: ..._`), footnote blockquotes (`> ...`), report
running-header bleed, and figure-title/body-prose fragments are filtered out by
an author-plausibility heuristic applied to every layout path.

## LLM-Wiki

The `llm-wiki/` folder implements [Andrej Karpathy's LLM-Wiki pattern](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f):
a persistent, compounding knowledge base maintained by an LLM. The reports in
`markdown/` are organized **chronologically**; the wiki reorganizes that same
content **thematically** so a concept like "central bank gold buying" resolves
to one page citing every relevant chapter across all 20 years, instead of
requiring 20 separate file reads.

- **Raw sources**: `markdown/<year>/` — read-only; the agent never edits these.
- **The wiki**: `llm-wiki/` — written and maintained entirely by the agent.
- **The schema**: [`llm-wiki/AGENTS.md`](llm-wiki/AGENTS.md) — the full operating
  rules.

### Wiki file conventions

- **`index.md`** — the catalog. Read FIRST when entering the wiki.
- **`log.md`** — append-only activity log; entries use
  `## [YYYY-MM-DD] ingest|query|lint | <short title>`.
- **`concepts/<topic>.md`** — thematic pages; each must cite ≥2 source chapters
  (links of the form `[Year — Chapter](../markdown/YYYY/NN_title.md)`) before
  being created. Concepts emerge from reading sources, not from guessing upfront.

### The agent loop

- **Ingest**: read a source chapter → update every relevant concept page with a
  new citation → create a new page only when a second source confirms the theme
  → append to `log.md`.
- **Query**: read `index.md` → read relevant concept pages → synthesize an answer
  grounded in citations → offer to file the synthesis back as a new page.
- **Lint**: scan all concept pages for broken links, orphan pages, single-citation
  pages, and contradictions → summarize findings in `log.md`.

Full rules and conventions are in [`llm-wiki/AGENTS.md`](llm-wiki/AGENTS.md).

## Key Dependencies

| Package        | Purpose                              |
|---------------|--------------------------------------|
| `pymupdf4llm` | PDF → Markdown conversion engine     |
| `pymupdf`     | Low-level PDF handling (TOC, pages)  |

## Notes for AI Agents

- PDFs are **not** committed to git. They must be placed in `pdfs/` manually before running the script.
- The `markdown/` folder **is** committed and is the primary output of this project.
- `docs/quotes.json` **is** committed and is a derived artifact: regenerate it with
  `python scripts/extract_quotes.py` whenever `markdown/` changes. It lives under
  `docs/` so the static quote-browser page can fetch it as a same-folder URL on
  GitHub Pages.
- The `llm-wiki/` folder **is** committed and contains the thematic knowledge base
  compiled from `markdown/`. Its `concepts/` pages are written by the agent during
  the ingest loop, not pre-fabricated.
- When modifying the conversion script, always re-run on at least one small PDF (e.g., 2007)
  and one large PDF (e.g., 2026) to verify correctness. Prefer `--resume` during
  iteration so only the year under test is reprocessed.
- The printed-TOC extractor is tuned for this corpus's five TOC layouts; if a new
  report uses a different layout, expect to extend `extract_printed_toc()` in
  `convert_pdfs.py` and re-verify with the dry-run snippet in its docstring.
