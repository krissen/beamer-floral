# Growing flora

Opt in to growth across overlays:

```tex
\florasetup{growth=overlays}
```

Displayed overlay `k` of `N` shows approximately `k/N` of the finished
painted area. Leaves and flowers expand as whole shapes from their
attachments; stems extend before their foliage. A frame with one displayed
overlay shows its complete decoration. Skipped overlay numbers do not count
as stages. The final composition, seed and protected text regions stay fixed.
The first run is provisional; let `latexmk` converge after editing overlays.
An error reports compositions whose growth resolution cannot support the
requested number of distinct stages.

**Only raster playback needs a render cache.** `growth=overlays` is a
manual reveal as you step through slides and requires neither a render cache,
Python, Poppler nor `animate`. `growth=off` keeps ordinary static flora.

For vector playback (`growth=timed`), load the optional package in the preamble:

```tex
\usepackage{beamer-floral-animation}
\florasetup{growth=timed, growth duration=8, growth fps=20}
% Or select playback for one frame:
\florathisframe{growth=timed, growth duration=4, growth fps=15}
```

The default vector path uses ordinary `latexmk` and requires no Python,
Poppler or render cache. Detailed watercolour vectors can play unevenly in
Reader even at a requested high fps.

For smoother playback, explicitly opt in to raster caching:

```tex
\usepackage[raster]{beamer-floral-animation}
```

**Extra build dependencies apply only to this raster playback option.**
Install Python 3.9 or later and Poppler's `pdftocairo`, in addition to the
usual LuaLaTeX, `latexmk` and `animate`. They must be on `PATH`. Build with:

```sh
python3 tools/build_animation.py --outdir build/slides slides.tex
```

`--dpi` (36 to 600, default 144) sets the sample resolution, `--jobs` (1 to
8, default 2) the number of concurrent raster jobs, and `--engine` a
development checkout of tikz-flora (otherwise `TIKZFLORA` is read).

The builder runs LaTeX to measure the document, renders missing background
samples and builds the final PDF. It reuses existing samples on later builds.
There is no shell escape. The external tools are needed **when creating or updating
the cache for raster playback only**; viewing the PDF needs no Python or Poppler.
The builder's measurement PDF is an intermediate product: on cache misses it
collects geometry and the animation manifest without painting flora. LaTeX
still runs until cross-overlay geometry and page layout stabilize. The worker
then validates growth stages and exports missing samples before the final PDF
is built. Valid raster caches require no growth planning during LaTeX passes.
With `[raster]`, ordinary `latexmk` reports an error when the cache is
missing or stale and tells you to run the builder. It never silently uses
old frames. Changing geometry, seeds, engine sources, overlay counts or the
sample grid invalidates the affected cache.

The cache lives beside the build outputs in `<job>.floral-animation/`; keep
it with the document when moving to another machine. Cold builds need extra
time and temporary disk space, and cached samples consume disk space. Moving
flora is rasterized at 144 dpi by default (`--dpi` changes this),
including interval boundaries and static posters. Text and links remain
ordinary vector PDF content. With `[raster]`, the static and printed floral
endpoint uses the same raster image as playback, avoiding a vector redraw when playback stops.
Handout mode always uses complete static flora and needs no render cache.

`\usepackage[vector]{beamer-floral-animation}` explicitly selects the default
vector path. Neither this path nor manual overlay reveals need the external
raster tools.

Overleaf can compile static flora, manual reveals and vector playback directly.
For cached timed playback, build the cache locally first and upload it with
the document; rebuild locally after changes that invalidate it. The external
raster builder is not part of an ordinary Overleaf LaTeX compile.

Each overlay plays its own growth interval, starts automatically on page
entry, plays once and stops at its endpoint. With `animate` playback, returning to
a page restarts that interval; GIF playback does not replay it (see below). Advancing early starts the next page at its nominal starting
stage. Duration is the total active growth time across the frame, divided
equally among its displayed overlays; time waiting between clicks is excluded.
A single title page animates the whole plant. **Text is visible from the start**;
only the background flora plays an animation.

`growth` accepts `off` (default), `overlays` or `timed`. `growth duration`
is a positive finite number of seconds (default 8). `growth fps` is an integer
from 1 to 60 (default 20); the frame count is rounded and the playback rate
adjusted so each interval contains both endpoints. Playback follows elapsed
time and skips late samples when a viewer cannot keep up.
Document settings are inherited; `\florathisframe` applies to the whole frame
and does not affect the next one. Use `\florathisframe{growth=off}` for a
complete static decoration.

Animation uses `animate` with `method=ocg` behind ordinary Beamer text,
links and numbering, with no mouse controls. With this path, vector or raster,
the interval's final stage is the static poster, including in viewers without
JavaScript. Handout mode
always paints complete static flora and needs no animation support package.
Ordinary documents do not load `animate`.

The [animate manual](https://tug.ctan.org/macros/latex/contrib/animate/animate.pdf)
documents OCG playback in desktop Acrobat Reader and Okular. We have checked
playback in desktop Acrobat Reader; Okular is untested. With the vector and
raster paths, viewers that cannot play the animation show the finished flora;
with GIF playback they show each interval's start state (see below). See [the timed example](../src/growth.tex)
and [the acceptance checklist](../../test/acceptance/growth.md).

## GIF playback for viewers without JavaScript

Viewers such as pympress cannot run the JavaScript of `animate`. For them,
select GIF playback:

```tex
\usepackage[gif]{beamer-floral-animation}
\floralgifmatte{FFFFFF} % optional: the page colour, six hex digits
```

Every `growth=timed` interval is then built from the raster cache as a GIF
and played by a full-page Screen annotation, with no `animate` environment
and no JavaScript in the PDF. `gif` includes `[raster]`, so the builder and
its requirements above apply. It also needs
[Pillow](https://pypi.org/project/pillow/) when it builds GIFs
(`python3 -m pip install pillow`). The build is the same:

```sh
python3 tools/build_animation.py --outdir build/slides slides.tex
```

By default the GIFs are **embedded in the PDF**, which is then
self-contained, at the price of a larger PDF; a measured figure is in
[performance](../dev/performance.md#embedded-gif-playback). With `[gif-external]` the PDF stays small and
plays the GIFs from files instead, in a Movie annotation. Keep
`<job>.floral-animation/` beside the PDF then, and move them together; a PDF
without them plays nothing.

The frames are composited against `\floralgifmatte` (default `FFFFFF`), so
set it to your page colour; pixels that are almost fully transparent stay
transparent. GIF files are named by interval, frame rate, matte colour and
encoder version, and are reused on later builds.

Limits:

- GIF frames are thinned above 50 fps effective rate (`growth fps` times
  the rounding of steps per interval can exceed it): every k-th sample is
  kept, with the first and last always present. Viewers that decode GIFs with
  GdkPixbuf, as pympress does, play any frame delay below 2 centiseconds as 20 ms
  (and a zero delay as 100 ms), so faster frames would play too slowly.
  An interval shorter than 20 ms plays in 20 ms.
- The GIF is an annotation above the page, not page content. Reservations
  (`\florareserve`) are applied to it: every pixel inside a reserved rectangle
  is transparent in every frame, rounded outward to whole pixels. Because the
  GIF plays above all page content, reserve areas that hold a logo or footline.
- Soft flora edges are matted against `\floralgifmatte`, not against what is
  under them. Over a coloured background band, set the matte to the band's colour
  or accept a light halo.
- Playback is verified in pympress 1.8.6. Viewers that do not play these
  annotations show each interval's start state, not the finished flora.
- Each interval plays once. Returning to a page does not replay it.
- The path of the cache (the output directory included) must not contain `%`,
  `{` or `}`. With `[gif]` it must not contain `#` or `^` either. With
  `[gif-external]` the document name must not contain `#`, `^`, `(`, `)` or a
  backslash. The build stops with an error that says to rename.
- Print or export from handout mode (it paints complete static flora).
