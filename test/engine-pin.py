"""Every "<revision> or later" engine requirement must name the pinned engine.

Package requirements follow engine-ref.txt. A floor for a single optional
feature may name an older revision when it is listed in FEATURE_FLOORS.
EXPECTED counts the requirements per file, so a requirement that is reworded
past the pattern, or added in a new place, fails here and gets looked at.
"""

from collections import Counter
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[1]
PIN = (ROOT / "engine-ref.txt").read_text().strip()
SUFFIXES = {".sty", ".tex", ".lua", ".py", ".md", ".yml", ".txt", ".cjs"}
REQUIREMENT = re.compile(r"\b([0-9a-f]{7,40})\b[`}\s]*\s+or\s+(?:later|newer)")
FEATURE_FLOORS = {
    ("docs/user/ornaments.md", "28c394a"),  # optional ornament templates
}
EXPECTED = Counter({
    "README.md": 1,
    "docs/user/ornaments.md": 1,
    "beamer-floral.sty": 3,
    "docs/beamer-floral.tex": 1,
    "tools/ctan.py": 1,
})

files = subprocess.check_output(["git", "-C", str(ROOT), "ls-files"], text=True).split()
found = Counter()
used_floors = set()
errors = []
for name in files:
    path = ROOT / name
    if path.suffix not in SUFFIXES or path.is_symlink() or name == "test/engine-pin.py":
        continue
    text = path.read_text(errors="replace")
    for match in REQUIREMENT.finditer(text):
        found[name] += 1
        line = text.count("\n", 0, match.start()) + 1
        if (name, match[1]) in FEATURE_FLOORS:
            used_floors.add((name, match[1]))
        elif not PIN.startswith(match[1]):
            errors.append(f"{name}:{line}: {match[1]} is not the pinned engine {PIN[:7]}")
for floor in sorted(FEATURE_FLOORS - used_floors):
    errors.append(f"{floor[0]}: feature floor {floor[1]} is listed but no longer present")
if found != EXPECTED:
    errors.append(f"engine requirements per file changed: expected {dict(EXPECTED)}, found {dict(found)}")
if errors:
    raise SystemExit("\n".join(errors))
print(f"{sum(found.values())} engine requirements checked against the pinned engine {PIN[:7]}")
