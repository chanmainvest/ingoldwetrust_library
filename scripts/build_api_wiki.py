"""
Hosted-API LLM-Wiki builder.

Same two-pass design as build_local_wiki.py (grounded extract -> cluster+write,
>=2-citation rule), but the extractor is a hosted API endpoint instead of a
local GPU model. Supports three provider types via --provider:

  - nvidia     : NVIDIA Integrate free tier (poolside/laguna-*, thinkingmachines/inkling)
  - openai     : OpenAI or OpenAI-compatible gateway (gpt-5.x; needs user header
                 + max_completion_tokens on some gateways)
  - anthropic  : Anthropic or Vertex-compatible gateway (Claude-* models)

This lets us benchmark hosted models (free and paid/frontier) against the local
Gemma models on an identical pipeline. Reuses the prompts, JSONL layout, and
pass-2 clustering from build_local_wiki.py so every wiki is directly
comparable. The ONLY difference is the inference call.

API credentials are read from a gitignored .env file (NVIDIA_API_KEY,
OPENAI_API_KEY/BASE_URL, ANTHROPIC_API_KEY/BASE_URL) or the process
environment — never hardcoded, never committed.

Usage:
    python scripts/build_api_wiki.py --provider nvidia \\
        --output-dir free-llm-wiki/nvidia-laguna --chapters subset [--resume]
    python scripts/build_api_wiki.py --provider openai --model gpt-5.6-terra \\
        --output-dir frontier-llm-wiki/openai-gpt-5.6-terra --chapters subset
    python scripts/build_api_wiki.py --provider anthropic --model Claude-Sonnet-5 \\
        --output-dir frontier-llm-wiki/anthropic-sonnet-5 --chapters subset
"""
import os
import sys
import json
import time
import random
import datetime
import argparse
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# Make the local-wiki engine importable so we reuse its prompts + pass-2 logic
sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_local_wiki as bl  # noqa: E402

# load .env if python-dotenv is available (optional; env vars also work)
try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

from openai import OpenAI  # noqa: E402


# ----------------------------------------------------------------------------
# API client
# ----------------------------------------------------------------------------

def make_client(provider: str = "nvidia"):
    """Build a client for the given provider. Returns (client, model, provider).
    provider is one of: nvidia, openai, anthropic. Credentials come from env."""
    if provider == "nvidia":
        base = os.environ.get("NVIDIA_BASE_URL", "https://integrate.api.nvidia.com/v1")
        key = os.environ.get("NVIDIA_API_KEY")
        if not key:
            sys.exit("ERROR: NVIDIA_API_KEY not set. Put it in .env or the environment.")
        model = os.environ.get("NVIDIA_MODEL", "poolside/laguna-xs-2.1")
        return OpenAI(base_url=base, api_key=key), model, "nvidia"
    if provider == "openai":
        base = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1")
        key = os.environ.get("OPENAI_API_KEY")
        if not key:
            sys.exit("ERROR: OPENAI_API_KEY not set. Put it in .env or the environment.")
        model = os.environ.get("OPENAI_MODEL", "gpt-5.6-terra")
        return OpenAI(base_url=base, api_key=key), model, "openai"
    if provider == "anthropic":
        from anthropic import Anthropic
        base = os.environ.get("ANTHROPIC_BASE_URL", "https://api.anthropic.com")
        key = os.environ.get("ANTHROPIC_API_KEY")
        if not key:
            sys.exit("ERROR: ANTHROPIC_API_KEY not set. Put it in .env or the environment.")
        model = os.environ.get("ANTHROPIC_MODEL", "Claude-Sonnet-5")
        return Anthropic(base_url=base, api_key=key), model, "anthropic"
    sys.exit(f"ERROR: unknown provider {provider!r}")


# Per-model tuning. Reasoning models (e.g. thinkingmachines/inkling, gpt-5.6)
# emit a chain-of-thought before the final answer and/or reject temperature=0,
# so they need a larger token budget and different sampling; standard chat
# models answer directly and prefer greedy decoding.
MODEL_CONFIG = {
    # --- NVIDIA free tier ---
    "thinkingmachines/inkling": {
        "max_tokens": 8192, "temperature": 0.6, "top_p": 0.95,
    },
    "poolside/laguna-xs-2.1": {
        "max_tokens": 2000, "temperature": 0.0, "top_p": 1.0,
    },
    # --- Frontier (AMD gateway) ---
    "gpt-5.6-terra": {  # Azure OpenAI reasoning model: no temp, max_completion_tokens
        "max_tokens": 8000, "temperature": None, "top_p": None,
        "use_completion_tokens": True, "needs_user": True,
    },
    "Claude-Sonnet-5": {  # Anthropic via Vertex gateway: rejects top_p
        "max_tokens": 8000, "temperature": 0.0, "top_p": None,
    },
}
DEFAULT_CONFIG = {"max_tokens": 2000, "temperature": 0.0, "top_p": 1.0}


def config_for(model: str) -> dict:
    # case-insensitive match for the frontier models (gateway uses mixed case)
    for k, v in MODEL_CONFIG.items():
        if k.lower() == model.lower():
            return v
    return DEFAULT_CONFIG


def chat_complete(client, model: str, system: str, user: str,
                  provider: str = "nvidia", max_retries: int = 5) -> str:
    """Call the right endpoint for the provider with exponential backoff on
    rate-limit/transient errors. Per-model sampling/token config from
    MODEL_CONFIG. Returns the assistant's text answer."""
    cfg = config_for(model)
    delay = 2.0
    last_err = None
    for attempt in range(max_retries):
        try:
            if provider == "anthropic":
                return _complete_anthropic(client, model, cfg, system, user)
            return _complete_openai(client, model, cfg, system, user)
        except Exception as e:
            last_err = e
            msg = str(e).lower()
            retryable = ("429" in msg or "rate" in msg or "timeout" in msg
                         or "503" in msg or "502" in msg or "500" in msg
                         or "connection" in msg or "overloaded" in msg)
            if not retryable and attempt >= 2:
                raise
            time.sleep(delay + random.uniform(0, 1))
            delay *= 2
    raise last_err  # type: ignore[misc]


def _complete_openai(client, model, cfg, system, user) -> str:
    kwargs = dict(
        model=model,
        messages=[{"role": "system", "content": system},
                  {"role": "user", "content": user}],
        stream=False,
    )
    # gpt-5.x needs max_completion_tokens instead of max_tokens
    if cfg.get("use_completion_tokens"):
        kwargs["max_completion_tokens"] = cfg["max_tokens"]
    else:
        kwargs["max_tokens"] = cfg["max_tokens"]
    if cfg.get("temperature") is not None:
        kwargs["temperature"] = cfg["temperature"]
    if cfg.get("top_p") is not None:
        kwargs["top_p"] = cfg["top_p"]
    if cfg.get("needs_user"):
        kwargs["user"] = os.environ.get("GATEWAY_USER", "")
    comp = client.chat.completions.create(**kwargs)
    return comp.choices[0].message.content or ""


def _complete_anthropic(client, model, cfg, system, user) -> str:
    # Anthropic takes system as a top-level param, not in messages
    kwargs = dict(model=model, system=system, max_tokens=cfg["max_tokens"],
                  messages=[{"role": "user", "content": user}])
    if cfg.get("temperature") is not None:
        kwargs["temperature"] = cfg["temperature"]
    if cfg.get("top_p") is not None:
        kwargs["top_p"] = cfg["top_p"]
    resp = client.messages.create(**kwargs)
    # content is a list of blocks; concatenate text blocks
    parts = [b.text for b in resp.content if getattr(b, "type", None) == "text"]
    return "".join(parts)


# ----------------------------------------------------------------------------
# Pass 1: extract via API (mirrors bl.extract_chapter, minus the GPU)
# ----------------------------------------------------------------------------

def extract_chapter_api(client, model, provider, year, title, full_text):
    chunks = bl.chunk_text(full_text, limit=16000)
    if len(chunks) > 6:
        print(f"  [cap] chapter has {len(chunks)} chunks; limiting to first 6",
              flush=True)
        chunks = chunks[:6]
    all_concepts = []
    for ci, ch in enumerate(chunks):
        prompt = bl.EXTRACT_USER_TMPL.format(year=year, title=title, text=ch)
        if ci == 0:
            prompt = bl.FEWSHOT + "\n" + prompt
        try:
            resp = chat_complete(client, model, bl.EXTRACT_SYSTEM, prompt,
                                 provider=provider)
        except Exception as e:
            print(f"  [chunk {ci}] API error after retries: {e}", flush=True)
            continue
        parsed = bl.parse_json_obj(resp)
        if not parsed or "concepts" not in parsed:
            print(f"  [chunk {ci}] no JSON; raw[:120]={resp[:120]!r}",
                  flush=True)
            continue
        added = 0
        for c in parsed.get("concepts", []):
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
            added += 1
        print(f"  [chunk {ci+1}/{len(chunks)}] +{added}", flush=True)
    # dedup within chapter (same logic as the local builder)
    by_key = {}
    for c in all_concepts:
        k = bl.normalize_title_for_cluster(c["title"])
        if k not in by_key or len(c["evidence_quotes"]) > len(by_key[k]["evidence_quotes"]):
            by_key[k] = c
    return list(by_key.values())


def run_pass1(client, model, provider, out_dir, chapters, resume):
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    (out / "concepts").mkdir(exist_ok=True)
    jsonl = out / "extraction.jsonl"

    done_keys = set()
    if resume and jsonl.exists():
        for line in jsonl.read_text(encoding="utf-8").splitlines():
            try:
                rec = json.loads(line)
                # Only treat a chapter as done if it actually yielded concepts.
                # A zero-concept entry usually means the API call failed (e.g.
                # endpoint degraded), so we retry it on resume.
                if rec.get("concepts"):
                    done_keys.add(rec["rel"])
            except Exception:
                pass
        print(f"[resume] {len(done_keys)} chapters already in extraction.jsonl",
              flush=True)

    t0 = time.time()
    with open(jsonl, "a", encoding="utf-8") as fjson:
        for i, chap in enumerate(chapters, 1):
            year, title, rel = bl.chapter_meta(chap)
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
            concepts = extract_chapter_api(client, model, provider, year, title, text)
            rec = {"rel": rel, "year": year, "title": title,
                   "concepts": concepts,
                   "ts": datetime.datetime.now().isoformat(timespec="seconds")}
            fjson.write(json.dumps(rec, ensure_ascii=False) + "\n")
            fjson.flush()
            print(f"  -> {len(concepts)} concept(s); elapsed "
                  f"{time.time()-t0:.0f}s", flush=True)
    print(f"[pass1] done in {time.time()-t0:.0f}s", flush=True)
    return jsonl


# ----------------------------------------------------------------------------
# CLI
# ----------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--output-dir", required=True)
    ap.add_argument("--provider", choices=["nvidia", "openai", "anthropic"],
                    default="nvidia",
                    help="Which API provider/SDK to use.")
    ap.add_argument("--model", default=None,
                    help="Override model id (else read from env, e.g. "
                         "OPENAI_MODEL / ANTHROPIC_MODEL / NVIDIA_MODEL).")
    ap.add_argument("--chapters", choices=["all", "subset", "smoke"],
                    default="subset")
    ap.add_argument("--resume", action="store_true")
    ap.add_argument("--pass-only", choices=["1", "2", "3"])
    ap.add_argument("--synthesize", action="store_true",
                    help="After pass-2, run pass-3: rewrite each concept page "
                         "as a synthesized narrative via the API model.")
    ap.add_argument("--agent-loop", action="store_true",
                    help="Manual evaluator-optimizer loop (same contract as "
                         "the local builder) for pass-3. Comparable metric.")
    ap.add_argument("--fast-agent", action="store_true",
                    help="Use fast-agent's native evaluator_optimizer "
                         "workflow for pass-3 (API models only). Mutually "
                         "exclusive with --agent-loop.")
    ap.add_argument("--max-refinements", type=int, default=5)
    ap.add_argument("--min-rating", choices=["EXCELLENT", "GOOD", "FAIR"],
                    default="GOOD")
    args = ap.parse_args()

    if args.model:
        os.environ[args.provider.upper() + "_MODEL"] = args.model

    chapters = bl.list_chapters(args.chapters)
    print(f"[plan] provider={args.provider}  out={args.output_dir}  "
          f"chapters={args.chapters} ({len(chapters)} files)", flush=True)

    out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)
    jsonl = out / "extraction.jsonl"

    want_pass1 = args.pass_only != "2" and args.pass_only != "3"
    want_pass2 = args.pass_only != "1" and args.pass_only != "3"
    want_pass3 = args.synthesize or args.pass_only == "3"

    client = model = provider = None
    if want_pass1 or want_pass3:
        client, model, provider = make_client(args.provider)
        print(f"[api] provider={provider}  model={model}", flush=True)
    if want_pass1:
        run_pass1(client, model, provider, args.output_dir, chapters, args.resume)
    if want_pass2:
        if not jsonl.exists():
            print("[pass2] no extraction.jsonl; skipping", flush=True)
            want_pass3 = False
        else:
            model_label = (args.model or os.environ.get(
                args.provider.upper() + "_MODEL", args.provider))
            stats = bl.run_pass2(model_label, args.output_dir, jsonl)
            print(f"[pass2] {stats}", flush=True)

    if want_pass3:
        if not jsonl.exists():
            print("[pass3] no extraction.jsonl; skipping synthesis", flush=True)
        else:
            rows = bl.load_extractions(jsonl)
            clusters = bl.cluster_concepts(rows)
            promoted = {}
            for k, cl in clusters.items():
                if len({c["rel"] for c in cl["citations"]}) >= 2:
                    slug = bl.slugify(cl["title"])
                    base, n = slug, 2
                    while slug in promoted:
                        slug = f"{base}_{n}"; n += 1
                    promoted[slug] = cl
            if not promoted:
                print("[pass3] no promoted concepts to synthesize", flush=True)
            elif args.fast_agent:
                # Native fast-agent evaluator-optimizer workflow (API only).
                run_pass3_fastagent(args.output_dir, promoted, args.provider,
                                    model, args.max_refinements, args.min_rating)
            elif args.agent_loop:
                # Manual loop with the SAME contract as the local builder, so
                # the convergence metric is comparable across all models.
                def gen_fn(system, user):
                    return chat_complete(client, model, system, user,
                                         provider=provider)
                def eval_fn(system, user):
                    return chat_complete(client, model, system, user,
                                         provider=provider)
                print(f"[pass3-loop] fast-agent OFF; manual loop "
                      f"max_refinements={args.max_refinements} "
                      f"min_rating={args.min_rating}", flush=True)
                bl.run_pass3_agent_loop(
                    args.output_dir, promoted, gen_fn, eval_fn,
                    max_refinements=args.max_refinements,
                    min_rating=args.min_rating,
                    batch_label=f"{provider}/{model}")
            else:
                def call_fn(system, user):
                    return chat_complete(client, model, system, user,
                                         provider=provider)
                bl.run_pass3_synthesize(args.output_dir, promoted, call_fn,
                                        batch_label=f"{provider}/{model}")


def run_pass3_fastagent(out_dir, promoted, provider, model, max_refinements,
                        min_rating):
    """Native fast-agent evaluator-optimizer workflow (API models only).

    Builds a FastAgent app with a synthesizer + evaluator agent wired to the
    configured provider/model, then runs evaluator_optimizer per cluster.
    fast-agent returns only the final synthesized string, so we re-score once
    at the end to capture the rating for the convergence metric. Writes the
    same synthesis_meta.jsonl as the manual loop path.
    """
    import asyncio
    import json as _json
    from fast_agent import FastAgent

    out = Path(out_dir)
    concepts_dir = out / "concepts"
    meta_path = out / "synthesis_meta.jsonl"
    # Map provider -> fast-agent model namespace (anthropic.X / openai.X)
    ns = {"anthropic": "anthropic", "openai": "openai", "nvidia": "openai"}[provider]
    fa_model = f"{ns}.{model}"
    print(f"[pass3-fastagent] model={fa_model} max_refinements={max_refinements} "
          f"min_rating={min_rating}", flush=True)

    fast = FastAgent("wiki-synth-loop")

    @fast.agent(name="synthesizer", instruction=bl.SYNTH_SYSTEM, model=fa_model)
    async def synthesizer():
        ...

    @fast.agent(name="evaluator", instruction=bl.EVAL_SYSTEM, model=fa_model)
    async def evaluator():
        ...

    @fast.evaluator_optimizer(
        name="synth_loop", generator="synthesizer", evaluator="evaluator",
        min_rating=min_rating, max_refinements=max_refinements,
    )
    async def synth_loop():
        ...

    async def _run():
        async with fast.run() as agent:
            with open(meta_path, "w", encoding="utf-8") as fmeta:
                n = len(promoted)
                for i, (slug, cluster) in enumerate(sorted(promoted.items()), 1):
                    title = cluster["title"]
                    siblings = [cl["title"] for cl in promoted.values()
                                if cl["title"] != title][:12]
                    prompt = bl.build_synth_prompt(cluster, siblings)
                    try:
                        md = await agent.synth_loop.send(prompt)
                    except Exception as e:
                        print(f"  [fa {i}/{n}] {title}: FAILED ({e})",
                              flush=True)
                        rec = {"slug": slug, "title": title, "iterations": max_refinements,
                               "final_rating": None, "reason": str(e)[:200],
                               "converged": False}
                        fmeta.write(_json.dumps(rec, ensure_ascii=False) + "\n")
                        fmeta.flush(); continue
                    # re-score to capture the rating (fast-agent hides it)
                    try:
                        ev = await agent.evaluator.send(
                            bl.build_eval_prompt(cluster, md))
                    except Exception:
                        ev = ""
                    rating, reason = bl.parse_rating(ev)
                    ok = (f"# {title}" in md and "## Sources" in md)
                    if ok:
                        (concepts_dir / f"{slug}.md").write_text(
                            md.strip() + "\n", encoding="utf-8")
                    min_level = bl.RATING_ORDER.get(min_rating.upper(), 2)
                    converged = bool(rating and bl.RATING_ORDER[rating] >= min_level)
                    rec = {"slug": slug, "title": title,
                           "iterations": max_refinements,  # fast-agent hides actual count
                           "final_rating": rating, "reason": reason,
                           "converged": converged}
                    fmeta.write(_json.dumps(rec, ensure_ascii=False) + "\n")
                    fmeta.flush()
                    print(f"  [fa {i}/{n}] {title}: rating={rating} "
                          f"converged={converged}", flush=True)

    asyncio.run(_run())


if __name__ == "__main__":
    main()
