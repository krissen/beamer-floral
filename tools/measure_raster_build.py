"""Measure cold and warm raster builds with per-step time, memory and disk.

RSS is the largest single subprocess, not the sum of concurrent raster jobs.
Disk is the largest sampled size of the output tree, every 500 ms.
"""

import argparse
import importlib.util
import json
import os
from pathlib import Path
import platform
import re
import shutil
import subprocess
import threading
import time
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ("title", "slides")
LINUX = platform.system() == "Linux"
TIME_COMMAND = ["/usr/bin/time", "-v" if LINUX else "-l"]
RSS_PATTERN = (r"Maximum resident set size \(kbytes\): (\d+)" if LINUX
               else r"(\d+)\s+maximum resident set size")
RSS_UNIT = 1024 if LINUX else 1


def load_builder():
    spec = importlib.util.spec_from_file_location("build_animation", ROOT / "tools/build_animation.py")
    builder = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(builder)
    return builder


def write_fixture(fixture, target):
    target.mkdir(parents=True, exist_ok=True)
    if fixture == "title":
        text = (ROOT / "test/growth-benchmark.tex").read_text()
        if "[vector]{beamer-floral-animation}" not in text:
            raise RuntimeError("test/growth-benchmark.tex no longer selects the vector backend")
        source = target / "dense.tex"
        source.write_text(text.replace("[vector]{beamer-floral-animation}",
                                       "[raster]{beamer-floral-animation}"))
    else:
        source = target / "slides.tex"
        source.write_text("\\def\\floralvariant{raster}\n\\input{test/size-benchmark.tex}\n")
    return source


def stage_of(command):
    return {"latexmk": "latex", "texlua": "export", "pdftocairo": "raster"}[command[0]]


def timed_run(original, steps, scratch):
    """Wrap subprocess.run so each builder step records its time and RSS."""
    def run(command, **kwargs):
        report = scratch / f"{threading.get_ident()}-{time.time_ns()}.txt"
        start = time.monotonic()
        try:
            return original([*TIME_COMMAND, "-o", str(report), *command], **kwargs)
        finally:
            seconds = time.monotonic() - start
            text = report.read_text() if report.exists() else ""
            match = re.search(RSS_PATTERN, text)
            steps.append({"stage": stage_of(command), "seconds": round(seconds, 3),
                          "rss": int(match[1]) * RSS_UNIT if match else 0})
    return run


def tree_size(path):
    total = 0
    for item in path.rglob("*"):
        try:
            total += item.stat().st_size if item.is_file() else 0
        except FileNotFoundError:
            pass
    return total


def measure(builder, source, outdir, args):
    steps = []
    peak = [0]
    stop = threading.Event()

    def sample_disk():
        while not stop.wait(0.5):
            peak[0] = max(peak[0], tree_size(outdir))

    outdir.mkdir(parents=True, exist_ok=True)
    scratch = outdir.parent / f"{outdir.name}-time"
    shutil.rmtree(scratch, ignore_errors=True)
    scratch.mkdir(parents=True)
    original = builder.subprocess.run
    builder.subprocess.run = timed_run(original, steps, scratch)
    sampler = threading.Thread(target=sample_disk)
    sampler.start()
    start = time.monotonic()
    try:
        builder.build(SimpleNamespace(source=source, outdir=outdir, engine=args.engine,
                                      dpi=args.dpi, jobs=args.jobs))
    finally:
        total = time.monotonic() - start
        stop.set()
        sampler.join()
        builder.subprocess.run = original
        shutil.rmtree(scratch, ignore_errors=True)
    peak[0] = max(peak[0], tree_size(outdir))
    return {"total_seconds": round(total, 3), "peak_disk_bytes": peak[0], "steps": steps}


def summarize(result):
    seconds = {}
    for step in result["steps"]:
        seconds[step["stage"]] = seconds.get(step["stage"], 0) + step["seconds"]
    latex = [step["seconds"] for step in result["steps"] if step["stage"] == "latex"]
    export = seconds.get("export", 0)
    return {"total": result["total_seconds"], "measure_latex": latex[0], "final_latex": sum(latex[1:]),
            "export": export, "raster_and_overhead": result["total_seconds"] - sum(latex) - export,
            "rss_mib": max(step["rss"] for step in result["steps"]) / 2**20,
            "disk_mib": result["peak_disk_bytes"] / 2**20}


def git_commit(path):
    return subprocess.check_output(["git", "-C", str(path), "rev-parse", "HEAD"], text=True).strip()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--engine", type=Path, required=True,
                        help="frozen tikz-flora tree; do not point this at a checkout under development")
    parser.add_argument("--outdir", type=Path, default=ROOT / "build/raster-measurements")
    parser.add_argument("--fixture", action="append", choices=FIXTURES,
                        help="measure only this fixture; may be repeated")
    parser.add_argument("--source", type=Path, help="measure this document instead of the fixtures")
    parser.add_argument("--dpi", type=int, default=144)
    parser.add_argument("--jobs", type=int, default=2)
    args = parser.parse_args()
    args.engine = args.engine.resolve()
    outdir = args.outdir.resolve()
    source_path = args.source.resolve() if args.source else None
    os.chdir(ROOT)
    builder = load_builder()
    if source_path:
        work = [(source_path.stem, source_path)]
    else:
        work = [(name, write_fixture(name, outdir / name / "source")) for name in args.fixture or FIXTURES]
    report = {"commit": git_commit(ROOT), "engine": args.engine.name, "dpi": args.dpi, "jobs": args.jobs,
              "platform": platform.platform(), "builds": {}}
    engine_ref = args.engine / "engine-commit.txt"
    if engine_ref.is_file():
        report["engine"] = engine_ref.read_text().strip()
    elif (args.engine / ".git").exists():
        report["engine"] = git_commit(args.engine)
    print(f"{'build':16}{'total':>9}{'latex1':>9}{'export':>9}{'raster+':>9}{'latex2':>9}{'RSS MiB':>9}{'disk MiB':>10}")
    for name, source in work:
        build_dir = outdir / name / "build"
        shutil.rmtree(build_dir, ignore_errors=True)
        for state in ("cold", "warm"):
            result = measure(builder, source, build_dir, args)
            result["summary"] = summarize(result)
            report["builds"][f"{name}-{state}"] = result
            row = result["summary"]
            print(f"{name + '-' + state:16}{row['total']:>9.1f}{row['measure_latex']:>9.1f}{row['export']:>9.1f}"
                  f"{row['raster_and_overhead']:>9.1f}{row['final_latex']:>9.1f}{row['rss_mib']:>9.1f}"
                  f"{row['disk_mib']:>10.1f}")
    outdir.mkdir(parents=True, exist_ok=True)
    (outdir / "results.json").write_text(json.dumps(report, indent=2) + "\n")


if __name__ == "__main__":
    main()
