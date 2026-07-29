#!/usr/bin/env python3
"""
Convert "In Gold We Trust" PDF reports into structured Markdown files.

For each PDF in pdfs/:
  1. Extract the year from the filename.
  2. Read the PDF's Table of Contents (bookmarks) to identify chapter boundaries.
  3. Convert each chapter to Markdown with embedded images.
  4. Write output to markdown/{year}/ with a README table of contents.

Usage:
    python scripts/convert_pdfs.py
"""

import os
import re
import sys
import time
from pathlib import Path

import pymupdf          # PyMuPDF (fitz)
import pymupdf4llm

# Years whose PDFs must use pymupdf4llm's legacy "rag" path instead of the
# default "layout" path. Layout mode (the current default) silently ignores the
# ``image_size_limit`` kwarg, so PDFs whose pages are tiled-mosaic covers or
# photo collages (2007's cover is 286 raster tiles of ~16x15px each) dump every
# tile as a separate image and bury the text. The legacy path honors the limit
# and drops sub-5% images. Add a year here only when its layout-mode output is
# confirmed to be image-spammed.
LEGACY_MODE_YEARS: set[str] = {"2007"}

# Reconfigure stdout/stderr to use UTF-8 on Windows to avoid UnicodeEncodeErrors
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass
if sys.stderr.encoding != 'utf-8':
    try:
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def is_valid_chapter_title(title: str) -> bool:
    """Filter out internal bookmarks and junk TOC titles."""
    title = title.strip()
    if not title:
        return False
    if title.startswith('_'):
        return False
    if "OLE_LINK" in title:
        return False
    # Check for long hash-like strings (no spaces, length >= 15, alphanumeric/hex)
    if len(title) >= 15 and " " not in title:
        if re.match(r'^[Xx]?[0-9a-fA-F]+$', title):
            return False
    return True


def extract_year(filename: str) -> str | None:
    """Extract a 4-digit year (2000-2099) from a filename."""
    match = re.search(r"(20\d{2})", filename)
    return match.group(1) if match else None


def sanitize_filename(title: str, max_length: int = 80) -> str:
    """Turn a chapter title into a safe, lowercase, underscore-delimited filename stem.

    Also strips leading numbering prefixes (``1.``, ``2.``, ``a.)``) and trailing
    footnote-reference markers (e.g. ``...consequences13F`` -> ``...consequences``)
    that leak into titles extracted from the printed Table of Contents.
    """
    s = title.strip()
    # Strip leading chapter/section numbering: "1. ", "10. ", "a.) ", "a) "
    s = re.sub(r"^(?:\d{1,3}[.)]|[a-z][.)]+)\s+", "", s)
    # Strip a trailing inline-glued page number (1-3 digits, page-like) leaked
    # from the printed TOC. A 4-digit trailing number is treated as a year and
    # preserved (e.g. "...the bull market in 1980").
    s = re.sub(r"\s+\d{1,3}$", "", s)
    # Strip a trailing footnote-ref style suffix: letters/digits glued to a word end
    # e.g. "consequences13F" -> "consequences", "diversification128f" -> "diversification"
    s = re.sub(r"(?<=[A-Za-z])\d{1,3}[A-Za-z]?$", "", s)
    s = re.sub(r"[^\w\s-]", "", s)
    s = re.sub(r"[\s-]+", "_", s.strip())
    s = s.lower()
    return s[:max_length] if s else "untitled"


def fix_image_paths(md_text: str, abs_images_dir: str, year: str) -> str:
    """Replace absolute and generated relative image-directory paths with a relative ``images/`` prefix.

    pymupdf4llm emits image paths rooted at the ``image_path`` we pass in. When
    that path is absolute (as it is when the converter is invoked from
    ``main()``), the emitted reference looks like
    ``.../ingoldwetrust_library/markdown/2026/images/foo.png``; when relative,
    it looks like ``markdown/2026/images/foo.png``. Both must collapse to
    ``images/foo.png``.

    The absolute prefix is replaced first (most specific, longest match); the
    bare ``markdown/{year}/images/`` substitution that follows is anchored to
    the path-start (the ``(`` opening the Markdown image reference) so it only
    rewrites genuinely-relative paths and never a substring of an absolute one.
    """
    # Normalise to forward-slash for comparison
    abs_fwd = abs_images_dir.replace("\\", "/")
    # Also handle the raw Windows backslash form
    abs_bwd = abs_images_dir.replace("/", "\\")

    md_text = md_text.replace(abs_fwd + "/", "images/")
    md_text = md_text.replace(abs_bwd + "\\", "images/")
    md_text = md_text.replace(abs_fwd, "images")
    md_text = md_text.replace(abs_bwd, "images")

    # Bare relative paths: "markdown/2026/images/..." -> "images/...".
    # Anchor to the Markdown-image opening "(" so the substitution only matches
    # a path *start* and never a substring of a still-absolute path.
    md_text = re.sub(r"\(markdown/" + year + r"/images/", "(images/", md_text)
    # Match a backslash-delimited relative path; each literal "\" is "\\" in a regex.
    md_text = re.sub(r"\(markdown\\" + year + r"\\images\\", r"(images\\", md_text)
    return md_text


# ---------------------------------------------------------------------------
# Printed Table-of-Contents extraction (for PDFs without PDF bookmarks)
# ---------------------------------------------------------------------------

# Lines on a TOC page that are pure boilerplate, not chapter titles.
_TOC_NOISE_PATTERNS = [
    r"^incrementum\s+ag$",
    r"^\d{1,2}\s+\w+\s+\d{4}$",          # "24 June 2014"
    r"^\d{1,2}\.\s+\w+\s+\d{4}$",        # "28. June 2016"
    r"“in\s+gold\s+we\s+trust”",
    r"in\s+gold\s+we\s+trust\s+20",
    r"^“?in\s*gold",
    r"linkedin", r"twitter", r"#igwt", r"@igwt", r"igwtreport",
    r"über\s+uns",
    r"extended\s+version", r"special\s+report",
    r"erste\s+group", r"cee\s+equity",
    r"company\s+descriptions", r"sound\s+money",
    r"^x\s*\|",
    r"^table\s+of\s+contents$", r"^contents$", r"^disclaimer",
    r"key\s+takeaways",
    r"^page\s+\d", r"^page$",
]


def _is_toc_noise(text: str) -> bool:
    """True if a TOC-page line is boilerplate rather than a chapter title."""
    t = text.strip().lower()
    if not t or not re.search(r"[a-z]", t):
        return True
    return any(re.search(p, t) for p in _TOC_NOISE_PATTERNS)


def _looks_like_title(text: str) -> bool:
    """A TOC title is short and not a full sentence or descriptive blurb."""
    t = re.sub(r"[_.·\s\d]+$", "", text).strip()
    if not t:
        return False
    words = t.split()
    if len(words) > 14:
        return False
    if t.endswith(".") and len(words) > 6:
        return False
    if t.count(",") >= 3:
        return False
    return True


def _is_subentry_marker(text: str) -> bool:
    """True if a title starts with a lettered sub-entry marker (``a.``, ``a.)``, ``a)``)."""
    t = text.strip()
    return bool(re.match(r"^[a-z][.)]\s+", t))


def _line_representative_size(spans) -> float:
    """Representative font size of a line: the size of its longest non-whitespace span.

    PDFs sometimes append a differently-sized whitespace span (e.g. a trailing
    11pt space on an 8pt TOC line); using ``max(span sizes)`` would misclassify
    such lines. The longest *text* span is the reliable signal.
    """
    best = None
    best_len = -1
    for sp in spans:
        n = len(sp["text"].strip())
        if n > best_len:
            best_len = n
            best = sp["size"]
    if best is None:
        best = max(sp["size"] for sp in spans)
    return round(float(best), 1)


def find_toc_pages(doc, max_scan: int = 12) -> list[int]:
    """Return 0-indexed page numbers that look like a Table-of-Contents page."""
    hits = []
    for i in range(min(max_scan, len(doc))):
        t = doc[i].get_text()
        low = t.lower()
        if ("table of contents" in low
                or "table of content" in low
                or (re.search(r"\bcontents\b", low) and ("....." in t or "____" in t))
                or ("contents" in low and low.count("\n") > 8)):
            hits.append(i)
    return hits


def extract_printed_toc(doc, toc_pages: list[int]) -> list[tuple[str, int]]:
    """Extract top-level ``(title, printed_page)`` entries from the printed TOC.

    Works across the heterogeneous TOC formats used by the reports across years
    (leader-dot, underscore-leader, two-line separated, mixed, inline-glued) by
    using the geometry of the page: the dominant title font size identifies
    top-level entries, and each entry's page number sits either on the same row
    or on the next non-empty line below.
    """
    if not toc_pages:
        return []

    lines: list[dict] = []
    for pidx in toc_pages:
        if pidx >= len(doc):
            continue
        d = doc[pidx].get_text("dict")
        for blk in d["blocks"]:
            if blk.get("type", 0) != 0:
                continue
            for ln in blk["lines"]:
                spans = ln.get("spans", [])
                if not spans:
                    continue
                text = "".join(sp["text"] for sp in spans).strip()
                if not text:
                    continue
                lines.append({
                    "y": round(ln["bbox"][1], 1),
                    "x0": round(ln["bbox"][0], 1),
                    "x1": round(ln["bbox"][2], 1),
                    "size": _line_representative_size(spans),
                    "text": text,
                    "page": pidx,
                })

    titled = [l for l in lines if not _is_toc_noise(l["text"])]
    if not titled:
        return []

    title_like = [l for l in titled if _looks_like_title(l["text"])]
    pool = title_like if title_like else titled
    size_counts: dict[float, int] = {}
    for l in pool:
        size_counts[l["size"]] = size_counts.get(l["size"], 0) + 1

    nums = [l for l in lines if re.fullmatch(r"\d{1,4}", l["text"])]

    def pair_one(t: dict) -> tuple[str, int] | None:
        """Pair a title line with its page number, or None if unresolvable."""
        m = re.search(r"[_.·]{3,}.*?(\d{1,4})\s*$", t["text"])
        if m:
            title = re.sub(r"[_.·\s]{3,}.*$", "", t["text"]).strip()
            return (title, int(m.group(1)))
        same = [n for n in nums if n["page"] == t["page"] and abs(n["y"] - t["y"]) <= 6.0]
        if same:
            return (t["text"], int(max(same, key=lambda n: n["x1"])["text"]))
        below = [n for n in nums if n["page"] == t["page"] and 0 < n["y"] - t["y"] <= 30]
        if below:
            return (t["text"], int(min(below, key=lambda n: n["y"] - t["y"])["text"]))
        m2 = re.search(r"\s+(\d{1,3})\s*$", t["text"])
        if m2:
            prefix = t["text"][: m2.start()].strip()
            if 4 <= len(prefix) <= 70 and _looks_like_title(prefix):
                return (prefix, int(m2.group(1)))
        return None

    def entries_for_size(size: float) -> list[tuple[str, int]]:
        out = []
        for l in titled:
            if abs(l["size"] - size) > 0.6:
                continue
            if not _looks_like_title(l["text"]) or _is_subentry_marker(l["text"]):
                continue
            pair = pair_one(l)
            if pair and len(pair[0]) >= 3:
                out.append(pair)
        return out

    # Choose the title size whose paired entries form the cleanest chapter list:
    # strictly increasing page numbers with few duplicates. This robustly
    # distinguishes the top-level tier from a sub-entry tier (whose page numbers
    # repeat/decrease because multiple sub-entries share a chapter's pages).
    distinct_sizes = sorted(size_counts.keys(), reverse=True)
    substantial = [s for s in distinct_sizes if size_counts[s] >= 3] or distinct_sizes

    best_size: float | None = None
    best_entries: list[tuple[str, int]] = []
    best_score: tuple = ()
    for s in substantial:
        cand = entries_for_size(s)
        if len(cand) < 2:
            continue
        pages = [p for _, p in cand]
        unique_pages = len(set(pages))
        uniq_ratio = unique_pages / len(pages)
        # Score: (uniqueness_ratio, completeness_bucket, font_size).
        #  - uniqueness: a clean chapter list has strictly increasing pages;
        #    sub-entry tiers repeat pages (ratio < 1).
        #  - completeness: prefer a full chapter list over a sparse subset
        #    (e.g. 2025 highlights only 4 of ~14 chapters at a larger size).
        #    Bucketed so a handful of extra entries doesn't outweigh uniqueness.
        #  - font_size: when two tiers are otherwise tied, the larger size is
        #    the top-level tier (typeset convention).
        completeness_bucket = 0 if len(cand) < 5 else (1 if len(cand) < 9 else 2)
        score = (round(uniq_ratio, 3), completeness_bucket, s)
        if score > best_score:
            best_score = score
            best_size = s
            best_entries = cand

    if best_size is None:
        return []

    # Deduplicate (title, page) preserving order.
    seen: set[tuple[str, int]] = set()
    out: list[tuple[str, int]] = []
    for t, p in best_entries:
        key = (t, p)
        if key in seen:
            continue
        seen.add(key)
        out.append((t, p))
    return out


def _norm_text(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip().lower()


def _title_key(title: str, max_words: int = 6) -> str:
    """First few whitespace-normalized words of a title, for fuzzy heading matching."""
    return " ".join(_norm_text(title).split()[:max_words])


def find_chapter_start(doc, title: str, center_idx: int, min_idx: int,
                       window: int = 3) -> int | None:
    """Find the PDF page index near ``center_idx`` where ``title`` appears as a heading.

    The search is restricted to ``[center_idx-window, center_idx+window]`` and to
    pages ``>= min_idx`` (so TOC/front-matter pages are never matched), which
    eliminates the running-header false positives that plague unconstrained
    title search (each chapter title is repeated as a running header on every
    page of that chapter).
    """
    key = _title_key(title)
    if len(key) < 5:
        return None
    start = max(min_idx, center_idx - window)
    end = min(len(doc), center_idx + window + 1)
    best: int | None = None
    for i in range(start, end):
        txt = doc[i].get_text()
        matched = False
        for ln in txt.splitlines():
            lns = _norm_text(ln)
            if 3 <= len(lns) <= 120 and key in lns:
                matched = True
                break
        if matched:
            if best is None or abs(i - center_idx) < abs(best - center_idx):
                best = i
    return best


def calibrate_offset(doc, entries: list[tuple[str, int]],
                     min_idx: int) -> int | None:
    """Determine the constant per-PDF offset mapping printed page -> PDF index.

    Uses the first entry whose title can be located in the body to compute
    ``offset = real_index - printed_page``. The offset is constant within a
    report, so a single successful calibration unlocks every entry. Returns
    ``None`` if no entry could be located (caller should fall back to whole-PDF
    conversion).
    """
    for title, printed_page in entries:
        real = find_chapter_start(doc, title, printed_page, min_idx, window=4)
        if real is not None:
            return real - printed_page
    return None


# ---------------------------------------------------------------------------
# Core conversion
# ---------------------------------------------------------------------------

def convert_pdf(pdf_path: str, output_base: str, skip_if_done: bool = False) -> str | None:
    """
    Convert a single PDF into per-chapter Markdown files.

    Returns the extracted year string, or ``None`` on failure. When
    ``skip_if_done`` is true, a year that already has generated Markdown output
    (a README plus at least one article) is left untouched, so an interrupted
    batch run can be safely resumed.
    """
    filename = os.path.basename(pdf_path)
    year = extract_year(filename)
    if not year:
        print(f"  [!] Skipping {filename}: could not determine year")
        return None

    year_dir = os.path.join(output_base, year)
    if skip_if_done:
        readme = os.path.join(year_dir, "README.md")
        articles = [f for f in os.listdir(year_dir)
                    if f.endswith(".md") and f != "README.md"] if os.path.isdir(year_dir) else []
        if os.path.isfile(readme) and articles:
            print(f"  [skip] {filename}: markdown/{year}/ already has {len(articles)} article(s)")
            return year

    print(f"\n{'=' * 60}")
    print(f"  Processing: {filename}  (year {year})")
    print(f"{'=' * 60}")

    # Select the pymupdf4llm extraction path. Layout mode (the default) does not
    # honor ``image_size_limit``, so years in LEGACY_MODE_YEARS fall back to the
    # legacy rag path that does. See LEGACY_MODE_YEARS docstring for details.
    use_legacy = year in LEGACY_MODE_YEARS
    pymupdf4llm.use_layout(not use_legacy)
    print(f"  Mode  : {'legacy (rag)' if use_legacy else 'layout'}")

    images_dir = os.path.join(year_dir, "images")
    os.makedirs(images_dir, exist_ok=True)

    # ------------------------------------------------------------------
    # Read PDF metadata
    # ------------------------------------------------------------------
    doc = pymupdf.open(pdf_path)
    toc = doc.get_toc()          # list of [level, title, page_number]
    total_pages = len(doc)
    doc.close()

    print(f"  Pages : {total_pages}")
    print(f"  TOC   : {len(toc)} entries")

    # Keep only valid top-level (level-1) entries
    top_level = [(title.strip(), page) for level, title, page in toc if level == 1 and is_valid_chapter_title(title)]

    # Sort top-level entries by page number
    top_level.sort(key=lambda x: x[1])

    # Deduplicate entries pointing to the same page
    seen_pages = set()
    unique_top_level = []
    for title, page in top_level:
        if page not in seen_pages:
            seen_pages.add(page)
            unique_top_level.append((title, page))
    top_level = unique_top_level

    print(f"  Chapters (L1 bookmarks): {len(top_level)}")

    # ------------------------------------------------------------------
    # Convert
    # ------------------------------------------------------------------
    if len(top_level) >= 2:
        # PDF has a usable bookmark structure -> split by bookmark
        articles = _convert_by_chapter(
            pdf_path, year_dir, images_dir, top_level, total_pages, year
        )
    else:
        # No bookmarks: try to split using the *printed* Table of Contents.
        articles = _convert_from_printed_toc(
            pdf_path, year_dir, images_dir, total_pages, year
        )
        if articles is None:
            # Printed-TOC parsing failed (or no TOC) -> single file
            articles = _convert_whole(pdf_path, year_dir, images_dir, year)

    # ------------------------------------------------------------------
    # Write year-level README (table of contents)
    # ------------------------------------------------------------------
    readme_path = os.path.join(year_dir, "README.md")
    with open(readme_path, "w", encoding="utf-8") as fh:
        fh.write(f"# In Gold We Trust Report {year}\n\n")
        fh.write("## Table of Contents\n\n")
        for idx, (title, fname) in enumerate(articles, 1):
            fh.write(f"{idx}. [{title}]({fname})\n")

    print(f"  [OK] {len(articles)} article(s) + README -> markdown/{year}/")
    return year


def _convert_whole(pdf_path: str, year_dir: str, images_dir: str, year: str):
    """Convert the entire PDF as one Markdown file."""
    print("  -> No chapter structure; converting as single file...")
    md_text = pymupdf4llm.to_markdown(
        pdf_path,
        write_images=True,
        image_path=images_dir,
        image_size_limit=0.05,
    )
    md_text = fix_image_paths(md_text, images_dir, year)

    out_file = os.path.join(year_dir, "full_report.md")
    with open(out_file, "w", encoding="utf-8") as fh:
        fh.write(md_text)

    return [("Full Report", "full_report.md")]


def _convert_from_printed_toc(
    pdf_path: str,
    year_dir: str,
    images_dir: str,
    total_pages: int,
    year: str,
):
    """Split a bookmark-less PDF using its printed Table of Contents.

    Returns the list of ``(title, filename)`` articles on success, or ``None``
    if no usable printed TOC could be extracted (caller falls back to a single
    whole-PDF file).
    """
    doc = pymupdf.open(pdf_path)
    try:
        toc_pages = find_toc_pages(doc)
        if not toc_pages:
            print("  -> No printed Table of Contents found")
            return None

        entries = extract_printed_toc(doc, toc_pages)
        print(f"  Printed TOC: {len(entries)} entries (on pages {[p+1 for p in toc_pages]})")
        if len(entries) < 2:
            print("  -> Too few printed-TOC entries to split")
            return None

        # Body content starts after the last TOC page; chapter searches must
        # never match TOC/front-matter pages.
        min_idx = max(toc_pages) + 1

        offset = calibrate_offset(doc, entries, min_idx)
        if offset is None:
            print("  -> Could not calibrate printed-page offset; falling back")
            return None
        print(f"  Calibrated offset (pdf_idx - printed_page): {offset}")

        # Resolve each entry to a real PDF page index. Entries that can't be
        # located inherit ``printed_page + offset`` (the constant offset is the
        # reliable signal, so this is safe). Drop any that fall outside the doc.
        resolved: list[tuple[str, int]] = []  # (title, 0-indexed pdf page)
        for title, printed_page in entries:
            real = find_chapter_start(doc, title, printed_page + offset, min_idx, window=2)
            if real is None:
                real = printed_page + offset
            if 0 <= real < total_pages:
                resolved.append((title, real))

        if len(resolved) < 2:
            print("  -> Too few resolvable chapters after calibration")
            return None
    finally:
        doc.close()

    # Deduplicate chapters that resolved to the same start page (e.g. a
    # wrapped-title artifact that landed on the previous chapter's page), then
    # re-sort by page index. ``_convert_by_chapter`` expects 1-indexed pages.
    seen: set[int] = set()
    unique: list[tuple[str, int]] = []
    for title, idx in sorted(resolved, key=lambda x: x[1]):
        if idx in seen:
            continue
        seen.add(idx)
        unique.append((title, idx))

    print(f"  Chapters (printed TOC): {len(unique)}")
    top_level_1indexed = [(title, idx + 1) for title, idx in unique]
    return _convert_by_chapter(
        pdf_path, year_dir, images_dir, top_level_1indexed, total_pages, year
    )


def _convert_by_chapter(
    pdf_path: str,
    year_dir: str,
    images_dir: str,
    top_level: list[tuple[str, int]],
    total_pages: int,
    year: str,
):
    """Split the PDF by top-level TOC entries and convert each chapter."""
    # Build (title, start_page, end_page) triples  (1-indexed pages)
    chapters: list[tuple[str, int, int]] = []
    for i, (title, start_page) in enumerate(top_level):
        end_page = (
            top_level[i + 1][1] - 1 if i + 1 < len(top_level) else total_pages
        )
        chapters.append((title, start_page, end_page))

    articles: list[tuple[str, str]] = []
    seen_names: dict[str, int] = {}

    for i, (title, start_page, end_page) in enumerate(chapters, 1):
        # pymupdf4llm pages are 0-indexed
        page_numbers = list(range(start_page - 1, end_page))
        if not page_numbers:
            continue

        print(f"  Ch {i:>2}: pp {start_page}-{end_page}  '{title}'")
        t0 = time.time()

        md_text = pymupdf4llm.to_markdown(
            pdf_path,
            pages=page_numbers,
            write_images=True,
            image_path=images_dir,
            image_size_limit=0.05,
        )
        md_text = fix_image_paths(md_text, images_dir, year)

        elapsed = time.time() - t0
        print(f"         ({elapsed:.1f}s)")

        # Unique filename
        base = f"{i:02d}_{sanitize_filename(title)}"
        if base in seen_names:
            seen_names[base] += 1
            base = f"{base}_{seen_names[base]}"
        else:
            seen_names[base] = 0

        article_filename = f"{base}.md"
        out_file = os.path.join(year_dir, article_filename)
        with open(out_file, "w", encoding="utf-8") as fh:
            fh.write(md_text)

        articles.append((title, article_filename))

    return articles


# ---------------------------------------------------------------------------
# Root-level README
# ---------------------------------------------------------------------------

def write_root_readme(output_dir: str, years: list[str]) -> None:
    """Write the master ``markdown/README.md`` linking to all year folders."""
    root_readme = os.path.join(output_dir, "README.md")
    with open(root_readme, "w", encoding="utf-8") as fh:
        fh.write("# In Gold We Trust Report Library\n\n")
        fh.write(
            "Markdown conversions of the annual "
            "*In Gold We Trust* reports by Incrementum AG.\n\n"
        )
        fh.write("## Reports by Year\n\n")
        for year in sorted(years):
            fh.write(f"- [{year}]({year}/README.md)\n")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    script_dir = Path(__file__).resolve().parent
    project_root = script_dir.parent

    pdfs_dir = project_root / "pdfs"
    output_dir = project_root / "markdown"
    output_dir.mkdir(exist_ok=True)

    if not pdfs_dir.is_dir():
        print(f"Error: PDF directory not found: {pdfs_dir}")
        sys.exit(1)

    # ``--resume`` skips years that already have generated Markdown output, so
    # an interrupted batch run can be safely continued without re-processing
    # finished years.
    resume = "--resume" in sys.argv

    pdf_files = sorted(
        f for f in os.listdir(pdfs_dir) if f.lower().endswith(".pdf")
    )
    print(f"Found {len(pdf_files)} PDF(s) in {pdfs_dir}"
          + (" (resume mode: skipping completed years)" if resume else "") + "\n")

    processed_years: list[str] = []
    for pdf_file in pdf_files:
        pdf_path = str(pdfs_dir / pdf_file)
        year = convert_pdf(pdf_path, str(output_dir), skip_if_done=resume)
        if year:
            processed_years.append(year)

    # Master index
    unique_years = sorted(set(processed_years))
    write_root_readme(str(output_dir), unique_years)

    print(f"\n{'=' * 60}")
    print(f"  All done!  {len(pdf_files)} PDFs -> {len(unique_years)} year folders")
    print(f"  Output: {output_dir}")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
