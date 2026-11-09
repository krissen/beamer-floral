"""Render the README's growth GIF from a built raster cache of growth-title.tex.

Build the cache first:
    python3 tools/build_animation.py --outdir build/title docs/src/growth-title.tex
"""

import argparse
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
(ROOT / "build").mkdir(exist_ok=True)


def run(command, **kwargs):
    subprocess.run(command, check=True, stdout=subprocess.DEVNULL, **kwargs)


def text_layer(engine, work):
    """The title page without flora, as a transparent PNG at the sample resolution."""
    env = dict(os.environ, TIKZFLORA=str(engine))
    out = work / "text"
    run(["latexmk", "-g", "-lualatex", "-interaction=nonstopmode", "-halt-on-error",
         r"-usepretex=\AtBeginDocument{\floraoff}", f"-outdir={out}", "docs/src/growth-title.tex"],
        cwd=ROOT, env=env)
    target = work / "text-layer"
    run(["pdftocairo", "-png", "-transp", "-singlefile", "-r", "144",
         str(out / "growth-title.pdf"), str(target)])
    return target.with_suffix(".png")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--engine", type=Path, required=True)
    parser.add_argument("--cache", type=Path, required=True,
                        help="the build's growth-title.floral-animation directory")
    parser.add_argument("--output", type=Path, default=ROOT / "docs/img/growth-title.gif")
    parser.add_argument("--width", type=int, default=720)
    parser.add_argument("--fps", type=int, default=10)
    parser.add_argument("--hold", type=int, default=25, help="frames to hold the finished page")
    args = parser.parse_args()
    samples = next(args.cache.glob("*-144"))
    ordered = sorted(samples.glob("sample-*.png"), key=lambda p: int(p.stem.split("-")[1]))
    # The cache is sampled at 20 fps; the GIF keeps the same eight-second pace.
    chosen = ordered[::max(1, round(20 / args.fps))]
    work = Path(tempfile.mkdtemp(prefix="floral-gif-", dir=ROOT / "build"))
    try:
        text = text_layer(args.engine.resolve(), work)
        frames = []
        for index, sample in enumerate(chosen + [chosen[-1]] * args.hold):
            frame = work / f"frame-{index:04d}.png"
            run(["magick", str(sample), "-background", "white", "-alpha", "remove",
                 str(text), "-composite", "-resize", f"{args.width}x", str(frame)])
            frames.append(str(frame))
        run(["gifski", "--fps", str(args.fps), "--quality", "75", "--width", str(args.width),
             "-o", str(args.output), *frames], stderr=subprocess.DEVNULL)
    finally:
        shutil.rmtree(work, ignore_errors=True)
    print(f"{args.output}: {args.output.stat().st_size} bytes, {len(frames)} frames")


if __name__ == "__main__":
    main()
