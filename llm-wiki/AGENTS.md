# AGENTS.md — LLM-Wiki (In Gold We Trust)

This is an **LLM-Wiki** for the *In Gold We Trust* report corpus, following
[Andrej Karpathy's LLM-Wiki pattern](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f).

> Obsidian is the IDE; the LLM is the programmer; the wiki is the codebase.

## Purpose

Turn the raw, year-by-year report Markdown in `../markdown/` into a **persistent,
compounding knowledge base** of cross-cutting concept pages. The reports are
organized chronologically; the wiki is organized **thematically**. A question
about "central bank gold buying" should resolve to one concept page that cites
every relevant chapter across all 20 years, not 20 separate file reads.

## The three layers

1. **Raw sources** — `../markdown/<year>/`. Read-only. The agent never edits these.
2. **The wiki** — this folder (`llm-wiki/`). Written and maintained entirely by
   the agent. Concepts live in `concepts/`; navigation lives in `index.md` and
   `log.md`.
3. **The schema** — this file (`AGENTS.md`). Defines structure and operating rules.

## File conventions

- **Concept pages** live in `concepts/<topic>.md`, e.g. `concepts/central_bank_gold.md`.
  Filenames are lowercase with underscores.
- Each concept page opens with a one-line definition, then a **Sources** section
  of citations: `- [Year — Chapter](../../markdown/YYYY/NN_title.md)`. (Concept
  pages live in `concepts/`, so reaching `markdown/` at the repo root requires
  two `../`.)
- Every concept page MUST cite at least two source chapters before it is created.
  Single-source "concepts" stay as notes in `log.md` until a second source appears.
- Pages cross-link each other with relative paths: `[inflation](central_bank_gold.md)`.

## Navigation files

- **`index.md`** — the catalog. The agent reads this FIRST to locate relevant
  pages. Two sections: the source corpus (what exists) and the concept index
  (what has been compiled).
- **`log.md`** — append-only chronological record. Every ingest/query/lint action
  adds one entry with the header format:
  `## [YYYY-MM-DD] ingest|query|lint | <short title>`

## The agent loop

### Ingest (adding knowledge from a source)
1. Read the source chapter in `../markdown/YYYY/NN_title.md`.
2. Identify which existing concept pages it informs; update each with a new
   citation and any new nuance. Touch as many pages as warranted — don't be lazy.
3. If the source introduces a concept not yet in the wiki AND a second source
   already touches it, create `concepts/<topic>.md`.
4. Otherwise, log the nascent concept in `log.md` under a "candidates" note.
5. Append an entry to `log.md`.

### Query (answering from the wiki)
1. Read `index.md` to find relevant concept pages.
2. Read those pages; synthesize an answer grounded in their citations.
3. If the answer required real synthesis across sources, offer to file it back
   as a new concept page or update an existing one. Knowledge should compound.

### Lint (health check)
1. Scan all `concepts/*.md` for:
   - Broken citation links (source file moved/deleted).
   - Orphan pages (no incoming links from other concepts).
   - Pages with only one citation (promote or fold back into `log.md` candidates).
   - Contradictions between pages.
2. Append a summary of findings to `log.md`.

## Operating rules

- **Never fabricate citations.** Every `[Year — Chapter]` link must point to a
  real file in `../markdown/`. If unsure, verify the path exists.
- **Read before write.** Always read a concept page before editing it.
- **One concept per page.** If a page grows past ~300 lines, split it.
- **Dates in `log.md` use ISO format** (`YYYY-MM-DD`) so the history is
  unix-greppable.
