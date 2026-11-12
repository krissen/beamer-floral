"""A reused frame asks for a rerun if and only if its running-head marks change.

Builds a small deck of reused frames until it converges, then applies one
edit at a time and compiles once. That compile must ask for a rerun
("Floral geometry or overlay count changed") exactly when the converged
marks of the edited deck (each mark's kind, box and rule, as
test/reuse-mark.lua logs them) differ from the original deck's, or the
edit adds an overlay, whose count asks for a rerun of its own. After the
edited deck converges, one more compile must ask for nothing.

    python3 test/rerun-marks.py [--reuse all,content] [--header margin,body]
        [--outdir DIR] [--tree DIR] [--table]

--tree compiles another checkout of the theme with this deck (the marks are
then logged by this checkout's test/reuse-mark.lua); --table prints the
table and does not fail. TIKZFLORA, or TEXINPUTS and FLORA_LUA, select the
engine as for any build.
"""

import argparse
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOGGER = ROOT / "test" / "reuse-mark.lua"
WARNING = "Floral geometry or overlay count changed"

DECK = r"""
\providecommand\floralreuse{all}
\providecommand\floralheader{margin}
\providecommand\TitleA{A title}
\providecommand\SubA{}
\providecommand\BodyA{Body text on the frame.}
\providecommand\BelowA{}
\providecommand\TopA{The first line of a frame set at the top.}
\providecommand\BesideA{A line beside the reserve.}
\providecommand\PauseA{}
\documentclass[aspectratio=169]{beamer}
\usetheme{floral}
\edef\next{\noexpand\florasetup{seed=3, density=0.25, cache=false,
  reuse={\floralreuse}, header=\floralheader}}\next
\directlua{dofile([[LOGGER]])}
\begin{document}
\begin{frame}{\TitleA}\SubA\BodyA\BelowA\end{frame}
\begin{frame}[t]\TopA\par More body text.\end{frame}
\florareserve{0pt}{\the\dimexpr\paperheight-1.2cm\relax}{\the\dimexpr 3cm\relax}{\the\paperheight}
\begin{frame}\BesideA\end{frame}
\floraclearreserve
\begin{frame}{Overlays}First\PauseA\end{frame}
\end{document}
"""

# Each edit redefines one macro of the deck. An added overlay changes the
# frame's overlay count, which asks for a rerun of its own (as on main).
OVERLAY_EDITS = {"overlay added"}
EDITS = [
    # The same letters again: a wider title whose ink is as tall.
    ("title longer on one line", r"\def\TitleA{A title A title A title}"),
    ("title wrapping to two lines",
     r"\def\TitleA{A title long enough that it has to wrap onto a second line of the frame title}"),
    ("subtitle added", r"\def\SubA{\framesubtitle{A subtitle under the title}}"),
    ("first body line longer", r"\def\BodyA{Body text on the frame, now running a good deal longer than before.}"),
    ("body text added below", r"\def\BelowA{\par More body text added below.\par And another line.}"),
    ("[t] frame's first line longer", r"\def\TopA{The first line of a frame set at the top, now a good deal longer.}"),
    ("line beside a reserve longer", r"\def\BesideA{A line beside the reserve, now running a good deal longer.}"),
    ("overlay added", r"\def\PauseA{\pause\par Second}"),
    ("title ink top moved (accent)", r"\def\TitleA{\'Etude title}"),
]

MARK = re.compile(r"bf test: frame (\d+) stage \d+ mark (\S+) +(\S+) +(\S+) +(\S+) +(\S+)")
RULE = re.compile(r"bf rule: frame (\d+) (\S+) (\S+) (\S+)")


def read_log(path):
    text = path.read_text(errors="replace")
    # TeX wraps long lines; a warning may be split anywhere.
    return text, text.replace("\n", "")


def marks(text):
    out = set()
    for line in text.splitlines():
        m = MARK.search(line)
        if m:
            out.add(("mark",) + m.groups())
        r = RULE.search(line)
        if r:
            out.add(("rule",) + r.groups())
    return frozenset(out)


def environment():
    env = dict(os.environ)
    flora = env.get("TIKZFLORA")
    if flora:
        env["TEXINPUTS"] = f"{flora}/tex//:" + env.get("TEXINPUTS", "")
        env["FLORA_LUA"] = f"{flora}/lua"
    return env


ENV = environment()


def lualatex(tree, outdir, source):
    subprocess.run(["lualatex", "-interaction=nonstopmode", "-halt-on-error", "-jobname=deck",
                    f"-output-directory={outdir}", str(source)],
                   cwd=tree, env=ENV, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
    return read_log(outdir / "deck.log")


def converge(tree, outdir, source):
    subprocess.run(["latexmk", "-lualatex", "-interaction=nonstopmode", "-halt-on-error", "-jobname=deck",
                    f"-outdir={outdir}", str(source)],
                   cwd=tree, env=ENV, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
    text, flat = lualatex(tree, outdir, source)
    return text, WARNING in flat


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--reuse", default="all,content")
    ap.add_argument("--header", default="margin,body")
    ap.add_argument("--outdir", default=str(ROOT / "build" / "rerun-marks"))
    ap.add_argument("--tree", default=str(ROOT))
    ap.add_argument("--table", action="store_true")
    args = ap.parse_args()
    tree, work = Path(args.tree), Path(args.outdir).resolve()
    shutil.rmtree(work, ignore_errors=True)
    work.mkdir(parents=True)
    deck = work / "deck.tex"
    deck.write_text(DECK.replace("LOGGER", str(LOGGER)))
    failures, rows = [], []
    for reuse in args.reuse.split(","):
        for header in args.header.split(","):
            config = f"reuse={reuse}, {header}"
            prefix = f"\\def\\floralreuse{{{reuse}}}\\def\\floralheader{{{header}}}"
            base_src = work / f"base-{reuse}-{header}.tex"
            base_src.write_text(f"{prefix}\n\\input{{{deck}}}\n")
            base_dir = work / f"base-{reuse}-{header}"
            base_dir.mkdir()
            base_text, loud = converge(tree, base_dir, base_src)
            if loud:
                failures.append(f"{config}: the unedited deck does not converge")
            before = marks(base_text)
            for n, (name, edit) in enumerate(EDITS, 1):
                src = work / f"edit{n}-{reuse}-{header}.tex"
                src.write_text(f"{prefix}{edit}\n\\input{{{deck}}}\n")
                out = work / f"edit{n}-{reuse}-{header}"
                shutil.copytree(base_dir, out)
                # The edited source keeps the base job's name, cache and aux files.
                _, flat = lualatex(tree, out, src)
                rerun = WARNING in flat
                after_text, still = converge(tree, out, src)
                changed = marks(after_text) != before
                rows.append((config, name, rerun, changed, still))
                expected = changed or name in OVERLAY_EDITS
                if rerun != expected:
                    failures.append(f"{config}, {name}: rerun requested {rerun}, marks changed {changed}")
                if still:
                    failures.append(f"{config}, {name}: still asks for a rerun after converging")
    width = max(len(r[1]) for r in rows)
    print(f"{'config':<20} {'edit':<{width}}  rerun  marks changed  converged quiet")
    for config, name, rerun, changed, still in rows:
        print(f"{config:<20} {name:<{width}}  {'yes' if rerun else 'no ':<5}  {'yes' if changed else 'no':<13}  {'no' if still else 'yes'}")
    if failures and not args.table:
        sys.exit("\n".join(failures))
    print(f"{len(rows)} edits checked" + ("" if args.table else ": a rerun is requested exactly when the marks change"))


if __name__ == "__main__":
    main()
