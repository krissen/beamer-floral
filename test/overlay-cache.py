"""Static overlay frames are drawn from the page cache across compiles.

Run: python3 test/overlay-cache.py /path/to/tikz-flora

Compiles test/overlay-cache.tex once to fill the caches, then compiles each
variant below from a copy of those caches, pass by pass until LaTeX asks for
no rerun. A frame counts as a hit when every pass drew it from the cache,
and as a miss when some pass had to grow it. Any change that alters a
frame's drawing must miss; an overlay count that leaves the merged geometry
unchanged leaves the drawing unchanged, so it must hit.

The hit/miss status alone cannot show that a hit served the right drawing:
a frame whose first overlay misses on the engine path counts as a miss even
when its static drawing was served stale. So each variant is also built cold,
in an empty output directory, and its warm pages must match the cold pages
pixel for pixel.
"""

import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
FRAMES = 5
DPI = 40
RERUN = re.compile(r"Rerun\s+to\s+get")
# Each frame logs its reuse decision before its first page; every cache line
# after it, from the engine path or the static drawing, belongs to that frame.
FRAME = re.compile(r"^beamer-floral: frame (\d+) class ")
CACHE = re.compile(r"^(?:flora: page \d+|beamer-floral: frame \d+ static flora) "
                   r"(from the cache|grown and cached|painted)")

# name: (switches, expected status of frames 1-5; 4 is on the stage, 5 is not)
VARIANTS = {
    "unchanged": ({}, "HHHHH"),
    "changed text": ({"octext": "Second, changed"}, "MHHHH"),
    "frame setting": ({"ocsetting": r"\florathisframe{gilt=vector}"}, "MHHHH"),
    "document setting": ({"ocdensity": "0.25"}, "MMMMM"),
    "overlay count, new geometry": ({"octhird": r"\pause\par Third"}, "MHHHH"),
    "overlay count, same geometry": ({"occount": "3"}, "HHHHH"),
    # The stage keys are document settings, which the engine's cache key
    # covers whole, so changing one misses every frame, though only the stage
    # frame's geometry changes. Correct, if conservative.
    "stage width": ({"ocstagesetting": r"\florasetup{stage width=50mm}"}, "MMMMM"),
    "stage margin": ({"ocstagesetting": r"\florasetup{stage margin=20mm}"}, "MMMMM"),
    # Document-level stage=left stages frames 1-3 and 5; frame 4 asks for the right.
    "stage left": ({"ocstagesetting": r"\florasetup{stage=left}"}, "MMMHM"),
}

# Variants whose changed frame must be grown exactly once on the first
# compile, however many overlays it has: frame number -> count. The frame
# override lives for the first overlay only, so every overlay's drawing must
# be keyed on the settings the frame started with.
GROWN_ONCE = {"frame setting": {1: 1}}


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


def grown_counts(logs):
    """How many times each frame was grown and cached, over all passes."""
    grown = {frame: 0 for frame in range(1, FRAMES + 1)}
    for log in logs:
        frame = None
        for line in log.splitlines():
            if m := FRAME.match(line):
                frame = int(m.group(1))
            elif (m := CACHE.match(line)) and frame in grown and m.group(1) == "grown and cached":
                grown[frame] += 1
    return grown


def pages(out, name):
    """The PDF's pages as raw RGB rasters, in page order."""
    prefix = out / f"{name}-page"
    subprocess.run(["pdftoppm", "-r", str(DPI), str(out / "d.pdf"), str(prefix)], check=True)
    result = []
    for ppm in sorted(out.glob(f"{name}-page-*.ppm"), key=lambda p: int(p.stem.rsplit("-", 1)[1])):
        data = ppm.read_bytes()
        # P6 header: magic, width, height, maximum value, then one whitespace byte.
        fields = data.split(maxsplit=4)
        assert fields[0] == b"P6" and fields[3] == b"255", ppm
        result.append((int(fields[1]), int(fields[2]), fields[4]))
    return result


def differing_pixels(warm, cold):
    """Differing pixels per page; None when the page counts or sizes differ."""
    if len(warm) != len(cold) or any(w[:2] != c[:2] for w, c in zip(warm, cold)):
        return None
    counts = []
    for (_, _, a), (_, _, b) in zip(warm, cold):
        counts.append(0 if a == b else sum(a[i:i + 3] != b[i:i + 3] for i in range(0, len(a), 3)))
    return counts


def main():
    engine = Path(sys.argv[1]).resolve()
    env = dict(os.environ, LC_ALL="C", FLORA_LUA=f"{engine}/lua", TEXINPUTS=f"{ROOT}:{engine}/tex//:")
    failures = []
    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp) / "base"
        base.mkdir()
        (base / "d.tex").write_text(source({}))
        compile_passes(base, env)
        base_pages = pages(base, "base")
        # Frames 4 and 5 have the same text; the stage gives them different
        # geometry, so their first overlay pages must differ.
        if len(base_pages) != 10 or base_pages[6][2] == base_pages[8][2]:
            sys.exit("the stage frame and the document-margin frame with the same text look alike")
        for name, (switches, expected) in VARIANTS.items():
            slug = re.sub(r"\W+", "-", name)
            out = Path(tmp) / slug
            shutil.copytree(base, out)
            (out / "d.tex").write_text(source(switches))
            logs = compile_passes(out, env)
            got = statuses(logs)
            grown = grown_counts(logs)
            wanted = GROWN_ONCE.get(name, {})
            grown_ok = all(grown[f] == n for f, n in wanted.items())
            # The cold build of the unchanged deck is the base build itself.
            if switches:
                cold = Path(tmp) / f"{slug}-cold"
                cold.mkdir()
                (cold / "d.tex").write_text(source(switches))
                compile_passes(cold, env)
                cold_pages = pages(cold, "cold")
            else:
                cold_pages = base_pages
            diff = differing_pixels(pages(out, "warm"), cold_pages)
            ok = got == expected and grown_ok and diff is not None and not any(diff)
            pixels = "page count or size differs" if diff is None else f"warm vs cold {sum(diff)} px"
            print(f"{'PASS' if ok else 'FAIL'} {name}: frames {got}, expected {expected}; {pixels}"
                  + "".join(f"; frame {f} grown {grown[f]}x (want {n})" for f, n in wanted.items()))
            if not ok:
                failures.append(name)
    if failures:
        sys.exit(f"{len(failures)} variant(s) failed: {', '.join(failures)}")
    print("overlay cache tests passed")


if __name__ == "__main__":
    main()
