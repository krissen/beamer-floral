# Development

For whoever builds, tests, measures or releases the package. Commit-message
conventions are in [CONTRIBUTING.md](../../CONTRIBUTING.md).

## Building and testing

```sh
latexmk -lualatex test/smoke.tex
```

CI checks out the pinned engine and builds the test documents, executable
documentation and integration fixtures with LuaLaTeX. The engine's own tests run in its
repository. The `tune` keys are validated by the engine against its tuner
index, so a typo names the key and its valid siblings.

Title, palette and stock-theme screenshots are exported from the visual
acceptance PDFs. Layout and density scenes come from the executable
documentation fixture `docs/src/showcase.tex`, which is also compiled in CI.

For visual acceptance across title lengths, themes and aspect ratios, use the
reusable [visual template](../../test/visual/README.md):

```sh
python3 tools/visual_suite.py --engine ../tikz-flora
```

This produces comparison PDFs, a page guide, contact sheets and build
diagnostics under `build/visual-review/`. Stock-theme warnings trigger matching
builds without floral to help identify regressions. Inspect the output before
approving changes; compilation success alone is insufficient.

Use `--screenshots docs/img` to refresh all documentation screenshots from
those acceptance and documentation PDFs. All example content is English.

To compare raster build cost, freeze an engine tree outside your working
checkout and run:

```sh
python3 tools/measure_raster_build.py --engine ../frozen-engine
```

This builds the dense title and slideshow fixtures cold and then warm, and
writes step times, memory and disk use to
`build/raster-measurements/results.json`.

## Checks

`.github/workflows/ci.yml` is the list of what is built and checked, and a
pull request must pass it. It checks out the engine at the revision in
`engine-ref.txt`; the `pre_compile` step runs the Lua and Python unit checks
in `test/` (after linking the engine's `lua/` directory as `./lua`), then every
document in `root_file` is compiled with LuaLaTeX, and the `post_compile`
step checks the logs and PDFs and builds the raster and GIF animations through
`tools/build_animation.py`. Run the same commands against your own engine
checkout, for example `TIKZFLORA=../tikz-flora latexmk -lualatex
test/smoke.tex`. CI skips changes that touch only `.md`, `.png` and `.jpg` files, and
does not build the manual: after changing `docs/beamer-floral.tex`, run
`latexmk -lualatex beamer-floral.tex` in `docs/`.

## Engine pin

`engine-ref.txt` names the tikz-flora commit the package is tested with. Every
"`<commit>` or later" requirement in the sources and documents names that
commit. `test/engine-pin.py` fails on a requirement that names another
commit, and when the number of requirements per file changes, so a moved pin
updates `engine-ref.txt` and all of them in one commit. Measured figures in
`docs/dev/performance.md` state the engine they were measured with.

## Tools

The scripts in `tools/`. `build_animation.py` is for users of raster and GIF
playback and is described in [Growing flora](../user/growth.md); the others are
for maintenance and measurement.

| Script | Use |
|---|---|
| `build_animation.py` | Builds a document with raster or GIF playback; runs `render_animation.lua` for the missing samples |
| `render_animation.lua` | Internal worker of the builder: exports only the missing raster samples and lists the GIFs |
| `check_growth_pdf.py` | Checks the PDF resource structure and runs the emitted animation clock |
| `check_gif_pdf.py` | Checks a PDF built with GIF playback (`--pages`, `--mode embedded` or `external`, `--reserved`); needs qpdf and Pillow |
| `check_growth_acrobat.applescript` | Opens a PDF in desktop Acrobat Reader to check playback progress and stopping (`osascript`) |
| `probe_pympress.py` | Runs pympress on a deck and records what its media overlays do |
| `make_growth_gif.py` | Renders the README's growth GIF from a built raster cache of `docs/src/growth-title.tex` |
| `visual_suite.py` | Compiles the visual template across themes and aspect ratios (see above) |
| `measure_reuse.py`, `measure_sizes.py`, `measure_raster_build.py` | Build times and file sizes; see [performance](performance.md) |
| `dist.py` | The standalone ZIP, below |
| `ctan.py` | The CTAN archive, below |

## Standalone bundle

Build a self-contained ZIP with its exact engine revision and verify its
extracted example without local development paths:

```sh
python3 tools/dist.py --engine /path/to/tikz-flora --test
```

The output is `build/beamer-floral.zip`. Unzip it, keep the supplied styles,
`beamer-floral.lua`, engine boot file and `lua/` beside your document, and
compile with LuaLaTeX. Both packages' licences and engine acknowledgements
are included. Publishing the archive is a separate step.

The CTAN-format archive is built the same way and nothing is uploaded:

```sh
python3 tools/ctan.py --engine /path/to/tikz-flora --test
```

The output is `build/ctan/beamer-floral.zip` (`--output` changes it).

## Releasing

A release is a version bump, a tag and three attached files. The steps below
follow `v0.1.0`; `tools/` builds the files.

1. **Version bump**, in one commit. The version and date stand in the three
   `\ProvidesPackage` lines (`beamer-floral.sty`, `beamerthemefloral.sty`,
   `beamer-floral-animation.sty`), in the title and date of
   `docs/beamer-floral.tex`, and in the archive name in the README's "From the
   release archive". `tools/ctan.py` reads the version from `beamer-floral.sty`.
   Search the repository for the old version to find any other place.
2. **Tag** the merged commit on `main` as `vX.Y.Z` (`v0.1.0` is a tag on the
   commit that prepared the announcement).
3. **Attach** to the GitHub release the three files `v0.1.0` carried. The README
   links to `beamer-floral-tour.pdf` through `releases/latest/download/`, so keep
   that name.

   | File | Built with |
   |---|---|
   | `beamer-floral-vX.Y.Z.zip` | `python3 tools/dist.py --engine /path/to/tikz-flora --output build/beamer-floral-vX.Y.Z.zip --test`; `--test` unpacks it without development paths and builds its examples, including the raster one (about 5 minutes) |
   | `beamer-floral-tour.pdf` | `latexmk -lualatex -outdir=build/tour docs/src/tour.tex` from the repository root (the build command stated in the tour's header); copy `build/tour/tour.pdf` under this name |
   | `growth-title.gif` | the README's image, `docs/img/growth-title.gif`: `python3 tools/build_animation.py --outdir build/title docs/src/growth-title.tex`, then `python3 tools/make_growth_gif.py --engine /path/to/tikz-flora --cache build/title/growth-title.floral-animation` (needs `magick` and `gifski`) |

   The engine revision of the archive is the one in `engine-ref.txt`. The
   CTAN archive (`tools/ctan.py`, above) is a separate step.
