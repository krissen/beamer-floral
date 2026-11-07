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
