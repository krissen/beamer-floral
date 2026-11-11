"""A pattern on the stage must fill the wide margin and leave the text column.

Usage: check_stage_pattern.py stage-pattern.pdf

Renders the page at low resolution and measures the share of non-white
pixels in the stage (right of the text block, which ends 0.39 of the paper
width from the right edge) and in the text column (between the 12 mm margin
and the stage), below the headline band.
"""
import subprocess
import sys
import tempfile
from pathlib import Path

pdf = Path(sys.argv[1])
DPI = 40
with tempfile.TemporaryDirectory() as directory:
    stem = Path(directory) / "p"
    subprocess.check_call(["pdftoppm", "-r", str(DPI), "-gray", "-singlefile", str(pdf), str(stem)])
    header, rows = stem.with_suffix(".pgm").read_bytes().split(b"\n255\n", 1)
width, height = map(int, header.split()[1:3])


def share(x0, x1, y0, y1):
    dark = sum(rows[y * width + x] < 235 for y in range(y0, y1) for x in range(x0, x1))
    return dark / ((x1 - x0) * (y1 - y0))


stage_x = int(width * 0.61) + 2
top, bottom = int(height * 0.12), height
stage = share(stage_x, width, top, bottom)
column = share(int(12 / 25.4 * DPI) + 2, stage_x - 2, top, bottom)
print(f"stage ink {stage:.3f}, text column ink {column:.3f}")
errors = []
if stage < 0.25:
    errors.append(f"the pattern does not fill the stage ({stage:.3f} ink, need 0.25)")
if column > 0.10:
    errors.append(f"the pattern runs into the text column ({column:.3f} ink, at most 0.10)")
if errors:
    raise SystemExit("\n".join(errors))
print("the pattern fills the stage and leaves the text column")
