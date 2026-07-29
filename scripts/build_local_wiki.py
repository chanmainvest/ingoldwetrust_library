"""
Two-pass local LLM-Wiki builder.

Goal: build a Karpathy-style thematic wiki from the In Gold We Trust corpus
using a LOCAL model (e.g. google/gemma-4-E4B-it), so we can measure how good
each local model is at the task. No calls to a hosted LLM, no peeking at the
human-curated ../llm-wiki reference.

Pass 1 (extract, GPU):  per chapter -> grounded JSON concept candidates.
Pass 2 (cluster+write): deterministic Python clustering; a page is created
                        ONLY when >=2 distinct chapters cite the concept
                        (matches the wiki schema in ../llm-wiki/AGENTS.md).
                        The model is used in pass 2 only for "same concept?"
                        tie-breaks between ambiguous title pairs.

Intermediate state is written to <model>/extraction.jsonl so a partial run
can be resumed without re-running inference.

Usage:
    python scripts/build_local_wiki.py --model-id google/gemma-4-E4B-it \\
        --output-dir local-llm-wiki/gemma-4-e4b --chapters subset [--resume]
"""
import os
import sys
import json
import re
import time
import datetime
import argparse
from pathlib import Path
from collections import defaultdict

# UTF-8 on the Windows terminal
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# Enterprise proxy / SSL helper (no-op if absent)
try:
    import pip_system_certs.wrapt_requests  # noqa: F401
except Exception:
    pass

# torch/transformers are only needed for the LOCAL (GPU) path. Importing them
# lazily (inside load_model) keeps the pass-2 / clustering utilities importable
# by API-only builders (build_api_wiki.py) on machines without torch installed.
torch = None  # type: ignore


# ----------------------------------------------------------------------------
# Corpus selection
# ----------------------------------------------------------------------------

# A representative subset of the corpus: each year's introduction plus one
# key thematic chapter (supply/demand, monetary policy & inflation,
# central-bank gold / de-dollarization, or technical analysis). Target ~40
# chapters total so a full subset run finishes in a few hours per model.
SUBSET_PATTERNS = [
    r"full_report\.md$",                                   # 2007 special report
    r"01_introduction\.md$",
    r".*(supply_and_demand|monetary_policy|central_bank|de_dollarization|technical_analysis|inflation).*\.md$",
]


def list_chapters(mode: str):
    """Return a chronologically ordered list of chapter Paths under markdown/."""
    md = Path("markdown")
    out = []
    for year in sorted(md.iterdir()):
        if not (year.is_dir() and year.name.isdigit()):
            continue
        for f in sorted(year.glob("*.md")):
            if f.name.lower() == "readme.md":
                continue
            out.append(f)
    if mode == "all":
        return out
    if mode == "subset":
        pats = [re.compile(p, re.IGNORECASE) for p in SUBSET_PATTERNS]
        kept = [f for f in out if any(p.search(str(f)) for p in pats)]
        # Always guarantee the yearly introduction even if naming drifts
        seen_years = {f.parent.name for f in kept}
        for f in out:
            if f.parent.name not in seen_years and "intro" in f.name.lower():
                kept.append(f)
                seen_years.add(f.parent.name)
        # Dedup preserving order
        seen = set()
        dedup = []
        for f in kept:
            if f not in seen:
                seen.add(f)
                dedup.append(f)
        return dedup
    if mode == "smoke":
        # 2 short chapters for verification only
        return [Path("markdown/2007/full_report.md"),
                Path("markdown/2010/11_gold_is_money_nothing_else.md")]
    raise ValueError(f"unknown chapters mode: {mode}")


# ----------------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------------

SLUG_STOP = {
    "the", "of", "a", "an", "and", "or", "in", "on", "to", "for", "with",
    "as", "is", "are", "at", "by", "from", "into", "its", "their",
}


def slugify(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_-]+", "_", text)
    return text.strip("_")[:80]


def normalize_title_for_cluster(title: str) -> str:
    """Aggressive normalization so 'Central Bank Gold Accumulation' and
    'Central-Bank Gold Accumulation Shift' land in the same cluster key."""
    t = title.lower()
    t = re.sub(r"[^a-z0-9 ]", " ", t)
    words = [w for w in t.split() if w and w not in SLUG_STOP]
    # crude singularization
    words = [w[:-1] if w.endswith("s") and len(w) > 3 else w for w in words]
    words.sort()  # order-independent
    return " ".join(words)


def chapter_meta(chap_path: Path):
    year = chap_path.parent.name
    title = chap_path.stem.replace("_", " ").strip().title()
    rel = f"../../markdown/{year}/{chap_path.name}"
    return year, title, rel


def parse_json_obj(text: str):
    """Best-effort JSON object extraction from a model response.
    Handles the common failure where greedy decoding hits max_new_tokens
    mid-array: we salvage every complete `{...}` object inside `concepts`
    even if the outer array/object is never closed."""
    # fenced block
    m = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(1))
        except Exception:
            pass
    # bare braces (well-formed)
    a, b = text.find("{"), text.rfind("}")
    if a != -1 and b > a:
        try:
            return json.loads(text[a:b + 1])
        except Exception:
            pass
    # SALVAGE: truncated `{"concepts": [ {...}, {...}, (cut)` -> recover the
    # complete inner objects even if the array/object is never closed.
    # We look for the concepts array, then walk it capturing each balanced
    # {...} member independently of the outer wrapper object.
    if '"concepts"' in text:
        salvaged = []
        # find the array start (first '[' after 'concepts')
        arr = text.find('"concepts"')
        arr = text.find("[", arr) if arr != -1 else -1
        if arr != -1:
            depth = 0
            start = None
            in_str = False
            esc = False
            for i in range(arr, len(text)):
                ch = text[i]
                if esc:
                    esc = False
                    continue
                if ch == "\\":
                    esc = True
                    continue
                if ch == '"':
                    in_str = not in_str
                    continue
                if in_str:
                    continue
                if ch == "{":
                    if depth == 0:
                        start = i
                    depth += 1
                elif ch == "}":
                    depth -= 1
                    if depth == 0 and start is not None:
                        frag = text[start:i + 1]
                        try:
                            obj = json.loads(frag)
                            if "title" in obj:
                                salvaged.append(obj)
                        except Exception:
                            pass
                        start = None
        if salvaged:
            return {"concepts": salvaged}
    return None


def chunk_text(text: str, limit: int = 16000):
    """Split on paragraph boundaries into <=limit-char chunks.
    16k chars (~4k tok) keeps most chapters in 1-2 generations, which is the
    main throughput lever on an 8GB GPU."""
    paras = text.split("\n\n")
    out, cur = [], ""
    for p in paras:
        if len(cur) + len(p) + 2 <= limit:
            cur = (cur + "\n\n" + p) if cur else p
        else:
            if cur:
                out.append(cur)
            cur = p if len(p) <= limit else p[:limit]
    if cur:
        out.append(cur)
    return out or [text[:limit]]


# ----------------------------------------------------------------------------
# Pass 1: extraction (GPU)
# ----------------------------------------------------------------------------

EXTRACT_SYSTEM = (
    "You are a meticulous financial-knowledge extractor building a thematic "
    "wiki from the 'In Gold We Trust' investment reports. You read source "
    "text and extract ONLY concepts that are explicitly discussed in that "
    "text. You never speculate about figures, charts, or images. Every "
    "concept you output MUST be backed by verbatim quotes copied from the "
    "supplied text."
)

EXTRACT_USER_TMPL = """Read the source text below and extract the distinct financial, monetary, macroeconomic, or market-structure CONCEPTS that the text actually discusses.

STRICT RULES:
- Extract only concepts the text explicitly addresses. Do NOT invent.
- NEVER describe or speculate about images, figures, charts, or layout. If you cannot find textual evidence, output nothing for that idea.
- For every concept, provide 2-4 `evidence_quotes`: SHORT verbatim phrases (<= 20 words each) copied character-for-character from the text. These are checked against the source; fabricated quotes make the whole output invalid.
- 3-8 concepts is typical. If the text has no relevant concept, return `{{"concepts": []}}`.
- Keep `title` to <= 6 words, noun-phrase style (e.g. "Central Bank Gold Accumulation").
- `summary` is 1 sentence (<= 30 words) in your own words.

Respond with ONLY a JSON object, no prose, in this exact shape:
```json
{{
  "concepts": [
    {{
      "title": "Concept Name",
      "summary": "One-sentence description grounded in the text.",
      "evidence_quotes": ["verbatim phrase from the text", "another verbatim phrase"]
    }}
  ]
}}
```

SOURCE TITLE: {title}
SOURCE YEAR: {year}

SOURCE TEXT:
\"\"\"
{text}
\"\"\"
"""

# Few-shot example embedded once to anchor behavior; kept compact.
FEWSHOT = """
EXAMPLE (do not reuse these concepts, they are illustrative only):

SOURCE TEXT (excerpt):
"...central banks have become net buyers of gold for the first time in decades.
The shift from seller to buyer marks a regime change in reserve management..."

CORRECT:
```json
{"concepts": [{"title": "Central Bank Gold Accumulation", "summary": "Central banks have shifted from net sellers to net buyers of gold, reshaping reserve management.", "evidence_quotes": ["central banks have become net buyers of gold", "shift from seller to buyer marks a regime change in reserve management"]}]}
```

WRONG (do not do this):
- "The report uses charts to show reserve trends."  <- describes an image; forbidden.
- evidence_quotes that paraphrase or are not present verbatim in the source.
"""


def load_model(model_id: str, quantize: bool = True):
    """Load model+tokenizer. With quantize=True (default) we load in 4-bit
    via bitsandbytes so a 16GB model fits in 8GB VRAM. Without it, the model
    is CPU-offloaded and generation is ~10x slower on this GPU."""
    global torch
    import torch as _torch
    torch = _torch
    from transformers import AutoTokenizer, AutoModelForCausalLM
    globals()["AutoTokenizer"] = AutoTokenizer
    globals()["AutoModelForCausalLM"] = AutoModelForCausalLM
    print(f"[load] {model_id}  (quantize={quantize})", flush=True)
    tok = AutoTokenizer.from_pretrained(model_id, trust_remote_code=True)
    kw = {"trust_remote_code": True}
    if torch.cuda.is_available():
        try:
            import accelerate  # noqa: F401  (needed for device_map)
            kw["device_map"] = "cuda"
        except ImportError:
            pass
        if quantize:
            try:
                from transformers import BitsAndBytesConfig
                kw["quantization_config"] = BitsAndBytesConfig(
                    load_in_4bit=True,
                    bnb_4bit_compute_dtype=torch.bfloat16,
                    bnb_4bit_quant_type="nf4",
                    bnb_4bit_use_double_quant=True,
                )
                print("[load] 4-bit NF4 quantization enabled", flush=True)
            except Exception as e:
                print(f"[load] 4-bit unavailable ({e}); "
                      f"falling back to bf16 + offload", flush=True)
                kw["dtype"] = torch.bfloat16
        else:
            kw["dtype"] = torch.bfloat16
    model = AutoModelForCausalLM.from_pretrained(model_id, **kw)
    if "device_map" not in kw and torch.cuda.is_available():
        model = model.to("cuda")
    model.eval()
    if torch.cuda.is_available():
        alloc = torch.cuda.memory_allocated() / 1e9
        print(f"[load] done; VRAM allocated={alloc:.2f} GB", flush=True)
    else:
        print("[load] done (CPU)", flush=True)
    return tok, model


def generate(tok, model, user_msg: str, system_msg: str, max_new_tokens: int):
    # torch.no_grad applied at call time so the module can be imported without torch
    with torch.no_grad():
        messages = [{"role": "system", "content": system_msg},
                    {"role": "user", "content": user_msg}]
        prompt = tok.apply_chat_template(messages, tokenize=False,
                                         add_generation_prompt=True)
        inputs = tok(prompt, return_tensors="pt").to(model.device)
        n_in = inputs.input_ids.shape[1]
        out = model.generate(
            **inputs,
            max_new_tokens=max_new_tokens,
            do_sample=False,  # greedy: reproducible + less hallucinated prose
            temperature=1.0,
            pad_token_id=tok.eos_token_id,
        )
        text = tok.decode(out[0][n_in:], skip_special_tokens=True)
        return text, n_in, out.shape[1] - n_in


def extract_chapter(tok, model, year, title, full_text, max_chunks=6):
    """Run extraction across chunks of a chapter; merge concept lists.
    Caps at `max_chunks` chunks so one pathological chapter (e.g. a 500KB
    merged report) cannot dominate a whole run; later chunks of oversized
    chapters carry diminishing new concepts anyway."""
    chunks = chunk_text(full_text, limit=16000)
    if len(chunks) > max_chunks:
        print(f"  [cap] chapter has {len(chunks)} chunks; limiting to first "
              f"{max_chunks}", flush=True)
        chunks = chunks[:max_chunks]
    all_concepts = []
    for ci, ch in enumerate(chunks):
        prompt = EXTRACT_USER_TMPL.format(year=year, title=title, text=ch)
        if ci == 0:
            prompt = FEWSHOT + "\n" + prompt
        try:
            resp, n_in, n_out = generate(tok, model, prompt, EXTRACT_SYSTEM,
                                         max_new_tokens=1500)
        except Exception as e:
            print(f"  [chunk {ci}] generation error: {e}", flush=True)
            continue
        parsed = parse_json_obj(resp)
        if not parsed or "concepts" not in parsed:
            print(f"  [chunk {ci}] no JSON; raw[:120]={resp[:120]!r}",
                  flush=True)
            continue
        for c in parsed.get("concepts", []):
            # validate required shape
            t = (c.get("title") or "").strip()
            qs = c.get("evidence_quotes") or []
            if not t or not isinstance(qs, list) or len(qs) < 1:
                continue
            all_concepts.append({
                "title": t[:80],
                "summary": (c.get("summary") or "").strip(),
                "evidence_quotes": [str(q).strip() for q in qs if str(q).strip()],
                "_chunk": ci,
            })
        print(f"  [chunk {ci+1}/{len(chunks)}] +{len(parsed.get('concepts', []))} "
              f"({n_in}/{n_out} tok)", flush=True)
    # de-dup within chapter by normalized title (keep richest evidence)
    by_key = {}
    for c in all_concepts:
        k = normalize_title_for_cluster(c["title"])
        if k not in by_key or len(c["evidence_quotes"]) > len(by_key[k]["evidence_quotes"]):
            by_key[k] = c
    return list(by_key.values())


def run_pass1(model_id, out_dir, chapters, resume, quantize=True):
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    (out / "concepts").mkdir(exist_ok=True)
    jsonl = out / "extraction.jsonl"

    done_keys = set()
    if resume and jsonl.exists():
        for line in jsonl.read_text(encoding="utf-8").splitlines():
            try:
                r = json.loads(line)
                done_keys.add(r["rel"])
            except Exception:
                pass
        print(f"[resume] {len(done_keys)} chapters already in extraction.jsonl",
              flush=True)

    tok, model = load_model(model_id, quantize=quantize)
    t0 = time.time()
    total_in, total_out = 0, 0

    with open(jsonl, "a", encoding="utf-8") as fjson:
        for i, chap in enumerate(chapters, 1):
            year, title, rel = chapter_meta(chap)
            if rel in done_keys:
                print(f"[{i}/{len(chapters)}] skip (resume) {year} {title}",
                      flush=True)
                continue
            print(f"[{i}/{len(chapters)}] extract: {year} {title}", flush=True)
            try:
                text = chap.read_text(encoding="utf-8", errors="replace")
            except Exception as e:
                print(f"  read error: {e}", flush=True)
                continue
            concepts = extract_chapter(tok, model, year, title, text)
            rec = {"rel": rel, "year": year, "title": title,
                   "concepts": concepts,
                   "ts": datetime.datetime.now().isoformat(timespec="seconds")}
            fjson.write(json.dumps(rec, ensure_ascii=False) + "\n")
            fjson.flush()
            print(f"  -> {len(concepts)} concept(s); elapsed "
                  f"{time.time()-t0:.0f}s", flush=True)

    del model
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
    print(f"[pass1] done in {time.time()-t0:.0f}s", flush=True)
    return jsonl


# ----------------------------------------------------------------------------
# Pass 2: cluster + write (deterministic; optional GPU tie-breaks)
# ----------------------------------------------------------------------------

def load_extractions(jsonl_path: Path):
    rows = []
    for line in jsonl_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            rows.append(json.loads(line))
        except Exception:
            pass
    return rows


def cluster_concepts(rows):
    """Group concept candidates across chapters by normalized title key.
    Returns {cluster_key: {title, citations:[{year,title,rel,summary,quotes}]}}."""
    clusters = defaultdict(lambda: {"title": None, "citations": []})
    for r in rows:
        for c in r["concepts"]:
            k = normalize_title_for_cluster(c["title"])
            if not k:
                continue
            if clusters[k]["title"] is None or len(c["title"]) < len(clusters[k]["title"]):
                clusters[k]["title"] = c["title"]
            clusters[k]["citations"].append({
                "year": r["year"],
                "chapter": r["title"],
                "rel": r["rel"],
                "summary": c["summary"],
                "quotes": c["evidence_quotes"],
            })
    return clusters


def render_concept_md(cluster):
    title = cluster["title"]
    cits = cluster["citations"]
    # one-line definition = first non-empty summary
    definition = next((c["summary"] for c in cits if c["summary"]), title + ".")
    lines = [f"# {title}", "", definition, "", "## Analysis", ""]
    # group evidence by citing chapter
    for c in cits:
        lines.append(f"### {c['year']} — {c['chapter']}")
        if c["summary"]:
            lines.append(c["summary"])
        if c["quotes"]:
            lines.append("Evidence from source:")
            for q in c["quotes"][:4]:
                lines.append(f"> {q}")
        lines.append("")
    lines.append("## Sources")
    # stable, deduped citation list
    seen = set()
    for c in cits:
        if c["rel"] in seen:
            continue
        seen.add(c["rel"])
        lines.append(f"- [{c['year']} — {c['chapter']}]({c['rel']})")
    lines.append("")
    return "\n".join(lines)


def build_index(model_id, out_dir, clusters_promoted, n_candidates,
                chapter_count):
    lines = [
        f"# Local LLM-Wiki Index — {model_id}",
        "",
        "Auto-generated thematic wiki built by a local model from the "
        "*In Gold We Trust* corpus. Pages are created only when >=2 distinct "
        "source chapters discuss the concept.",
        "",
        "## Source Corpus",
        "",
        f"- Builder model: `{model_id}`",
        f"- Source chapters processed: {chapter_count}",
        f"- Concept pages (>=2 citations): {len(clusters_promoted)}",
        f"- Single-citation candidates (in log.md): {n_candidates}",
        "",
        "## Concept Index",
        "",
    ]
    for slug, cluster in sorted(clusters_promoted.items()):
        n = len({c["rel"] for c in cluster["citations"]})
        lines.append(f"- [{cluster['title']}](concepts/{slug}.md) — {n} sources")
    lines.append("")
    return "\n".join(lines)


def run_pass2(model_id, out_dir, jsonl_path):
    out = Path(out_dir)
    concepts_dir = out / "concepts"
    concepts_dir.mkdir(parents=True, exist_ok=True)
    rows = load_extractions(jsonl_path)
    clusters = cluster_concepts(rows)
    today = datetime.date.today().isoformat()

    promoted = {}     # slug -> cluster
    candidates = []   # single-citation clusters
    for k, cl in clusters.items():
        distinct = {c["rel"] for c in cl["citations"]}
        if len(distinct) >= 2:
            slug = slugify(cl["title"])
            # if two clusters slug-collide, disambiguate
            base, n = slug, 2
            while slug in promoted and promoted[slug] is not cl:
                slug = f"{base}_{n}"
                n += 1
            promoted[slug] = cl
        else:
            candidates.append(cl)

    # write concept pages (wipe stale ones from prior runs first)
    for old in concepts_dir.glob("*.md"):
        old.unlink()
    for slug, cl in promoted.items():
        (concepts_dir / f"{slug}.md").write_text(
            render_concept_md(cl), encoding="utf-8")

    # index + log
    chapter_count = len({r["rel"] for r in rows})
    (out / "index.md").write_text(
        build_index(model_id, out_dir, promoted, len(candidates),
                    chapter_count),
        encoding="utf-8")

    log = out / "log.md"
    header = "" if log.exists() else f"# Local LLM-Wiki Activity Log\n\n"
    entry = (f"## [{today}] build | {model_id}\n"
             f"Processed {chapter_count} chapters -> "
             f"{len(promoted)} concept pages (>=2 citations), "
             f"{len(candidates)} single-citation candidates.\n\n")
    if candidates:
        entry += "### Single-citation candidates (need a 2nd source to promote):\n"
        for cl in sorted(candidates, key=lambda x: x["title"])[:60]:
            c = cl["citations"][0]
            entry += f"- {cl['title']} — only {c['year']} {c['chapter']}\n"
        if len(candidates) > 60:
            entry += f"- ... ({len(candidates)-60} more)\n"
        entry += "\n"
    with open(log, "a", encoding="utf-8") as f:
        f.write(header + entry)

    return {
        "chapters": chapter_count,
        "concepts": len(promoted),
        "candidates": len(candidates),
        "promoted": promoted,  # slug -> cluster, for pass-3 synthesis
    }


# ----------------------------------------------------------------------------
# Pass 3: synthesis (LLM-rewrites each aggregated page as a narrative)
# ----------------------------------------------------------------------------

SYNTH_SYSTEM = (
    "You are a knowledge-base editor writing a thematic wiki page for the "
    "'In Gold We Trust' investment-report corpus. You receive a concept with "
    "its per-chapter notes and verbatim evidence, and you write ONE coherent, "
    "synthesized page in Markdown. You NEVER fabricate quotes or citations: "
    "every claim must trace to the supplied evidence, and you preserve every "
    "source link exactly as given."
)

SYNTH_USER_TMPL = """Synthesize the following extracted notes into a single cohesive wiki page for the concept "{title}".

The notes come from {n} distinct chapters of the In Gold We Trust reports (years {years}). Write a page that SYNTHESIZES them into a narrative, NOT a list. Structure it exactly as:

1. A `# {title}` heading.
2. One opening paragraph (2-4 sentences) defining the concept and stating its significance — this is the page's thesis.
3. A `## How the argument evolved` section that walks chronologically through the years, weaving the per-chapter notes into a flowing story of how the report's treatment of this concept developed. Use **{{year}}** bold run-ins (e.g. **2017**). Embed short verbatim phrases inline as "quotes" where they add color, but do not invent new quotes.
4. A `## See also` section listing 0-5 of the sibling concept titles below that are genuinely related (omit the section if none fit): {siblings}
5. A `## Sources` section listing EXACTLY these links, one per line, unchanged:
{source_links}

HARD RULES:
- Output Markdown only, no preamble.
- Do not invent facts, numbers, or quotes not present in the notes.
- Keep every source link verbatim. Do not add or remove sources.
- Aim for 300-600 words of prose (excluding the sources list).

EXTRACTED NOTES (per chapter):
{notes}
"""


def build_synth_prompt(cluster, sibling_titles):
    """Build the synthesis user-prompt for one concept cluster."""
    cits = sorted(cluster["citations"], key=lambda c: (c["year"], c["chapter"]))
    years = sorted({c["year"] for c in cits})
    notes_blocks = []
    source_links = []
    seen = set()
    for c in cits:
        quotes = " | ".join(f'"{q}"' for q in c["quotes"][:3]) if c["quotes"] else ""
        notes_blocks.append(
            f"- **{c['year']} — {c['chapter']}**: {c['summary']}  {quotes}".strip()
        )
        if c["rel"] not in seen:
            seen.add(c["rel"])
            source_links.append(f"  - [{c['year']} — {c['chapter']}]({c['rel']})")
    siblings = ", ".join(sibling_titles) if sibling_titles else "(none available)"
    return SYNTH_USER_TMPL.format(
        title=cluster["title"],
        n=len({c["rel"] for c in cits}),
        years=", ".join(years),
        notes="\n".join(notes_blocks),
        siblings=siblings,
        source_links="\n".join(source_links),
    )


def run_pass3_synthesize(out_dir, promoted, call_fn, batch_label=""):
    """Rewrite each promoted concept page as a synthesized narrative.

    `call_fn(system, user) -> str` is the model call (local or API). Pages that
    fail to synthesize are left as their pass-2 aggregated form.
    """
    out = Path(out_dir)
    concepts_dir = out / "concepts"
    all_titles = [cl["title"] for cl in promoted.values()]
    n = len(promoted)
    ok = 0
    for i, (slug, cluster) in enumerate(sorted(promoted.items()), 1):
        # sibling titles = other concepts, capped, excluding self
        siblings = [t for t in all_titles if t != cluster["title"]][:12]
        prompt = build_synth_prompt(cluster, siblings)
        try:
            md = call_fn(SYNTH_SYSTEM, prompt)
        except Exception as e:
            print(f"  [synth {i}/{n}] {cluster['title']}: FAILED ({e})",
                  flush=True)
            continue
        # basic sanity: must contain the title heading and at least the sources
        if f"# {cluster['title']}" not in md or "## Sources" not in md:
            print(f"  [synth {i}/{n}] {cluster['title']}: malformed, skipped",
                  flush=True)
            continue
        (concepts_dir / f"{slug}.md").write_text(md.strip() + "\n",
                                                 encoding="utf-8")
        ok += 1
        if i % 10 == 0 or i == n:
            print(f"  [synth {i}/{n}] synthesized {ok} pages", flush=True)
    print(f"[pass3] synthesized {ok}/{n} concept pages ({batch_label})",
          flush=True)
    return ok


# ----------------------------------------------------------------------------
# CLI
# ----------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--model-id", required=True)
    ap.add_argument("--output-dir", required=True)
    ap.add_argument("--chapters", choices=["all", "subset", "smoke"],
                    default="subset")
    ap.add_argument("--resume", action="store_true",
                    help="Skip chapters already in extraction.jsonl (pass 1).")
    ap.add_argument("--pass-only", choices=["1", "2", "3"],
                    help="Run only one pass (debugging). 3 = synthesize from "
                         "existing extraction.jsonl without re-extracting.")
    ap.add_argument("--no-quantize", action="store_true",
                    help="Disable 4-bit quantization (use bf16 + CPU offload).")
    ap.add_argument("--synthesize", action="store_true",
                    help="After pass-2, run pass-3: rewrite each concept page "
                         "as a synthesized narrative via the model.")
    args = ap.parse_args()

    chapters = list_chapters(args.chapters)
    print(f"[plan] model={args.model_id}  out={args.output_dir}  "
          f"chapters={args.chapters} ({len(chapters)} files)", flush=True)

    out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)
    jsonl = out / "extraction.jsonl"

    want_pass1 = args.pass_only != "2" and args.pass_only != "3"
    want_pass2 = args.pass_only != "1" and args.pass_only != "3"
    want_pass3 = args.synthesize or args.pass_only == "3"

    if want_pass1:
        run_pass1(args.model_id, args.output_dir, chapters, args.resume,
                  quantize=not args.no_quantize)
    if want_pass2:
        if not jsonl.exists():
            print("[pass2] no extraction.jsonl; skipping", flush=True)
            want_pass3 = False
        else:
            stats = run_pass2(args.model_id, args.output_dir, jsonl)
            print(f"[pass2] {stats}", flush=True)

    if want_pass3:
        if not jsonl.exists():
            print("[pass3] no extraction.jsonl; skipping synthesis", flush=True)
        else:
            # pass-3 needs the promoted clusters; recompute from jsonl (cheap)
            rows = load_extractions(jsonl)
            clusters = cluster_concepts(rows)
            promoted = {}
            for k, cl in clusters.items():
                if len({c["rel"] for c in cl["citations"]}) >= 2:
                    slug = slugify(cl["title"])
                    base, n = slug, 2
                    while slug in promoted:
                        slug = f"{base}_{n}"; n += 1
                    promoted[slug] = cl
            if not promoted:
                print("[pass3] no promoted concepts to synthesize", flush=True)
            else:
                tok, model = load_model(args.model_id,
                                        quantize=not args.no_quantize)

                def call_fn(system, user):
                    text, _, _ = generate(tok, model, user, system,
                                          max_new_tokens=1500)
                    return text
                run_pass3_synthesize(args.output_dir, promoted, call_fn,
                                     batch_label=args.model_id)


if __name__ == "__main__":
    main()
