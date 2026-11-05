"""Build a self-contained, deterministic ZIP; optionally test its extraction."""

import argparse
import io
import os
from pathlib import Path
import subprocess
import tarfile
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[1]


def build(engine, output):
    revision = (ROOT / "engine-ref.txt").read_text().strip()
    archive = subprocess.check_output(["git", "-C", str(engine), "archive", revision])
    files = {name: (ROOT / name).read_bytes() for name in (
        "beamer-floral.sty", "beamer-floral.lua", "beamerthemefloral.sty", "LICENSE", "engine-ref.txt"
    )}
    with tarfile.open(fileobj=io.BytesIO(archive)) as source:
        for member in source.getmembers():
            name = member.name
            if member.isfile() and (name.startswith("lua/") or name in (
                "tex/tikzflora.sty", "tex/tikzflora-boot.lua", "LICENSE", "README.md"
            )):
                target = name.removeprefix("tex/")
                if name in ("LICENSE", "README.md"):
                    target = "tikz-flora-" + name
                files[target] = source.extractfile(member).read()
    for required in ("tikzflora.sty", "tikzflora-boot.lua", "lua/flora/init.lua",
                     "tikz-flora-LICENSE"):
        if required not in files:
            raise RuntimeError(f"Engine archive is missing {required}")
    files["example.tex"] = br"""\documentclass[aspectratio=169]{beamer}
\usetheme{floral}
\florasetup{seed=3,density=1.2}
\title{Floral}\author{Your name}\date{}
\begin{document}
\begin{frame}[plain]\titlepage\end{frame}
\begin{frame}{A floral presentation}
\begin{itemize}\item Procedural watercolour margins.
\item Text and flora share a palette.\end{itemize}
\end{frame}
\end{document}
"""
    files["latexmkrc"] = b"$pdf_mode = 4;\n"
    files["README.md"] = ("""# beamer-floral standalone bundle

Requires LuaLaTeX (tested with TeX Live 2025). Unzip, enter this folder and run:

    latexmk -lualatex example.tex

Keep both theme styles, beamer-floral.lua, tikzflora.sty, tikzflora-boot.lua and lua/ beside your
document. No shell escape or development checkout is needed. In Overleaf,
upload the ZIP and select LuaLaTeX and example.tex as the main document.

Load the floral theme with \\usetheme{floral}. For an existing theme, load that
theme first and then \\usepackage{beamer-floral}. Choose a palette with
\\florapalette{warm}, blue, green or green-stems.

Flora stays fixed through a frame's overlays after geometry converges. Run
latexmk until rerun warnings clear. Change floral settings between frames.

beamer-floral is MIT licensed (LICENSE). Bundled tikz-flora retains its own
MIT licence and acknowledgements (tikz-flora-LICENSE, tikz-flora-README.md).
Engine revision: """ + revision + "\n").encode()
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as bundle:
        for name, data in sorted(files.items()):
            info = zipfile.ZipInfo("beamer-floral/" + name, (1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            bundle.writestr(info, data)
    print(f"Built {output} (engine {revision})")


def test(output):
    with tempfile.TemporaryDirectory(prefix="beamer-floral-dist-") as directory:
        with zipfile.ZipFile(output) as bundle:
            bundle.extractall(directory)
        env = dict(os.environ)
        for key in ("FLORA_LUA", "TIKZFLORA", "TEXINPUTS"):
            env.pop(key, None)
        subprocess.run(["latexmk", "-norc", "-lualatex", "-interaction=nonstopmode",
                        "-halt-on-error", "example.tex"],
                       cwd=Path(directory) / "beamer-floral", env=env, check=True)
    print("Extracted bundle compiled without development paths or latexmk config")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--engine", type=Path, required=True, help="local tikz-flora git repository")
    parser.add_argument("--output", type=Path, default=ROOT / "build/beamer-floral.zip")
    parser.add_argument("--test", action="store_true")
    args = parser.parse_args()
    build(args.engine, args.output)
    if args.test:
        test(args.output)
