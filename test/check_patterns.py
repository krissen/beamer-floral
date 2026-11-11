"""Check that pattern pages are painted, not blank, from the PDF itself.

Usage: check_patterns.py patterns.pdf

The log of test/patterns.tex only shows the reuse decisions. A reused drawing
once kept the whole text block clear and left a pattern page nearly empty
while the log looked right, so this renders each page at low resolution and
measures the ink. The text block is 2.5 cm from the left, 1 cm from the right
(the package defaults); the figures are the share of non-white pixels:
 - every page with a pattern has ink in the margins outside the text block,
   far above what an almost blank page gives;
 - frame 4 (outer=margin, hero=rosette) has a disc of ink in its top right
   corner;
 - frame 3 (pattern=none) is flora, so it is sparse but not empty.
"""
import subprocess
import sys
import tempfile
from pathlib import Path

pdf = Path(sys.argv[1])
DPI = 40
# Share of the margin area: a pattern fills it (0.41 painted, 0.08 when a
# reused drawing kept the text block clear); outer=margin leaves a margin.
MIN_MARGIN_INK = {"pattern": 0.25, "pattern+hero": 0.08}
MIN_HERO_INK = 0.15     # share of the top-right corner box
PAGES = {1: "pattern", 2: "pattern", 3: "flora", 4: "pattern+hero"}


def render(page, directory):
    stem = Path(directory) / f"p{page}"
    subprocess.check_call(["pdftoppm", "-r", str(DPI), "-f", str(page), "-l", str(page),
                           "-gray", "-singlefile", str(pdf), str(stem)])
    data = stem.with_suffix(".pgm").read_bytes()
    header, rest = data.split(b"\n255\n", 1)
    width, height = map(int, header.split()[1:3])
    return width, height, rest


def share(width, rows, x0, x1, y0, y1):
    count = dark = 0
    for y in range(y0, y1):
        row = rows[y * width:(y + 1) * width]
        for x in range(x0, x1):
            count += 1
            dark += row[x] < 235
    return dark / count if count else 0.0


errors = []
with tempfile.TemporaryDirectory() as directory:
    for page, kind in PAGES.items():
        width, height, rows = render(page, directory)
        left = int(2.5 / 2.54 * DPI)
        right = width - int(1 / 2.54 * DPI)
        # Margin area outside the text block, below the headline band.
        top = int(height * 0.12)
        ink = (share(width, rows, 0, left, top, height) * left
               + share(width, rows, right, width, top, height) * (width - right)
               + share(width, rows, left, right, int(height * 0.85), height) * (right - left) * 0.15)
        area = left + (width - right) + (right - left) * 0.15
        margin = ink / area
        print(f"frame {page} ({kind}): margin ink {margin:.3f}")
        if kind in MIN_MARGIN_INK and margin < MIN_MARGIN_INK[kind]:
            errors.append(f"frame {page}: a pattern page is almost blank outside the text block ({margin:.3f} ink, need {MIN_MARGIN_INK[kind]})")
        if kind == "flora" and margin <= 0:
            errors.append(f"frame {page}: the flora page is empty")
        if kind == "pattern+hero":
            corner = share(width, rows, int(width * 0.78), width, int(height * 0.12), int(height * 0.45))
            print(f"frame {page}: hero corner ink {corner:.3f}")
            if corner < MIN_HERO_INK:
                errors.append(f"frame {page}: no hero in the top right corner ({corner:.3f} ink, need {MIN_HERO_INK})")
if errors:
    raise SystemExit("\n".join(errors))
print("pattern pages are painted")
