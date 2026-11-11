"""Check the stage layout from a build log and its PDF.

Usage: check_stage.py stage.log stage.pdf

For every frame of test/stage.tex (and stage-43.tex) the log holds the
registers Beamer saw ("STAGE n textwidth=... left=... right=...") and the PDF
holds the words as typeset (stage-onlytext.tex: the class option onlytextwidth). Both must match the expected table: the document
margins (2 cm each side), the stage on either side with the default 0.39
paper width and 12 mm, an explicit width and margin, and the title and
section pages that keep the document margins unless they ask for the stage.
The words of a frame, its footnote and columns included, must lie inside the
text block and reach both its edges.
"""
import re
import subprocess
import sys
from pathlib import Path

log, pdf = Path(sys.argv[1]), Path(sys.argv[2])
info = subprocess.check_output(["pdfinfo", str(pdf)], text=True)
width_bp = float(re.search(r"Page size:\s+([\d.]+) x", info)[1])
width_mm = width_bp * 25.4 / 72
BP, TEXPT = 72 / 25.4, 72.27 / 25.4  # per mm
DOC = (20.0, 20.0)
STAGE = 0.39 * width_mm
# frame -> (left mm, right mm, kind)
EXPECTED = {
    1: (*DOC, "plain"),
    2: (12.0, STAGE, "content"),
    3: (*DOC, "plain"),
    4: (STAGE, 12.0, "content"),
    5: (*DOC, "title"),
    6: (*DOC, "section"),
    7: (STAGE, 12.0, "content"),
    8: (STAGE, 12.0, "title"),
    9: (*DOC, "plain"),
    10: (20.0, 50.0, "content"),
    11: (*DOC, "plain"),
    12: (20.0, 60.0, "content"),
    13: (*DOC, "spread"),
    14: (20.0, 50.0, "wide"),
}
# The class option onlytextwidth: stage=off must keep it on.
EXPECTED_ONLYTEXT = {
    1: (*DOC, "tight"),
    2: (12.0, STAGE, "tight"),
    3: (*DOC, "tight"),
    4: (STAGE, 12.0, "tight"),
    5: (*DOC, "tight"),
}
if "onlytext" in log.name:
    EXPECTED = EXPECTED_ONLYTEXT
TITLE_OFFSET_MM = 18.0  # \floratitleoffset

errors = []
chrome = {}  # marker word -> {frame: x of its left edge}


def fail(message):
    errors.append(message)


registers = {}
for m in re.finditer(r"STAGE (\d+) textwidth=([\d.]+)pt left=([\d.]+)pt right=([\d.]+)pt", log.read_text(errors="replace")):
    registers[int(m[1])] = tuple(float(m[i]) for i in (2, 3, 4))
gm = {int(m[1]): (float(m[2]), float(m[3])) for m in
      re.finditer(r"GM (\d+) gl=([\d.]+)pt gr=([\d.]+)pt", log.read_text(errors="replace"))}
if sorted(gm) != sorted(EXPECTED):
    fail(f"Gm@ margins logged for frames {sorted(gm)}, expected {sorted(EXPECTED)}")
if sorted(registers) != sorted(EXPECTED):
    fail(f"frames logged {sorted(registers)}, expected {sorted(EXPECTED)}")

for n, (left, right, kind) in sorted(EXPECTED.items()):
    if n not in registers:
        continue
    text_pt, left_pt, right_pt = registers[n]
    gl_pt, gr_pt = gm.get(n, (float('nan'), float('nan')))
    # geometry's \\Gm@lmargin and \\Gm@rmargin place Beamer's headline, footline,
    # canvas and sidebars: they must follow the margins (there are no sidebars).
    for name, got, want in (("Gm@lmargin", gl_pt, left_pt), ("Gm@rmargin", gr_pt, right_pt)):
        if abs(got - want) > 0.1:
            fail(f"frame {n}: {name} is {got:.2f}pt, expected {want:.2f}pt")
    page_pt = width_mm * TEXPT
    for name, got, want in (("left", left_pt, left * TEXPT), ("right", right_pt, right * TEXPT),
                            ("textwidth", text_pt, page_pt - (left + right) * TEXPT)):
        if abs(got - want) > 0.1:
            fail(f"frame {n}: {name} register {got:.2f}pt, expected {want:.2f}pt")
    words = subprocess.check_output(["pdftotext", "-f", str(n), "-l", str(n), "-bbox", str(pdf), "-"], text=True)
    allwords = re.findall(r'xMin="([-\d.]+)" yMin="([-\d.]+)" xMax="[-\d.]+" yMax="[-\d.]+">([^<]*)</word>', words)
    for mark in ("FOOTMARK", "Part"):  # footline marker, headline section name
        for x, y, w in allwords:
            # "Part" is also the title of the section page: the headline is the top strip.
            if w == mark and (mark == "FOOTMARK" or float(y) < 20):
                chrome.setdefault(mark, {})[n] = float(x)
    boxes = [(float(a), float(b), float(c), float(d), w) for a, b, c, d, w in
             re.findall(r'xMin="([-\d.]+)" yMin="([-\d.]+)" xMax="([-\d.]+)" yMax="([-\d.]+)">([^<]*)</word>', words)
             if float(b) >= 20 and w != "FOOTMARK"]  # a stray glyph above the page is not text
    if not boxes:
        fail(f"frame {n}: no words on page {n}")
        continue
    lo, hi = left * BP, width_bp - right * BP
    xmin = min(b[0] for b in boxes)
    xmax = max(b[2] for b in boxes)
    # "plain": a frame on the document margins with Beamer's default columns,
    # which spread over the slide and may leave the text block on either side:
    # only the registers are checked.
    if kind not in ("plain", "wide") and (xmin < lo - 0.5 and kind != "spread" or xmax > hi + 0.5):
        fail(f"frame {n}: words span {xmin:.1f}..{xmax:.1f}bp, outside the text block {lo:.1f}..{hi:.1f}bp")
    if kind == "content":
        if not lo - 0.5 <= xmin <= lo + 1.5:
            fail(f"frame {n}: text starts at {xmin:.1f}bp, expected the left margin {lo:.1f}bp")
        if xmax < hi - 20:
            fail(f"frame {n}: text ends at {xmax:.1f}bp and does not use the width up to {hi:.1f}bp")
    elif kind == "tight":
        # Columns that fill the text block exactly start at its left edge.
        if not lo - 0.5 <= xmin <= lo + 1.5:
            fail(f"frame {n}: columns start at {xmin:.1f}bp, expected the left margin {lo:.1f}bp")
    elif kind == "wide":
        # An explicit [totalwidth=...] wins over the stage's onlytextwidth, so
        # the columns run past the text block.
        if xmax < hi + 5:
            fail(f"frame {n}: columns end at {xmax:.1f}bp; the explicit totalwidth should reach beyond {hi:.1f}bp")
    elif kind == "spread":
        # Beamer's default: such columns spread over the whole slide, so the
        # left one starts left of the text block.
        if xmin > lo - 5:
            fail(f"frame {n}: columns start at {xmin:.1f}bp; expected them to spread left of {lo:.1f}bp")
    elif kind == "title":
        title = [b for b in boxes if b[4] == "Stage"]
        if len(title) != 1:
            fail(f"frame {n}: expected one title word")
        else:
            centre = (title[0][0] + title[0][2]) / 2
            want = lo + (TITLE_OFFSET_MM * BP + (hi - lo)) / 2
            if abs(centre - want) > 2:
                fail(f"frame {n}: title centred at {centre:.1f}bp, expected {want:.1f}bp")

# The headline and the footline are drawn from the page edge, outside the text
# block: wherever a frame puts the stage, they stay where the frames on the
# document margins have them.
for mark, where in sorted(chrome.items()):
    ref = [x for n, x in where.items() if EXPECTED[n][:2] == DOC and EXPECTED[n][2] != "plain"]
    if not ref or len(where) < 3:
        fail(f"{mark} found on {sorted(where)}; needs a frame on the document margins and several frames")
        continue
    for n, x in sorted(where.items()):
        if abs(x - ref[0]) > 1.0:
            fail(f"frame {n}: {mark} at {x:.1f}bp, {ref[0]:.1f}bp on the document margins")

if errors:
    raise SystemExit("\n".join(errors))
print(f"stage layout checked on {len(EXPECTED)} frames ({log.name}, {width_bp:.0f}bp wide)")
