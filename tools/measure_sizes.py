"""Measure PDF size and clean build time for test/size-benchmark.tex."""

import argparse
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
VARIANTS = ("none", "static", "overlays", "vector", "raster")


def pages(pdf):
    for line in subprocess.check_output(["pdfinfo", str(pdf)], text=True).splitlines():
        if line.startswith("Pages:"):
            return int(line.split()[1])
    raise RuntimeError(f"No page count for {pdf}")


def measure(variant, outdir, engine):
    target = outdir / variant
    shutil.rmtree(target, ignore_errors=True)
    target.mkdir(parents=True)
    source = target / f"size-{variant}.tex"
    source.write_text(f"\\def\\floralvariant{{{variant}}}\n\\input{{test/size-benchmark.tex}}\n")
    relative = source.relative_to(ROOT)
    env = dict(os.environ, TIKZFLORA=str(engine))
    env["TEXINPUTS"] = f"{ROOT}:{engine}/tex//:"
    env["FLORA_LUA"] = f"{engine}/lua"
    if variant == "raster":
        command = [sys.executable, "tools/build_animation.py", "--engine", str(engine),
                   "--outdir", str(target.relative_to(ROOT)), str(relative)]
    else:
        command = ["latexmk", "-g", "-lualatex", "-interaction=nonstopmode", "-halt-on-error",
                   f"-outdir={target.relative_to(ROOT)}", str(relative)]
    start = time.monotonic()
    subprocess.run(command, cwd=ROOT, env=env, check=True, stdout=subprocess.DEVNULL)
    seconds = time.monotonic() - start
    pdf = target / f"size-{variant}.pdf"
    return {"variant": variant, "pages": pages(pdf), "bytes": pdf.stat().st_size,
            "build_seconds": round(seconds, 1)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--engine", type=Path, required=True, help="local tikz-flora checkout")
    parser.add_argument("--outdir", type=Path, default=ROOT / "build/size-benchmark")
    parser.add_argument("--variant", action="append", choices=VARIANTS,
                        help="measure only this variant; may be repeated")
    args = parser.parse_args()
    outdir = args.outdir.resolve()
    engine = args.engine.resolve()
    rows = [measure(variant, outdir, engine) for variant in args.variant or VARIANTS]
    commit = subprocess.check_output(["git", "-C", str(ROOT), "rev-parse", "--short", "HEAD"],
                                     text=True).strip()
    pinned = engine / "engine-commit.txt"
    if pinned.is_file():
        engine_commit = pinned.read_text().split()[0][:7]
    else:
        engine_commit = subprocess.check_output(
            ["git", "-C", str(engine), "rev-parse", "--short", "HEAD"], text=True).strip()
    tex = subprocess.check_output(["lualatex", "--version"], text=True).splitlines()[0]
    result = {"commit": commit, "engine": engine_commit, "tex": tex,
              "platform": platform.platform(), "rows": rows}
    (outdir / "results.json").write_text(json.dumps(result, indent=2) + "\n")
    print(f"{'variant':10}{'pages':>7}{'MB':>10}{'seconds':>10}")
    for row in rows:
        print(f"{row['variant']:10}{row['pages']:>7}{row['bytes'] / 1e6:>10.1f}{row['build_seconds']:>10.1f}")


if __name__ == "__main__":
    main()
