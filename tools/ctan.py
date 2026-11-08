"""Build a CTAN-format archive of beamer-floral; nothing is uploaded."""

import argparse
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ("beamer-floral.sty", "beamer-floral-animation.sty", "beamerthemefloral.sty",
           "beamer-floral.lua", "beamer-floral-cache.lua", "beamer-floral-pdf.lua", "LICENSE")
TOOLS = ("tools/build_animation.py", "tools/render_animation.lua")


def version():
    text = (ROOT / "beamer-floral.sty").read_text()
    return re.search(r"ProvidesPackage\{beamer-floral\}\[\S+ (v[\d.]+)", text)[1]


def manual(work):
    """Compile the manual outside the source tree and return its PDF."""
    target = work / "manual"
    shutil.copytree(ROOT / "docs/img", target / "img")
    shutil.copy(ROOT / "docs/beamer-floral.tex", target)
    subprocess.run(["latexmk", "-lualatex", "-interaction=nonstopmode", "-halt-on-error",
                    "beamer-floral.tex"], cwd=target, check=True, stdout=subprocess.DEVNULL)
    return target / "beamer-floral.pdf"


README = """# beamer-floral

Version {version}. Procedural watercolour flora for beamer slides. Each frame
gets its own plant, and the stems grow around the measured text block.

Requires LuaLaTeX and tikz-flora, which is not on CTAN:
https://github.com/krissen/tikz-flora (branch beamer-floral, revision ff21877
or later). Timed growth also needs animate; raster playback needs Python 3.9
or later and Poppler when its cache is built.

- beamer-floral.pdf: the manual (source: beamer-floral.tex)
- beamer-floral-tour.tex: a complete example presentation
- build_animation.py, render_animation.lua: optional raster cache builder

Licence: MIT; see LICENSE.
Repository and issues: https://github.com/krissen/beamer-floral
"""


def build(output):
    with tempfile.TemporaryDirectory(prefix="floral-ctan-", dir=ROOT / "build") as directory:
        work = Path(directory)
        files = {name: (ROOT / name).read_bytes() for name in PACKAGE}
        for name in TOOLS:
            files[Path(name).name] = (ROOT / name).read_bytes()
        files["README.md"] = README.format(version=version()).encode()
        files["beamer-floral.tex"] = (ROOT / "docs/beamer-floral.tex").read_bytes()
        files["beamer-floral.pdf"] = manual(work).read_bytes()
        files["title.png"] = (ROOT / "docs/img/title.png").read_bytes()
        files["beamer-floral.tex"] = files["beamer-floral.tex"].replace(b"{img/title.png}", b"{title.png}")
        tour = (ROOT / "docs/src/tour.tex").read_bytes()
        files["beamer-floral-tour.tex"] = tour.replace(b"docs/img/stock-madrid.png", b"stock-madrid.png")
        files["stock-madrid.png"] = (ROOT / "docs/img/stock-madrid.png").read_bytes()
        output.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
            for name, data in sorted(files.items()):
                info = zipfile.ZipInfo("beamer-floral/" + name, (1980, 1, 1, 0, 0, 0))
                info.compress_type = zipfile.ZIP_DEFLATED
                info.external_attr = 0o100644 << 16
                archive.writestr(info, data)
    print(f"Built {output}: {len(files)} files, {output.stat().st_size} bytes")


def test(output, engine):
    with zipfile.ZipFile(output) as archive:
        names = archive.namelist()
        for name in names:
            parts = name.split("/")
            assert len(parts) == 2 and parts[0] == "beamer-floral", f"not flat: {name}"
            assert not parts[1].startswith("."), f"hidden file: {name}"
            assert not re.search(r"\.(aux|log|toc|out|nav|snm|fls|fdb_latexmk)$", name), f"generated: {name}"
        for required in ("README.md", "LICENSE", "beamer-floral.pdf", "beamer-floral.tex"):
            assert f"beamer-floral/{required}" in names, f"missing {required}"
        with tempfile.TemporaryDirectory(prefix="floral-ctan-test-", dir=ROOT / "build") as directory:
            archive.extractall(directory)
            unpacked = Path(directory) / "beamer-floral"
            env = dict(os.environ, TEXINPUTS=f"{unpacked}:{engine}/tex//:", FLORA_LUA=f"{engine}/lua")
            env.pop("TIKZFLORA", None)
            for document in ("beamer-floral.tex", "beamer-floral-tour.tex"):
                subprocess.run(["latexmk", "-norc", "-lualatex", "-interaction=nonstopmode",
                                "-halt-on-error", document], cwd=unpacked, env=env, check=True,
                               stdout=subprocess.DEVNULL)
    print("Archive layout passed; manual and tour compiled from the extracted package")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--engine", type=Path, required=True, help="local tikz-flora checkout")
    parser.add_argument("--output", type=Path, default=ROOT / "build/ctan/beamer-floral.zip")
    parser.add_argument("--test", action="store_true")
    args = parser.parse_args()
    build(args.output)
    if args.test:
        test(args.output, args.engine.resolve())
