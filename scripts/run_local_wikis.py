"""
Orchestrate sequential local-LLM-Wiki builds across one or more models.

Runs scripts/build_local_wiki.py for each model (E4B then E2B by default),
flushing the CUDA cache between runs, and prints a final side-by-side
comparison table. A single model can be (re)run with --model.

Usage:
    python scripts/run_local_wikis.py --chapters subset [--model e4b|--model e2b]
"""
import os
import sys
import json
import time
import shutil
import argparse
import subprocess
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# Models to build, in run order. Keys are the short slugs used by --model.
MODELS = [
    {"slug": "e4b", "model_id": "google/gemma-4-E4B-it",
     "out": "local-llm-wiki/gemma-4-e4b"},
    {"slug": "e2b", "model_id": "google/gemma-4-E2B-it",
     "out": "local-llm-wiki/gemma-4-e2b"},
]

# Known venv that has torch+transformers installed. NOTE: the hermes-agent
# rotates this venv periodically and renames the old one to venv.stale.*;
# prefer the stale (torch-equipped) one and fall back to the live one.
_HERMES_BASE = r"C:\Users\hevan\AppData\Local\hermes\hermes-agent"
HERMES_PY_CANDIDATES = [
    os.path.join(_HERMES_BASE, "venv", "Scripts", "python.exe"),
]
# add any venv.stale.* directories (sorted newest-first by mtime)
import glob as _glob
for stale in sorted(_glob.glob(os.path.join(_HERMES_BASE, "venv.stale.*")),
                    key=lambda p: os.path.getmtime(p), reverse=True):
    HERMES_PY_CANDIDATES.append(os.path.join(stale, "Scripts", "python.exe"))


def find_python_with_torch() -> str:
    candidates = []
    venv = os.environ.get("VIRTUAL_ENV")
    if venv:
        candidates.append(os.path.join(venv, "Scripts", "python.exe"))
        candidates.append(os.path.join(venv, "bin", "python"))
    candidates.extend(HERMES_PY_CANDIDATES)
    candidates.append(sys.executable)
    seen = set()
    for c in candidates:
        if c in seen or not os.path.isfile(c):
            continue
        seen.add(c)
        r = subprocess.run([c, "-c", "import torch,transformers"],
                           capture_output=True)
        if r.returncode == 0:
            return c
    return sys.executable


def flush_cuda(py: str):
    print("\n[cuda] flushing cache between runs...", flush=True)
    subprocess.run([py, "-c",
                    "import torch;torch.cuda.empty_cache();"
                    "torch.cuda.synchronize();print('flushed')"],
                   check=False)


def run_model(py: str, model_id: str, out: str, chapters: str,
              resume: bool) -> int:
    print("\n" + "=" * 72)
    print(f"BUILDING  {model_id}")
    print(f"  -> {out}  (chapters={chapters}, resume={resume})")
    print("=" * 72, flush=True)
    cmd = [py, "-u", "scripts/build_local_wiki.py",
           "--model-id", model_id,
           "--output-dir", out,
           "--chapters", chapters]
    if resume:
        cmd.append("--resume")
    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"
    t0 = time.time()
    res = subprocess.run(cmd, env=env)
    dur = time.time() - t0
    print(f"[done] {model_id} exit={res.returncode}  "
          f"duration={dur/60:.1f} min", flush=True)
    return res.returncode


def gather_stats(out_dir: str) -> dict:
    import re as _re
    p = Path(out_dir)
    cdir = p / "concepts"
    concept_files = list(cdir.glob("*.md")) if cdir.exists() else []
    n_concepts = len(concept_files)
    total_chars = 0
    quote_lines = 0
    years = set()
    cite_re = _re.compile(r"\[(\d{4})\s+—")
    for cf in concept_files:
        txt = cf.read_text(encoding="utf-8", errors="replace")
        total_chars += len(txt)
        # evidence quotes are rendered as blockquote lines under each source
        quote_lines += sum(1 for ln in txt.splitlines() if ln.startswith("> "))
        for m in cite_re.finditer(txt):
            years.add(m.group(1))
    # candidate count: parse the build entry pass-2 writes to log.md
    n_cand = 0
    log = p / "log.md"
    if log.exists():
        m = _re.search(r"(\d+)\s+single-citation candidates",
                       log.read_text(encoding="utf-8", errors="replace"))
        if m:
            n_cand = int(m.group(1))
    # chapters actually processed
    jsonl = p / "extraction.jsonl"
    n_chapters = 0
    if jsonl.exists():
        n_chapters = sum(1 for line in jsonl.read_text(encoding="utf-8").splitlines()
                         if line.strip())
    return {
        "out": out_dir,
        "chapters": n_chapters,
        "concepts": n_concepts,
        "evidence_quotes": quote_lines,
        "years_covered": len(years),
        "chars": total_chars,
        "avg_chars": total_chars // max(n_concepts, 1),
    }


def print_comparison(stats_by_slug: dict):
    print("\n" + "=" * 72)
    print("SIDE-BY-SIDE COMPARISON")
    print("=" * 72)
    hdr = f"{'metric':28s}"
    for slug in stats_by_slug:
        hdr += f"  {slug:>12s}"
    print(hdr)
    print("-" * len(hdr))
    for key, label in [("chapters", "chapters processed"),
                       ("concepts", "concept pages"),
                       ("years_covered", "years covered"),
                       ("evidence_quotes", "evidence quotes"),
                       ("chars", "total chars"),
                       ("avg_chars", "avg chars/page")]:
        row = f"{label:28s}"
        for slug in stats_by_slug:
            row += f"  {stats_by_slug[slug][key]:>12,d}"
        print(row)
    print("\nSee local-llm-wiki/<model>/index.md for each model's catalog.")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--chapters", choices=["all", "subset", "smoke"],
                    default="subset")
    ap.add_argument("--resume", action="store_true",
                    help="Pass --resume to pass 1 (skip chapters already in "
                         "extraction.jsonl).")
    ap.add_argument("--model", choices=["e4b", "e2b"],
                    help="Run only one model (default: both, E4B then E2B).")
    ap.add_argument("--fresh", action="store_true",
                    help="Wipe the model's output dir before building.")
    args = ap.parse_args()

    targets = [m for m in MODELS if not args.model or m["slug"] == args.model]
    py = find_python_with_torch()
    print(f"[python] {py}", flush=True)

    for i, m in enumerate(targets):
        if args.fresh:
            out = Path(m["out"])
            if out.exists():
                print(f"[fresh] removing {out}", flush=True)
                shutil.rmtree(out)
        if i > 0:
            flush_cuda(py)
        run_model(py, m["model_id"], m["out"], args.chapters, args.resume)

    stats = {m["slug"]: gather_stats(m["out"]) for m in targets}
    print_comparison(stats)


if __name__ == "__main__":
    main()
