#!/usr/bin/env python3
"""
Extract epigraph quotes from the converted *In Gold We Trust* Markdown files.

Scans ``markdown/{year}/*.md`` and pulls out (quote, author) pairs together
with their provenance (year + chapter title + filename). Quotes are the
short italicized / bold-italicized sayings that open sections, attributed
to a person or organisation on the same line or the line immediately below.

The reports use five distinct citation layouts across the years:

  A. ``_quote_ **Author**``                         (same line, 2017-2025)
  B. ``_quote_`` then ``#### **Author**`` / ``**Author**``  (next line)
  C. ``**_"quote"_ Author**``                        (2012-2016, author inside ``**``)
  D. ``**_"quote"_** Author``                        (2026, author after ``**``)
  E. ``<mark>`` wrapping variants of A/B/C           (scattered 2015-2017)

Output: ``docs/quotes.json`` -- a single JSON array of objects::

    {
      "quote": "...",
      "author": "...",
      "year": "2024",
      "chapter": "Mastering the New Gold Playbook",
      "file": "08_mastering_the_new_gold_playbook.md"
    }

Duplicates across years are intentionally preserved (each occurrence carries
its own provenance).

Usage::

    python scripts/extract_quotes.py
"""

import json
import re
import sys
from pathlib import Path


# ---------------------------------------------------------------------------
# Line-level cleaning
# ---------------------------------------------------------------------------

# HTML <mark>...</mark> highlighting artifacts from the PDF conversion.
_MARK_RE = re.compile(r"</?mark>", re.IGNORECASE)
# Other inline HTML tags that survive the PDF->Markdown conversion (<u>, <b>, <i>).
_HTML_TAG_RE = re.compile(r"</?[a-z]+(?:\s[^>]*)?>", re.IGNORECASE)
# Superscripted footnote markers glued to the end of a quote, e.g. `text_<sup>**7**</sup>`.
_SUP_RE = re.compile(r"<sup>.*?</sup>", re.IGNORECASE)
# Trailing footnote-reference style suffixes glued to a word, e.g. `inflation13F`.
_FOOTNOTE_REF_RE = re.compile(r"(?<=[A-Za-z])\d{1,3}[A-Za-z]?$")


def clean_text(s: str) -> str:
    """Strip PDF-conversion noise (HTML tags, footnote markers, stray whitespace)."""
    s = _SUP_RE.sub("", s)
    s = _MARK_RE.sub("", s)
    s = _HTML_TAG_RE.sub("", s)
    s = _FOOTNOTE_REF_RE.sub("", s)
    # Collapse internal whitespace runs.
    s = re.sub(r"\s+", " ", s).strip()
    return s


def clean_quote(s: str) -> str:
    """Normalise a quote span: remove wrapping underscores, tidy whitespace."""
    s = clean_text(s)
    # Drop an outer pair of underscores left over from partial matches.
    if s.startswith("_"):
        s = s[1:]
    if s.endswith("_"):
        s = s[:-1]
    return s.strip().strip('"').strip("„").strip()


def clean_author(s: str) -> str:
    """Normalise an author span: drop markdown emphasis, keep commas/years."""
    s = clean_text(s)
    # Strip leading markdown heading markers (``##### Name`` -> ``Name``).
    # These leak through for H5/H6 headings used as author attributions.
    s = re.sub(r"^\s*#{1,6}\s*", "", s)
    # Strip any leftover emphasis markers.
    s = s.replace("**", "").replace("__", "")
    # A leading comma often separates quote from author in old formats
    # (e.g. ``_"..."``, Alan Greenspan``). Drop it.
    s = s.lstrip(",").strip()
    # Drop a trailing lone comma.
    s = s.rstrip(",").strip()
    return s


# ---------------------------------------------------------------------------
# Classification helpers
# ---------------------------------------------------------------------------

# A standalone italic line that is actually a chart caption or a bibliographic
# note rather than an epigraph. Matched case-insensitively against the start.
_CAPTION_PREFIXES = (
    "source",
    "sources",
    "figure",
    "chart",
    "table",
    "see ",
    "quellen",
)


def is_caption(line: str) -> bool:
    """True if a ``_..._`` line is a chart/bibliography caption, not a quote."""
    low = line.lower()
    # Strip the outer emphasis and any <mark> highlighting before matching.
    low = _MARK_RE.sub("", low).strip().strip("_").strip()
    return low.startswith(_CAPTION_PREFIXES)


def looks_like_author(line: str) -> str | None:
    """Return a cleaned author string if ``line`` plausibly attributes a quote.

    Accepts H4/H3/H2 headings (``#### Author``), bold-only lines
    (``**Author**``), and short plain-text lines (``Author``). Returns ``None``
    for body prose, footers, dividers, or overlong strings.
    """
    s = line.strip()
    if not s:
        return None

    # Footers / page furniture -- never an author.
    if any(tok in s for tok in ("LinkedIn", "twitter", "IGWTreport", "#igwt", "#IGWT")):
        return None
    # Footnote-block dividers / stray punctuation.
    if s in ("—", "---", "—", "*", "**") or set(s) <= {"-", "—", " "}:
        return None
    # Chapter/page-number-only lines (e.g. bare ``12``).
    if re.fullmatch(r"\d{1,4}", s):
        return None

    # Markdown heading used as an attribution (``#### Author`` through
    # ``###### Author``). H5/H6 appear in several reports.
    m = re.match(r"^#{2,6}\s+(.+?)\s*$", s)
    if m:
        body = clean_author(m.group(1))
        if _author_plausible(body):
            return body
        return None

    # Bold-only line: ``**Author**`` (possibly with trailing detail).
    m = re.match(r"^\*\*(.+?)\*\*\s*$", s)
    if m:
        body = clean_author(m.group(1))
        if _author_plausible(body):
            return body
        return None

    # Plain text: must be short and name-like, not a sentence.
    body = clean_author(s)
    if _author_plausible(body):
        return body
    return None


# Tokens that signal a "next line" is body prose rather than an attribution.
_PROSE_HINTS = (
    "the ", "and ", "but ", "we ", "in ", "of ", "as ", "this ", "that ",
    "is ", "are ", "was ", "were ", "has ", "have ", "for ", "with ",
)


def _author_plausible(body: str) -> bool:
    """Heuristic: does this string look like an author/source rather than prose?

    Rejects chart/figure titles, report running headers, and body sentences
    that happen to follow a standalone italic line.
    """
    if not body or len(body) < 2:
        return False
    # Overly long -> almost certainly a sentence or figure caption, not a name.
    if len(body) > 90:
        return False
    # Multiple sentences -> body prose.
    if body.count(".") >= 2:
        return False
    # Chart / figure titles typically use a colon ("Gold demand in 2010: +10%...")
    # or describe content ("Money is usually credited with...").
    if ":" in body and not re.search(r"\d{4}", body):
        # allow "Surname, Firstname" style? Those use commas, not colons, so a
        # colon almost always signals a title/caption.
        if len(body) > 20:
            return False
    # Report running-header bleed ("Erste Group Research – Gold Report 2012").
    if re.search(r"gold\s+report\s+20\d{2}", body, re.IGNORECASE):
        return False
    if re.search(r"in\s+gold\s+we\s+trust\s+(report\s+)?20\d{2}", body, re.IGNORECASE):
        return False
    # Long body that starts with a common prose word -> likely a sentence.
    if len(body) > 45 and body.lower().startswith(_PROSE_HINTS):
        return False
    # Hashtag tokens (``#igwt19``, ``#A One-Two Punch``) -- social tags or
    # in-document anchors, never author attributions.
    if body.startswith("#"):
        return False
    # A full sentence ending in a period with several words.
    words = body.split()
    if body.endswith(".") and len(words) > 10:
        return False
    # Starts lowercase -> almost never a name (proper nouns are capitalised).
    if body[0].islower():
        return False
    # Leading underscore / quote cruft -> fragment of a larger span, not a name.
    if body.startswith("_") or body.startswith("”") or body.startswith("'"):
        return False
    # Wrapped italic span (``_Some heading_``) -> a subsection title, not a name.
    if body.startswith("_") and body.endswith("_") and len(body) > 10:
        return False
    # Sentence-like section headings: capitalised but many words with no comma
    # (real attributions are short -- "Jim Grant", "Jim Grant, 2020"). A long
    # un-commaed run with lowercase function words mid-phrase is prose.
    if len(words) >= 8 and "," not in body and len(body) > 45:
        if any(re.search(r"\b" + re.escape(w.rstrip(",")) + r"\b", body.lower())
               for w in ("the", "and", "of", "to", "in", "is", "are", "was",
                         "that", "this", "has", "have", "while", "since",
                         "where", "from", "not", "but")):
            return False
    # Figure-title / sentence-fragment openers (capitalised but descriptive).
    if re.match(r"^(The\s|There\s|Many\s|Money\s|Stock-to-flow|Many countries|Writes\s|writes\s)", body):
        return False
    return True


# ---------------------------------------------------------------------------
# Per-file extraction
# ---------------------------------------------------------------------------

# Format C (2012-2016): ``**_"quote"_ Author**`` -- author inside the closing ``**``.
_FMT_C = re.compile(r'^\*\*_["„]?(.+?)["_„]?_\s*,?\s*([^*]+?)\*\*\s*$')
# Format D (2026): ``**_"quote"_** Author`` (optional ``- `` list prefix).
_FMT_D = re.compile(r'^(?:-\s+)?\*\*_["„]?(.+?)["_„]?_\*\*\s+(.+?)\s*$')
# Format A (2017-2025): ``_quote_ **Author**``.
_FMT_A = re.compile(r'^_(.+?)_\s+\*\*(.+?)\*\*\s*$')


def _resolve_chapter_title(readme_path: Path, filename: str) -> str:
    """Look up the human-readable chapter title for ``filename`` in the year README."""
    try:
        text = readme_path.read_text(encoding="utf-8")
    except OSError:
        return filename
    # README entries look like: ``N. [Title](filename.md)``
    pattern = re.escape(filename) + r"\)"
    for line in text.splitlines():
        m = re.match(r"^\s*\d+\.\s+\[(.+?)\]\(" + pattern, line)
        if m:
            return m.group(1).strip()
    return filename


def extract_from_file(md_path: Path, year: str, chapter_title: str) -> list[dict]:
    """Return all (quote, author) records found in a single Markdown file."""
    try:
        raw_lines = md_path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return []

    # Drop footnote block lines up front: anything beginning with ``>`` is a
    # bibliographic blockquote and never contains a usable epigraph.
    lines = [ln for ln in raw_lines if not ln.lstrip().startswith(">")]

    records: list[dict] = []
    base = {
        "year": year,
        "chapter": chapter_title,
        "file": md_path.name,
    }

    i = 0
    n = len(lines)
    while i < n:
        line = lines[i].rstrip()
        stripped = line.strip()

        # ---- Format C (2012-2016) ---------------------------------------
        m = _FMT_C.match(stripped)
        if m:
            quote = clean_quote(m.group(1))
            author = clean_author(m.group(2))
            if quote and _author_plausible(author):
                records.append({**base, "quote": quote, "author": author})
            i += 1
            continue

        # ---- Format D (2026) --------------------------------------------
        m = _FMT_D.match(stripped)
        if m:
            quote = clean_quote(m.group(1))
            author = clean_author(m.group(2))
            if quote and _author_plausible(author):
                records.append({**base, "quote": quote, "author": author})
            i += 1
            continue

        # ---- Format A (2017-2025): same-line author --------------------
        m = _FMT_A.match(stripped)
        if m:
            quote = clean_quote(m.group(1))
            author = clean_author(m.group(2))
            if quote and _author_plausible(author) and not is_caption(stripped):
                records.append({**base, "quote": quote, "author": author})
            i += 1
            continue

        # ---- Format B: standalone ``_..._`` quote, author on a later line
        if stripped.startswith("_") and stripped.count("_") >= 2:
            # Collect one or more consecutive italic quote paragraphs separated
            # by blank lines (multi-paragraph quotes split the author off the
            # last paragraph). Stop as soon as a non-italic attribution line
            # is found.
            quote_parts: list[str] = []
            cur = stripped
            if is_caption(cur) or not _is_pure_italic_line(cur):
                i += 1
                continue
            quote_parts.append(clean_quote(_strip_italics(cur)))
            j = i + 1
            # Skip a single blank line, then look for either another italic
            # paragraph (continuation) or the attribution.
            while j < n:
                nxt = lines[j].strip()
                if not nxt:
                    j += 1
                    continue
                if _is_pure_italic_line(nxt) and not is_caption(nxt):
                    quote_parts.append(clean_quote(_strip_italics(nxt)))
                    j += 1
                    # require a blank line before the next part
                    if j < n and lines[j].strip():
                        break
                    continue
                break

            author_line = lines[j].strip() if j < n else ""
            author = looks_like_author(author_line)
            if quote_parts and author:
                quote = " ".join(p for p in quote_parts if p)
                if len(quote) >= 3:
                    records.append({**base, "quote": quote, "author": author})
                i = j + 1
                continue

        i += 1

    return records


def _is_pure_italic_line(line: str) -> bool:
    """True if ``line`` is a standalone italic span like ``_some quote_``."""
    s = line.strip()
    if not s.startswith("_"):
        return False
    # Must contain a closing underscore, and the text between must be non-empty.
    inner = s.strip("_")
    return bool(inner) and "_" in s[1:]


def _strip_italics(line: str) -> str:
    """Remove the outer ``_..._`` emphasis from a standalone italic line."""
    s = line.strip()
    if s.startswith("_"):
        s = s[1:]
    if s.endswith("_"):
        s = s[:-1]
    return s.strip()


# ---------------------------------------------------------------------------
# Corpus-wide driver
# ---------------------------------------------------------------------------

def extract_all(markdown_dir: Path) -> list[dict]:
    """Walk every year folder under ``markdown_dir`` and collect all quotes."""
    out: list[dict] = []
    for year_dir in sorted(p for p in markdown_dir.iterdir() if p.is_dir()):
        if not year_dir.name.isdigit():
            continue
        year = year_dir.name
        readme = year_dir / "README.md"
        md_files = sorted(
            p for p in year_dir.glob("*.md")
            if p.name != "README.md"
        )
        for md_path in md_files:
            chapter = _resolve_chapter_title(readme, md_path.name)
            out.extend(extract_from_file(md_path, year, chapter))
    return out


def main() -> None:
    if "--resume" in sys.argv:
        # accepted for consistency with convert_pdfs.py, but a no-op here:
        # quote extraction is fast enough to always run end-to-end.
        pass

    script_dir = Path(__file__).resolve().parent
    project_root = script_dir.parent
    markdown_dir = project_root / "markdown"

    if not markdown_dir.is_dir():
        print(f"Error: markdown directory not found: {markdown_dir}")
        sys.exit(1)

    print(f"Scanning {markdown_dir} ...")
    records = extract_all(markdown_dir)

    # Sort for stable output: by year, then file, then quote.
    records.sort(key=lambda r: (r["year"], r["file"], r["quote"]))

    out_path = project_root / "docs" / "quotes.json"
    out_path.write_text(
        json.dumps(records, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    years = sorted({r["year"] for r in records})
    print(f"\nExtracted {len(records)} quote records across {len(years)} years.")
    print("Per-year counts:")
    for y in years:
        c = sum(1 for r in records if r["year"] == y)
        print(f"  {y}: {c}")
    print(f"\nWrote {out_path}")


if __name__ == "__main__":
    main()
