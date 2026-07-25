#!/usr/bin/env python3
"""
Fix the two mis-extracted chapters in markdown/2019/.

Root cause: the printed-TOC parser's fuzzy heading-match landed two chapters on
the wrong pages, so files 05 and 07 contain the wrong content:
  - 05 (should be FOFOA interview)       -> actually contains "Exter's Pyramid"
  - 07 (should be Gold Storage)          -> actually contains "Plaza Accord 2.0?"

Both displaced chapters are real report sections that were not listed in the
printed Table of Contents, so the parser had no entry for them and squeezed
their content into the neighbouring files' page ranges.

This script re-extracts the correct page ranges from the source PDF:
  - 05_highlights_..._fofoa.md      <- FOFOA interview   (pdf pages 121-129)
  - 07_gold_storage_..._singapore.md<- Gold Storage       (pdf pages 166-175)
and writes the two displaced chapters to correctly-named new files:
  - 06a_exters_pyramid.md           <- "Exter's Pyramid"  (pdf pages 130-142)
  - 06b_plaza_accord_2.md           <- "Plaza Accord 2.0?"(pdf pages 176-192)

All page boundaries were verified against the source PDF body text.

Usage:  python scripts/fix_2019_chapters.py
"""
import re
import sys
from pathlib import Path

import pymupdf
import pymupdf4llm

# Reuse the image-path fixer from the main converter.
SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))
from convert_pdfs import fix_image_paths  # noqa: E402

PROJECT_ROOT = SCRIPT_DIR.parent
PDF_PATH = PROJECT_ROOT / "pdfs" / "In-Gold-We-Trust-2019-Extended-Version-english.pdf"
YEAR_DIR = PROJECT_ROOT / "markdown" / "2019"
IMAGES_DIR = YEAR_DIR / "images"
YEAR = "2019"

# (output_filename, pdf_start_page_0indexed, pdf_end_page_exclusive, heading_for_log)
JOBS = [
    # Re-extract the two mis-assigned files with their CORRECT content.
    ("05_highlights_20_years_later_a_freegold_project_interview_with_fofoa.md", 121, 130,
     "Highlights: 20 Years Later – a Freegold Project: Interview with FOFOA"),
    ("07_gold_storage_fact_checking_liechtenstein_switzerland_and_singapore.md", 166, 176,
     "Gold Storage: Fact Checking Liechtenstein, Switzerland, and Singapore"),
    # The two displaced chapters become new, correctly-named files.
    ("06a_the_enduring_relevance_of_exters_pyramid.md", 130, 143,
     "The Enduring Relevance of Exter's Pyramid"),
    ("06b_history_does_not_repeat_itself_plaza_accord_2.md", 176, 193,
     "History Does (not) Repeat Itself – Plaza Accord 2.0?"),
]


def main() -> None:
    if not PDF_PATH.is_file():
        sys.exit(f"Source PDF not found: {PDF_PATH}")

    # Sanity-check page boundaries before writing anything.
    doc = pymupdf.open(str(PDF_PATH))
    try:
        expected_starts = {
            121: "freegold",        # FOFOA interview page
            166: "gold storage",    # storage chapter page
            130: "exter",           # Exter's pyramid page
            176: "plaza",           # Plaza accord page
        }
        for idx, needle in expected_starts.items():
            head = "\n".join(doc[idx].get_text().splitlines()[:12]).lower()
            if needle not in head:
                sys.exit(f"Boundary check FAILED: page idx {idx} head does not "
                         f"contain '{needle}'. Aborting before any writes.\n"
                         f"Head was: {head[:160]!r}")
        print("Boundary checks passed.")
    finally:
        doc.close()

    for fname, start, end, heading in JOBS:
        page_numbers = list(range(start, end))
        out_path = YEAR_DIR / fname
        print(f"\n-> {fname}")
        print(f"   pages[{start}:{end}] ({len(page_numbers)} pp)  '{heading}'")

        md_text = pymupdf4llm.to_markdown(
            str(PDF_PATH),
            pages=page_numbers,
            write_images=True,
            image_path=str(IMAGES_DIR),
        )
        md_text = fix_image_paths(md_text, str(IMAGES_DIR), YEAR)
        out_path.write_text(md_text, encoding="utf-8")
        # Show the first heading we actually got, for verification.
        first_line = next((l.strip() for l in md_text.splitlines() if l.strip()), "")
        print(f"   wrote {out_path.name}  | first line: {first_line[:70]}")

    print("\nDone. Review the output, then regenerate the 2019 README if desired.")


if __name__ == "__main__":
    main()
