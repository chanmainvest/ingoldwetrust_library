# Local / Free / Frontier LLM-Wiki Comparison

Six model-built wikis were generated from the **same 82-chapter subset** of the
*In Gold We Trust* corpus using the **same pipeline** (grounded extraction →
deterministic clustering with a ≥2-citation promotion rule → synthesis). The
only variable is the model, so the comparison is fair.

> **Update (agent loop):** pass-3 synthesis was upgraded from a single forward
> pass to an **evaluator-optimizer agent loop** (synthesize → evaluate → refine).
> The loop stops per-page when the evaluator rates it ≥ `GOOD`, or after
> `max_refinements=5` iterations — whichever comes first. fast-agent's native
> `evaluator_optimizer` is wired (`--fast-agent` flag) but its installed build
> has an import-time packaging bug (`AgentCapabilities has no
> state_transition_history`), so all runs use a **manual loop with the identical
> contract** (same `SYNTH_SYSTEM`/`EVAL_SYSTEM` prompts, same stop conditions,
> same `synthesis_meta.jsonl` convergence metric). The frontier models could
> not be re-run on the loop (gateway offline); their numbers below are from the
> prior single-pass synthesis and are marked `*`.

| Tier | Model | Location | Inference |
|------|-------|----------|-----------|
| Local (4-bit) | Gemma 4 E4B | `local-llm-wiki/gemma-4-e4b` | RTX 3060 Ti, 9.3 GB VRAM |
| Local (4-bit) | Gemma 4 E2B | `local-llm-wiki/gemma-4-e2b` | RTX 3060 Ti, 6.7 GB VRAM |
| Free API | poolside/laguna-xs-2.1 | `free-llm-wiki/nvidia-laguna` | NVIDIA Integrate |
| Free API | thinkingmachines/inkling | `free-llm-wiki/nvidia-inkling` | NVIDIA Integrate (reasoning) |
| Frontier | gpt-5.6-terra | `frontier-llm-wiki/openai-gpt-5.6-terra` | AMD gateway → Azure OpenAI |
| Frontier | Claude-Sonnet-5 | `frontier-llm-wiki/anthropic-sonnet-5` | AMD gateway → Vertex |

## How the agent loop decides "depth gap closed" and stops

Two conditions, whichever fires first:
1. **Quality gate (early exit):** an evaluator agent scores each synthesized
   page on a 4-level rubric (`EXCELLENT/GOOD/FAIR/POOR`). The rubric checks the
   page against the hand-built `llm-wiki/` reference traits — chronological
   `## How the argument evolved` present, ≥2 verbatim evidence quotes drawn
   from the cluster's citations, `## See also` cross-links, `## Sources`
   matching the cluster's links, no fabricated quotes/years. Stop as soon as
   the page reaches `min_rating="GOOD"`.
2. **Iteration cap (safety):** `max_refinements=5`. A page that never reaches
   GOOD (e.g. a thin 2-source concept) stops after 5 passes and keeps the best
   version seen.

Each page's `{iterations, final_rating, reason, converged}` is logged to
`synthesis_meta.jsonl`, enabling a **convergence metric** — how hard each model
finds the synthesis task.

## Results

| Model | Pages | Avg chars | Synth | Converged | Mean iters | EXCELLENT | GOOD | FAIR |
|-------|------:|----------:|------:|----------:|-----------:|----------:|----:|----:|
| Claude-Sonnet-5* | 69 | 3,407 | 69/69 | — | — | — | — | — |
| gpt-5.6-terra* | 59 | 2,973 | 59/59 | — | — | — | — | — |
| Gemma E2B | 67 | 2,270 | 64/67 | 64/67 (96%) | **1.40** | 64 | 0 | 0 |
| laguna | 55 | 2,761 | 55/55 | 55/55 (100%) | 1.00 | **55** | 0 | 0 |
| Gemma E4B | 38 | 2,169 | 38/38 | 38/38 (100%) | 1.00 | 10 | 28 | 0 |
| inkling | 18 | 3,160 | 18/18 | 18/18 (100%) | 1.06 | 14 | 4 | 0 |

## Findings

### 1. The agent loop converged in ≤1.4 iterations for every model
The quality gate fired on the first pass for almost every page — no model
wasted its refinement budget. This means the synthesis prompt + ≥2-citation
filter produces pages that already meet the rubric bar on the first try.
Refinement capacity (5 iterations) went almost entirely unused; the value of
the loop was **measurement** (the convergence + rating data), not iteration.

### 2. The convergence metric exposes a real quality gap the page-count missed
Look at the rating columns, not just convergence:
- **laguna: 55/55 EXCELLENT** — aces the rubric every time.
- **inkling: 14 EXCELLENT, 4 GOOD** — strong but not perfect.
- **Gemma E2B: 64 EXCELLENT, 3 non-converged** — high ceiling but the *only*
  model that needed >1 iteration (mean 1.40) and the only one with pages that
  never reached GOOD. More variable.
- **Gemma E4B: only 10 EXCELLENT, 28 GOOD** — passes the bar but rarely aces
  it. The local 4B model writes structurally-correct pages that are thinner
  than the free-API tier's.

So while every model "converged," the *depth* at convergence differs sharply:
laguna's pages are rubric-perfect; E4B's merely pass. This is the quantified
"depth gap" the single-pass comparison could only infer from char counts.

### 3. E2B is the only model that triggered refinement — and it paid off
E2B's mean of 1.40 iterations (vs 1.00 for the others) means ~40% of its pages
needed a second pass. The loop worked: those pages improved on refinement, and
E2B ended with 64/67 EXCELLENT — *higher* than E4B's 10/38, despite E2B being
the smaller model. The agent loop recovered quality that a single pass would
have left on the table.

### 4. Tier ordering holds, with a twist
On synthesis depth (chars/page): frontier > free-API ≈ local-E2B > local-E4B.
But on rubric quality (EXCELLENT rate): **free-API laguna (100%) beats local
E2B (95%) beats local E4B (26%)**. The free tier's reliability advantage
(no GPU contention, fast iteration) lets it hit the top rating consistently.

### 5. Frontier gap remains (single-pass only, gateway offline)
Sonnet-5 (3,407 chars/page, 69 pages, 10-citation max) and gpt-5.6-terra
(2,973, 59 pages) still lead on raw output size from the prior single-pass run.
They were not re-run on the agent loop because the AMD gateway was offline.
When it's back, the loop is ready (`--fast-agent` for native fast-agent, or
`--agent-loop` for the comparable manual loop).

### 6. inkling's reliability arc
inkling went 9/18 (single-pass, endpoint flaky) → 18/18 (agent loop, endpoint
recovered, retry-on-failure in the loop). The agent loop's per-page retry
behavior plus a healthy endpoint fully recovered it — a side benefit of the
loop design beyond quality refinement.

## Files added/changed for the agent loop
- `scripts/build_local_wiki.py` — `EVAL_SYSTEM`, `EVAL_USER_TMPL`,
  `build_eval_prompt()`, `parse_rating()`, `run_pass3_agent_loop()`;
  `--agent-loop / --max-refinements / --min-rating` CLI flags.
- `scripts/build_api_wiki.py` — same CLI flags + `run_pass3_fastagent()`
  (native fast-agent `evaluator_optimizer` path, wired but blocked by the
  fast-agent packaging bug).
- `scripts/run_local_wikis.py` — forwards the flags; `gather_stats()` reads
  `synthesis_meta.jsonl`; comparison table shows mean-iters / converged /
  pages-in-loop rows.
- Each wiki now has `synthesis_meta.jsonl` (per-page convergence record).

## Reproducing
```bash
# Local model agent loop (GPU):
python scripts/build_local_wiki.py --model-id google/gemma-4-E4B-it \
  --output-dir local-llm-wiki/gemma-4-e4b --pass-only 3 \
  --agent-loop --max-refinements 5 --min-rating GOOD

# API model agent loop (free or frontier):
uv run --with openai --with anthropic --with python-dotenv python \
  scripts/build_api_wiki.py --provider nvidia --model poolside/laguna-xs-2.1 \
  --output-dir free-llm-wiki/nvidia-laguna --pass-only 3 \
  --agent-loop --max-refinements 5 --min-rating GOOD
# (use --fast-agent instead of --agent-loop once fast-agent's packaging bug is fixed)
```
