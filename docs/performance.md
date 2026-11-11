# Performance

Build times and file sizes for beamer-floral, with the method that produced
them and the commands to repeat each table. The headline figures in the
[README](../README.md) link here.

Flora is detailed artwork, so a deck with flora is slower to build and far
larger than plain Beamer. Three things bring that down: `reuse` (one drawing
per page class), a `pattern` (small vector pages), and `growth=off` (no
per-stage drawings). The tables below show by how much.

## Method

All figures were measured with TeX Live 2025 and tikz-flora `60a153d`, the
engine pin of the theme at the time. The machine was shared, so times carry
some noise; file sizes do not depend on load.

**Warm and cold.** A cold build starts from an empty output directory. A warm
build is a second full `latexmk` compile of the unchanged document with the
flora caches kept: everything but `<job>-flora/` and `<job>.floral-cache` is
deleted first, so every pass runs again with the cache from the first compile
in place. Adaptive frames are read back from the cache as well, which is why
a warm adaptive build is much closer to a warm `reuse` build than a cold one.

**Benchmark documents.**

- `test/reuse-benchmark.tex` for the build-time tables: 16:9, floral theme,
  with a chosen number of frames and overlays per frame, and optionally a
  section page every few frames. The four decks below are 10 frames of two
  overlays (21 pages), 40 frames of one overlay (41 pages), 30 frames of
  three overlays (91 pages) and the same with 6 section pages (97 pages).
  The pattern decks use `PATTERN=asanoha` and no `reuse`.
- `test/size-benchmark.tex` for the file-size table: a title page and ten
  frames of two overlays, 21 PDF pages, with identical content in each
  variant. Timed variants use the defaults of 8 seconds and 20 fps, and
  raster samples are 144 dpi.

**Each figure is a range** over two passes of the builds. The 1-minute load
average at the start of the builds was 3.3-26.7 (5.1-26.7 for the pattern
table), even with the other heavy jobs paused. The 97-page `reuse=content`
warm range is wide because one of its three runs (30.7 s) started as the
load climbed; the three runs gave 30.7 s, 12.5 s and 17.9 s.

## Build times: adaptive and `reuse`

Flora normally adapts to each frame; `reuse` draws one picture per page class
(see [Reusing one drawing](../README.md#reusing-one-drawing)). Each cell is
the build time and the PDF size.

Warm builds:

| Deck | Adaptive | `reuse=content` | `reuse=all` |
|---|---:|---:|---:|
| Title and 10 frames of two overlays, 21 pages | 3.8-4.4 s, 21.5 MB | | 3.8-3.9 s, 3.3 MB |
| Title and 40 one-overlay frames, 41 pages | 4.6-5.2 s, 62.0 MB | 4.2-4.4 s, 8.5 MB | 4.2-4.3 s, 3.3 MB |
| Title and 30 frames of three overlays, 91 pages | 5.9-6.2 s, 48.8 MB | | 5.5-5.8 s, 3.3 MB |
| As above with 6 section pages, 97 pages | 23.2-25.7 s, 57.0 MB | 12.5-30.7 s, 16.7 MB | 12.8-13.8 s, 4.6 MB |

Cold builds, adaptive against `reuse=all`:

| Deck | Adaptive | `reuse=all` |
|---|---:|---:|
| 21 pages | 14.3-16.2 s | 5.4 s |
| 41 pages | 36.6-42.3 s | 5.7-5.9 s |
| 91 pages | 33.4-36.5 s | 7.1-7.8 s |
| 97 pages | 76.1-89.9 s | 14.7-16.0 s |

Baselines: Beamer without floral takes 3.3-3.4 s on the 21-page deck, and the
97-page deck takes 12.4-13.8 s with flora off.

## Build times: flora and patterns

A pattern page is a small vector drawing, so the file stays small without
`reuse` (see [Patterns](../README.md#patterns)). Cold builds, with the PDF
size:

| Deck | Flora | `pattern=asanoha` |
|---|---:|---:|
| Title and 10 frames of two overlays, 21 pages | 14.3-16.2 s, 21.5 MB | 4.4-4.5 s, 0.18 MB |
| Title and 40 one-overlay frames, 41 pages | 36.6-42.3 s, 62.0 MB | 5.6 s, 0.65 MB |
| Title and 30 frames of three overlays, 6 section pages, 97 pages | 76.1-89.9 s, 57.0 MB | 29.9-35.8 s, 0.72 MB |

## File size

Overlays of a static frame share one copy of the flora; growing flora needs a
separate drawing for each stage. The document is the 21-page one described
under Method.

| Variant | PDF size |
|---|---:|
| Beamer without floral | 0.05 MB |
| `growth=off` | 21.5 MB |
| `growth=overlays` | 47.5 MB |
| `growth=timed`, vector | 89.4 MB |
| `growth=timed`, raster | 113.4 MB |

Your own figures will depend on the density, layout and number of pages. A
raster build also keeps its sample cache on disk, 109 MB for this document.
Share a talk with `\florasetup{growth=off}` if size matters more than the
animation.

## Repeating the measurements

The tools write under `build/`, which is not tracked. All three need a
tikz-flora tree: a checkout, or a frozen copy of one revision. Measure against
a frozen copy when comparing runs, so that a change in the engine cannot
shift the figures:

```sh
mkdir -p build/engine-60a153d
git -C <tikz-flora> archive 60a153d | tar -x -C build/engine-60a153d
git -C <tikz-flora> rev-parse 60a153d > build/engine-60a153d/engine-commit.txt
```

The tools read `engine-commit.txt` for the revision they report, since the
copy has no `.git` of its own.

### Build times

`tools/measure_reuse.py` builds one deck cold and then warm. It takes a label,
a variant and the number of frames and overlays per frame; the engine and the
other settings go in environment variables. One command runs one config, so a
table is a series of commands:

```sh
export TIKZFLORA=$PWD/build/engine-60a153d

python3 tools/measure_reuse.py p-21-adaptive adaptive 10 2             # adaptive, 21 pages
REUSE=all python3 tools/measure_reuse.py p-21-all adaptive 10 2        # reuse=all
REUSE=content python3 tools/measure_reuse.py p-41-content adaptive 40 1
S=5 python3 tools/measure_reuse.py p-97-adaptive adaptive 30 3         # a section page every 5 frames
PATTERN=asanoha python3 tools/measure_reuse.py p-21-pattern adaptive 10 2
python3 tools/measure_reuse.py p-21-none none 10 2                     # Beamer without floral
S=5 python3 tools/measure_reuse.py p-97-off off 30 3                   # flora off, 97 pages
```

`REUSE` sets the `reuse` value, `PATTERN` a pattern, and `S` puts a section
page every S frames. The 21-, 41-, 91- and 97-page decks are `10 2`, `40 1`,
`30 3` and `30 3` with `S=5`. Each build waits until the 1-minute load average
is below `--max-load` (default 4, for at most `--wait` seconds) and records
the load before and after. Peak memory comes from `/usr/bin/time -l`, so the
tool needs macOS. Rows are appended to `build/reuse-benchmark/results.jsonl`
and printed as JSON; compare passes by running a config twice under different
labels.

### File sizes

`tools/measure_sizes.py` builds `test/size-benchmark.tex` in each variant
(`none`, `static`, `overlays`, `vector`, `raster`) and prints the page count,
size and build time. `--variant` measures only the named variants and may be
repeated, which gives one config per command. The tool rewrites `results.json`
in its `--outdir` on every run, so give each run its own `--outdir` or the
earlier rows are lost (the 60a153d figures were measured this way):

```sh
python3 tools/measure_sizes.py --engine build/engine-60a153d
for v in none static overlays vector raster; do
  python3 tools/measure_sizes.py --engine build/engine-60a153d \
    --variant $v --outdir build/size-60a153d/$v
done
```

The `growth=off` row of the table is the `static` variant. Without `--outdir`, results go to
`build/size-benchmark/results.json`, with the commit, the engine revision and
the TeX version. The raster variant builds through `tools/build_animation.py`
and is by far the slowest variant: it took 10-12 minutes on the loaded machine
of these runs, which is not a typical figure.

### Raster builds

`tools/measure_raster_build.py` measures cold and warm raster builds with the
time of each step, peak memory and peak disk. It takes a frozen engine and
must not be pointed at a checkout under development:

```sh
python3 tools/measure_raster_build.py --engine build/engine-60a153d --fixture slides
```

The `slides` fixture is the document of the file-size table built with the
raster backend; `--fixture title` measures a single dense title page, and
`--source` measures a document of your own. `--dpi` (default 144) and
`--jobs` (default 2, concurrent raster jobs) set the sample resolution and
parallelism. Results go to `build/raster-measurements/results.json`, written
after every build. Its disk figure is the peak size of the whole output tree
in MiB, which is not the same as the 109 MB sample cache above.
