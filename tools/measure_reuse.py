"""Cold and warm build time, peak memory and PDF size for test/reuse-benchmark.tex.

Cold: latexmk in an empty output directory. Warm: a second full latexmk
compile of the unchanged document after deleting everything but the flora
caches (<job>-flora/ and <job>.floral-cache), so every pass runs again with
the flora cache from the first compile in place.

Usage:
  TIKZFLORA=<engine> [REUSE=all] [S=5] [PATTERN=asanoha] measure_reuse.py LABEL VARIANT N K

VARIANT is none (Beamer only), off (theme, flora off) or adaptive; REUSE sets
the reuse value, PATTERN a pattern setting (a deck of that pattern instead of flora), N the frames, K the overlays per frame and S a section page
every S frames. Each build waits until the 1-minute load average is below
--max-load (default 4, at most --wait seconds) and records it. Peak RSS comes
from /usr/bin/time -l (macOS). Rows append to build/reuse-benchmark/results.jsonl.
"""

import argparse
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import time

ROOT = Path(__file__).resolve().parents[1]


def wait_for_quiet(max_load, wait):
    start = time.monotonic()
    while os.getloadavg()[0] >= max_load and time.monotonic() - start < wait:
        time.sleep(15)
    return round(os.getloadavg()[0], 2)


def build(out, src, env, max_load, wait):
    load = wait_for_quiet(max_load, wait)
    start = time.monotonic()
    r = subprocess.run(["/usr/bin/time", "-l", "latexmk", "-lualatex", "-interaction=nonstopmode",
                        "-halt-on-error", f"-outdir={out.relative_to(ROOT)}", str(src.relative_to(ROOT))],
                       cwd=ROOT, env=env, capture_output=True, text=True)
    wall = time.monotonic() - start
    if r.returncode:
        raise SystemExit(r.stdout[-2000:] + r.stderr[-2000:])
    rss = re.search(r"(\d+)\s+maximum resident", r.stderr)
    user = re.search(r"([\d.]+) user", r.stderr)
    passes = len(re.findall(r"Run number \d+ of rule 'lualatex'", r.stdout + r.stderr))
    pdf = out / "d.pdf"
    return {"wall": round(wall, 1), "user": float(user.group(1)) if user else None,
            "rss_mb": round(int(rss.group(1)) / 1e6) if rss else None, "passes": passes,
            "pdf_mb": round(pdf.stat().st_size / 1e6, 2), "load_before": load,
            "load_after": round(os.getloadavg()[0], 2)}


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("label")
    parser.add_argument("variant", choices=("none", "off", "adaptive"))
    parser.add_argument("frames", type=int)
    parser.add_argument("overlays", type=int)
    parser.add_argument("--max-load", type=float, default=4.0)
    parser.add_argument("--wait", type=float, default=1800)
    args = parser.parse_args()
    engine = os.environ["TIKZFLORA"]
    env = dict(os.environ, LC_ALL="C", FLORA_LUA=f"{engine}/lua", TEXINPUTS=f"{ROOT}:{engine}/tex//:")
    base = ROOT / "build/reuse-benchmark"
    out = base / args.label
    shutil.rmtree(out, ignore_errors=True)
    out.mkdir(parents=True)
    src = out / "d.tex"
    src.write_text(f"\\def\\floralpattern{{{os.environ.get('PATTERN', '')}}}\\def\\floralreuse{{{os.environ.get('REUSE', '')}}}\\def\\benchS{{{os.environ.get('S', '0')}}}"
                   f"\\def\\floralvariant{{{args.variant}}}\\def\\benchN{{{args.frames}}}"
                   f"\\def\\benchK{{{args.overlays}}}\\input{{test/reuse-benchmark.tex}}\n")
    row = {"label": args.label, "variant": args.variant, "reuse": os.environ.get("REUSE", ""), "pattern": os.environ.get("PATTERN", ""),
           "frames": args.frames, "overlays": args.overlays, "sections_every": int(os.environ.get("S", "0"))}
    row["cold"] = build(out, src, env, args.max_load, args.wait)
    for p in out.iterdir():
        if p.name not in ("d.tex", "d-flora", "d.floral-cache"):
            shutil.rmtree(p) if p.is_dir() else p.unlink()
    row["warm"] = build(out, src, env, args.max_load, args.wait)
    print(json.dumps(row), flush=True)
    with open(base / "results.jsonl", "a") as f:
        f.write(json.dumps(row) + "\n")


if __name__ == "__main__":
    main()
