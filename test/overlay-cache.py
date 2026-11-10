"""Static overlay frames are drawn from the page cache across compiles.

Run: python3 test/overlay-cache.py /path/to/tikz-flora

Compiles test/overlay-cache.tex once to fill the caches, then compiles each
variant below from a copy of those caches, pass by pass until LaTeX asks for
no rerun. A frame counts as a hit when every pass drew it from the cache,
and as a miss when some pass had to grow it. Any change that alters a
frame's drawing must miss; an overlay count that leaves the merged geometry
unchanged leaves the drawing unchanged, so it must hit.
"""

import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
FRAMES = 3
RERUN = re.compile(r"Rerun\s+to\s+get")
# Each frame logs its reuse decision before its first page; every cache line
# after it, from the engine path or the static drawing, belongs to that frame.
FRAME = re.compile(r"^beamer-floral: frame (\d+) class ")
CACHE = re.compile(r"^(?:flora: page \d+|beamer-floral: frame \d+ static flora) "
                   r"(from the cache|grown and cached|painted)")

# name: (switches, expected status of frames 1-3)
VARIANTS = {
    "unchanged": ({}, "HHH"),
    "changed text": ({"octext": "Second, changed"}, "MHH"),
    "frame setting": ({"ocsetting": r"\florathisframe{gilt=vector}"}, "MHH"),
    "document setting": ({"ocdensity": "0.25"}, "MMM"),
    "overlay count, new geometry": ({"octhird": r"\pause\par Third"}, "MHH"),
    "overlay count, same geometry": ({"occount": "3"}, "HHH"),
}


def source(switches):
    defs = "".join(f"\\def\\{k}{{{v}}}" for k, v in switches.items())
    return defs + "\\input{test/overlay-cache.tex}\n"


def compile_passes(out, env):
    """Run LuaLaTeX until it asks for no rerun; return each pass's log."""
    logs = []
    for _ in range(5):
        run = subprocess.run(["lualatex", "-interaction=nonstopmode", "-halt-on-error", "d.tex"],
                             cwd=out, env=env, capture_output=True, text=True)
        log = (out / "d.log").read_text(errors="replace")
        if run.returncode != 0:
            sys.exit(f"lualatex failed in {out}:\n" + log[-3000:])
        logs.append(log)
        if not RERUN.search(log):
            return logs
    sys.exit(f"{out}: no stable result after 5 passes")


def statuses(logs):
    """H when every pass drew the frame from the cache, M when one grew it."""
    seen = {frame: [] for frame in range(1, FRAMES + 1)}
    for log in logs:
        frame = None
        for line in log.splitlines():
            if m := FRAME.match(line):
                frame = int(m.group(1))
            elif (m := CACHE.match(line)) and frame in seen:
                seen[frame].append(m.group(1))
    result = ""
    for frame, found in seen.items():
        if len(found) < len(logs):
            sys.exit(f"frame {frame} logged no cached drawing in some pass; is the page cache in use?")
        if "painted" in found:
            sys.exit(f"frame {frame} was painted without the page cache")
        result += "H" if all(s == "from the cache" for s in found) else "M"
    return result


def main():
    engine = Path(sys.argv[1]).resolve()
    env = dict(os.environ, LC_ALL="C", FLORA_LUA=f"{engine}/lua", TEXINPUTS=f"{ROOT}:{engine}/tex//:")
    failures = []
    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp) / "base"
        base.mkdir()
        (base / "d.tex").write_text(source({}))
        compile_passes(base, env)
        for name, (switches, expected) in VARIANTS.items():
            out = Path(tmp) / re.sub(r"\W+", "-", name)
            shutil.copytree(base, out)
            (out / "d.tex").write_text(source(switches))
            got = statuses(compile_passes(out, env))
            ok = got == expected
            print(f"{'PASS' if ok else 'FAIL'} {name}: frames {got}, expected {expected}")
            if not ok:
                failures.append(name)
    if failures:
        sys.exit(f"{len(failures)} variant(s) failed: {', '.join(failures)}")
    print("overlay cache tests passed")


if __name__ == "__main__":
    main()
