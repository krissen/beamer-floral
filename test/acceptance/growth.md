# Growth acceptance

Build `test/growth.tex`, then rerun with `FLORAL_VERIFY_STABLE=1`.
This covers 1, 2, 4, 16 and 64 displayed overlays, selected raw numbers 2/5,
`pause`, `uncover`, `only`, changing titles, unnumbered frames, reservations,
`againframe`, continuations and a frame override inside its body. The body
execution counter must match Beamer's two displayed overlays. Cache counts
must converge and consecutive rendered growth stages must differ.

Build `test/growth-timed.tex` and `test/growth-handout.tex`. The latter must
compile without animate and render complete flora. Rasterize timed PDFs
with JavaScript disabled and compare posters with the corresponding static
interval endpoints. Check protected text areas, full leaves and blooms and
the unchanged finished composition, including sparse compositions.

Manual viewer acceptance (pending; do not infer from build success):

- Desktop Acrobat Reader: single title page plays 0→1 and stops.
- Each overlay plays only its nominal interval, once.
- Advance early; the next page begins at its nominal starting stage.
- Revisit a page; its interval starts again.
- Text and page numbering remain crisp; the example link is clickable.
- Print/export without playback; each page shows its interval's endpoint.
- Repeat in Okular when available.

For an eight-second dense animation, measure elapsed build time, peak memory
and PDF bytes. Keep viewer version, timings and any playback limitations
with the evidence. The plan and paint resources are reused; frame streams
are stored per sample, so long high-frame-rate animations can be large.

On macOS with desktop Acrobat Reader installed, the optional script below
opens the PDF and reports its
current progress and stopping state. It does not restart the animation unless
you pass a third argument `restart` for an explicit replay/performance test. It controls the Reader UI; do not run an explicit restart test while manually judging replay.

```sh
osascript tools/check_growth_acrobat.applescript "$PWD/build/growth/growth-benchmark.pdf" 8
```

Initial measurement before resource optimisation (Reader 26.00222031):
161 samples requested at 20 fps; observed sample 4 after one second, sample
34 after eight seconds, still playing. The dense PDF was 122,928,166 bytes;
a full `latexmk` build took 349.73 s with 591,282,176 bytes maximum resident
memory. This is a failing performance baseline, not playback acceptance.
The user also observed text flicker; smoothness and stable text remain open.
The automated script explicitly restarts playback, which can look like a
replay when the PDF is being inspected at the same time.

## Current integration findings

- Native per-part Forms reduced the dense vector baseline from 122.9 MB /
  349.73 s to about 5.1 MB / 14.08 s. Reader could still render only a subset
  of requested samples. Elapsed-time playback now skips late samples and
  stops at the nominal endpoint instead of accumulating timer delays.
- The user confirmed stable text from the start in the four-second probe;
  text flicker was no longer observed there. Raster playback was judged
  snappier and less choppy.
- The transient top ornament line at late stages of both 16 and 64 overlays
  was traced to clipped source geometry being scaled into view. Engine
  c70b5bd preserves source and destination clips; both stage counts have
  dedicated regression coverage.
- Duplicate PageOpen/PageVisible notifications can replay short intervals.
  A per-entry guard now rejects duplicates and resets only on page exit.
  The emitted-PDF JavaScript test checks catch-up, stop, duplicate events
  and genuine replay after page-close.

## Build modes and external tools

The user's forward-only recording established an endpoint flash on entry,
followed by the intended growth. This was not caused by navigating backwards.
The current candidate prepares owned animation layers in document JavaScript,
initializes their screen view at the interval start, and rearms them only on
PageInvisible. PageClose pauses without redrawing the outgoing page. Static
posters and print/export layer usage still select the interval endpoint.
Actual emitted PDF scripts pass startup, duplicate-entry, pause, invisible,
reentry, timing and endpoint checks. Visual Reader acceptance remains pending.
The user subsequently distinguished a clean first pass from a glitch on the
second pass. A further candidate prepares other owned animation layer families
when leaving a page, keeping the outgoing family unchanged. This is covered by
a sibling-family check against the emitted PDF JavaScript; Reader acceptance
still requires both passes.

Manual `growth=overlays` reveals need no render cache, Python, Poppler or
`animate`. Static `growth=off` needs none either. Default `growth=timed`
playback uses vector graphics and only adds the TeX package `animate`.
The explicit `[raster]` option needs Python 3.9+ and Poppler's `pdftocairo`
when creating/updating its cache; the final PDF and subsequent TeX builds
with a valid cache do not need those tools. This is an opt-in portability
tradeoff, particularly for Overleaf. See the README build instructions.

The user confirmed that `revisit-prepared.pdf` works after the other-family
preparation fix. Both participants navigated during the recording, so its page
order is not a controlled playback sequence. Automated emitted-PDF checks pass;
the complete final regression and standalone sweep remain to be run.

The updated engine (`103185a`) gives the full title an explicit support order.
The theme now selects the fuller title composition automatically; the title
regression confirms that frame overrides win and ordinary frames retain their
document settings. The 100-page growth matrix and stable cache reruns pass,
and all five vector animation posters match their static references at 72 dpi.
Extracted standalone static/vector/raster examples build without development
paths.

The user found one remaining brief white flash exactly at the end of the new
eight-second title. Raster playback had switched to a heavy vector endpoint.
All raster samples, including shared interval boundaries and the final poster,
now stay on the image path. Existing interior images are reused; older caches
need only their missing boundary images. Text and links remain vector content;
the floral static/print poster is raster in this explicitly selected mode.
The user confirmed the new `full-title-raster-endpoint.pdf` has no glitches.

PR #17 and engine PR #7 carry the changes. CI initially compiled all documents
but its host-side PDF checker could not read the container-owned PDF. PDF and
raster checks now run inside the TeX container with their system dependencies.
CI and bot review are pending; no merge has been performed.

## GIF playback (pympress)

Automated checks cover the build, not the viewer. Build both variants with
Pillow installed:

```sh
.venv/bin/python tools/build_animation.py --engine ../tikz-flora --outdir build/gif test/growth-gif.tex
.venv/bin/python tools/check_gif_pdf.py build/gif/growth-gif.pdf --pages 3 --mode embedded
.venv/bin/python tools/build_animation.py --engine ../tikz-flora --outdir build/gif-external test/growth-gif-external.tex
.venv/bin/python tools/check_gif_pdf.py build/gif-external/growth-gif-external.pdf --pages 3 --mode external
```

The reservation documents `test/growth-gif-reserve.tex` and
`test/growth-gif-reserve-external.tex` add a footline band and a block inside
the page; build them the same way (`--reserved` also requires the reservations
in the recorded frames). The checker compares frames with the samples after the
same masking and requires the reserved pixels to be transparent.

What the page does around the flora in the engine's `typeset_page`, and what
GIF playback does about it (the GIF is an annotation, so page-content operations
do not reach it):

| Operation | GIF playback |
| --- | --- |
| Reservation clips (`\florareserve`) | Baked into every frame: reserved pixels transparent, rounded outward. The engine also clips them inside the samples; measured on the reservation document, no sample has an opaque pixel inside a reserved box, so the mask changes only edge pixels. |
| Background band (`background_height`) | Documented limit: soft edges are matted against `\floralgifmatte`, not the band. |
| Bounding box | Cannot matter: sets the picture size; the annotation Rect is the page. |
| Transforms, opacity | None are applied at page level. |
| Stacking order | The GIF plays above all page content; documented, use `\florareserve` for logos and footlines. |

The checker reads the PDF and the GIFs: one full-page annotation per timed
page (Screen with an embedded GIF, or Movie with an external one), a GIF with
the interval's frame count whose first and last frame decode to their
samples, and no JavaScript. Then, in pympress (pending; do not infer from the
build):

- Each timed page plays its interval once, above the text, and stops.
- On the reservation documents nothing plays over the footline band or the
  block inside the page.
- The text stays crisp and the link on page 2 stays clickable.
- Pages 2 and 3 start at their nominal starting stage.
- Leaving a page and returning does not replay it (known limit).
- No flash of the finished flora on page entry or after the last frame.
- Embedded: copy the PDF alone to another folder; it still plays.
- External: copy the PDF without `growth-gif-external.floral-animation/`
  beside it: no playback, the start state of each interval shows (known limit).

`tools/probe_pympress.py` logs what the viewer does on each page: overlay
events, GIF repaint cost, peak memory and the drawing right after a page
change. Run it with pympress's own Python, from a shell where a window may open:

```sh
<pympress python> tools/probe_pympress.py <outdir> build/gif/growth-gif.pdf 4 1 2 3
```

(`<outdir>` receives `events.log`; `4` is seconds per page, then the pages
to visit.)
