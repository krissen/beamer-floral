"""Every "<revision> or later" engine requirement must name the pinned engine.

Package requirements follow engine-ref.txt. Floors for a single optional
feature may name an older revision; list them in FEATURE_FLOORS, and keep
each one an ancestor of the pin.
"""

from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[1]
PIN = (ROOT / "engine-ref.txt").read_text().strip()
FEATURE_FLOORS = {
    ("README.md", "28c394a"),  # optional ornament templates
}
REQUIREMENT = re.compile(r"\b([0-9a-f]{7,40})\b[`}\s]*\s+or\s+later")

files = subprocess.check_output(["git", "-C", str(ROOT), "ls-files"], text=True).split()
found = 0
stale = []
for name in files:
    path = ROOT / name
    if path.suffix not in {".sty", ".tex", ".lua", ".py", ".md"} or path.is_symlink():
        continue
    text = path.read_text(errors="replace")
    for match in REQUIREMENT.finditer(text):
        found += 1
        if (name, match[1]) in FEATURE_FLOORS:
            continue
        if not PIN.startswith(match[1]):
            line = text.count("\n", 0, match.start()) + 1
            stale.append(f"{name}:{line}: {match[1]} is not the pinned engine {PIN[:7]}")
if stale:
    raise SystemExit("\n".join(stale))
if found < 6:
    raise SystemExit(f"expected at least 6 engine requirements, found {found}")
print(f"{found} engine requirements name the pinned engine {PIN[:7]}")
