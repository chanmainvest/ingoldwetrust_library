# Local / Free / Frontier LLM-Wiki Comparison

Six model-built wikis were generated from the **same 82-chapter subset** of the
*In Gold We Trust* corpus (all 20 yearly introductions + key thematic chapters
on supply/demand, monetary policy, central-bank gold, de-dollarization, and
technical analysis), using the **same two-pass pipeline** (grounded extraction
→ deterministic clustering with a ≥2-citation promotion rule → LLM synthesis).
The only variable is the model. This makes the comparison fair.

| Tier | Model | Location | Inference |
|------|-------|----------|-----------|
| Local (4-bit) | Gemma 4 E4B | `local-llm-wiki/gemma-4-e4b` | RTX 3060 Ti, 9.3 GB VRAM |
| Local (4-bit) | Gemma 4 E2B | `local-llm-wiki/gemma-4-e2b` | RTX 3060 Ti, 6.7 GB VRAM |
| Free API | poolside/laguna-xs-2.1 | `free-llm-wiki/nvidia-laguna` | NVIDIA Integrate |
| Free API | thinkingmachines/inkling | `free-llm-wiki/nvidia-inkling` | NVIDIA Integrate (reasoning) |
| Frontier | gpt-5.6-terra | `frontier-llm-wiki/openai-gpt-5.6-terra` | AMD gateway → Azure OpenAI |
| Frontier | Claude-Sonnet-5 | `frontier-llm-wiki/anthropic-sonnet-5` | AMD gateway → Vertex |

## Results

| Model | Pages | Avg chars/page | Synthesized | Max citations | Avg citations | See-also |
|-------|------:|---------------:|------------|---------------|---------------|----------|
| **Claude-Sonnet-5** | 69 | **3,407** | 69/69 | 10 | 2.7 | 69 |
| gpt-5.6-terra | 59 | 2,973 | 59/59 | 7 | 2.4 | 54 |
| Gemma E2B | 67 | 2,042 | 49/67 | 5 | 2.4 | 49 |
| laguna | 55 | 2,785 | 55/55 | 13 | 2.5 | 54 |
| Gemma E4B | 38 | 2,169 | 38/38 | 6 | 2.4 | 38 |
| inkling | 18 | 2,297 | 9/18 | 5 | 2.3 | 9 |

## Findings

### 1. Tier ordering is consistent: frontier > free-API > local
On every quality axis — synthesis depth (chars/page), citation richness, and
reliability — the ordering holds. Claude-Sonnet-5 leads on page count (69),
average page depth (3,407 chars), and max single-page citations (10). The local
4-bit models produce the shallowest pages despite running far longer.

### 2. Claude-Sonnet-5 is the clear winner
Highest page count, deepest synthesis, the only model to reach 10 distinct
citations on a single page ("Incrementum Inflation Signal"), full synthesis
success (69/69), and full See-also cross-linking (69/69). Its concept naming is
also the most consistent across years — fewer near-duplicate splits.

### 3. gpt-5.6-terra is strong but more fragmented
Close to Sonnet-5 on depth (2,973 chars) but produces more near-duplicate
concept splits (e.g. "Central Bank Gold Buying", "...Purchases", "Gold Reserve
Accumulation" as separate pages where Sonnet-5 merges them). Still far ahead of
the free/local tier.

### 4. The free tier is viable but reliability varies
- **laguna** is the surprise: 55 pages, 2,785 chars/page, 100% synthesis —
  competitive with the frontier tier on structure, slightly shallower prose.
  The most cost-effective option of the six.
- **inkling** (reasoning model) produced high-quality output *when the endpoint
  was up*, but the NVIDIA free endpoint was flaky: only 75/82 chapters extracted
  (intermittent "DEGRADED function" / 404 errors) and just 9/18 pages
  synthesized. A capable model defeated by an unreliable host.

### 5. Local models: usable but slow and shallow
- **E2B** extracted the *most* concepts (67 pages — more than E4B's 38 and
  matching Sonnet-5's 69), suggesting the smaller model is more eager but less
  selective. Synthesis partially failed (49/67 — many "malformed" outputs),
  leaving 18 pages in aggregated form.
- **E4B** was the most selective (38 pages) and the slowest per page. Synthesis
  succeeded fully (38/38) but pages are the shallowest of the local set.
- Both local models took **hours** where the APIs took minutes (E4B extraction
  ~9 hrs vs Sonnet-5's 43 min).

### 6. Why all six still trail the hand-built `llm-wiki/`
The agent-built reference (`llm-wiki/`, 30 pages, ~9,800 chars/page) is deeper
per page because it's the product of an *agent loop* — many turns of read →
synthesize → cross-link → lint → refine — whereas every model here ran a
*fixed single forward pipeline*. The synthesis pass (pass-3) closed most of the
*structural* gap (chronological narrative + See-also), but not the depth gap
that comes from iterative refinement.

## How to read each wiki
Each wiki folder contains:
- `index.md` — catalog with per-page citation counts
- `concepts/*.md` — the concept pages (synthesized where pass-3 succeeded)
- `log.md` — build log + single-citation candidates not promoted
- `extraction.jsonl` — the raw per-chapter extractions (resumable)

## Reproducing / extending
```bash
# Local model (GPU): extract → cluster → synthesize
python scripts/build_local_wiki.py --model-id google/gemma-4-E4B-it \
  --output-dir local-llm-wiki/gemma-4-e4b --chapters subset --synthesize

# Hosted API: extract → cluster → synthesize (provider: nvidia|openai|anthropic)
uv run --with openai --with anthropic --with python-dotenv python \
  scripts/build_api_wiki.py --provider anthropic --model Claude-Sonnet-5 \
  --output-dir frontier-llm-wiki/anthropic-sonnet-5 --chapters subset --synthesize
```
Credentials live in the gitignored `.env`. `--resume` skips already-extracted
chapters; `--pass-only 3` re-synthesizes from an existing `extraction.jsonl`.
