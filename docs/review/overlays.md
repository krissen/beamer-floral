# Overlay stability investigation

Implementation update: the recommended adapter and geometry cache have now
been implemented and tested. The current status and final semantics are in
[README.md](README.md). The investigation below records the original evidence
and design rationale; it is not the current list of outstanding work.

Reproducer: `overlays.tex`, Beamer 3.72, engine `898fcd3`.
Run from the repository root with an existing relative diagnostics directory:

```sh
mkdir -p build/review-overlay-specs
FLORA_SPEC_DIR=build/review-overlay-specs latexmk -lualatex docs/review/overlays.tex
```

Absolute diagnostic output paths were refused by LuaTeX's file output policy
in this environment. A relative directory worked. This was a diagnostic setup
failure, not a rendering regression.

## Observations

| Scenario | Physical pages | Frame counter | Overlay | Start page |
|---|---|---|---|---|
| only | 1–2 | 1 | 1–2 | 1 |
| uncover | 3–4 | 2 | 1–2 | 3 |
| pause | 5–6 | 3 | 1–2 | 5 |
| noframenumbering | 7–8 | 3 | 1–2 | 7 |
| againframe, selecting overlay 2 | 9 | 4 | 2 | 9 |

`flora.measure.boxes` yielded 2 versus 3 line rectangles for the two `only`
slides. Serialized line geometry was exactly equal within the `uncover`,
`pause` and unnumbered pairs. Thus identical logical seeds would solve these
particular latter examples but cannot solve arbitrary `only` layouts.

The original inline framebreak fixture did not force a continuation. It has
been corrected with `\par` before `\framebreak`; both aspect-ratio matrix
documents now produce eight pages. The trace table above describes the
original overlay run, before that fixture correction.

The handout variant compiled. `againframe` produces duplicate hyperlink/label
diagnostics in this fixture, so compilation is not a warning-free acceptance
result. Isolate the same replay in stock Beamer before attributing those
diagnostics to floral.

## Recommended solution to prototype

Use a per-frame invocation identity owned by the Beamer adapter, separate from
the display frame counter and physical page number. A monotonic invocation
counter is preferable to keying solely on `framenumber`: unnumbered frames
share that counter. Treat `againframe` as a new invocation by default; stable
replay of the original garden would need a separate documented policy.
Continuation pages from `allowframebreaks` need separate geometry/identities.

Keep the engine's existing physical-page behavior as its default. Add optional
logical seed identity and measured-geometry input only after adapter ownership
and lifetime have been established with the tikz session. This is a proposed
interface capability, not an implemented or approved wire format.

For arbitrary overlays, collect the union of all content exclusion rectangles
for each invocation in a versioned job sidecar. On the next run, compose all
overlays against the same union, seed, title bounds and effective settings.
Include frame dimensions, header mode and relevant options in cache validity.
Warn and request a rerun when the collected union changes; never report stable
output on the first uncached run. Write the new sidecar atomically and do not
evaluate saved content as TeX. Clear stale frame entries after a changed deck.

Avoid extra executions of the frame body merely to find future geometry:
Beamer frame bodies can write files, increment counters and perform other
actions. Freezing only the first overlay's geometry can paint across content
revealed later. Reserving the whole text rectangle is a simpler alternative,
but changes the package's content-aware growth behavior substantially.

Engine geometry must remain valid independently of the cached visible title:
take maximum title clearance and union title extents, rather than retaining
the first overlay's height. Explicit content changes to palette/layout within
a frame need a documented precedence policy before implementation.

## Acceptance before readiness

- Byte-equivalent normalized decoration output for each overlay of a frame
  after convergence, excluding PDF resource identifiers.
- No intersections with any overlay's protected content, including changing
  titles and `only` content at different vertical positions.
- Correct isolation for unnumbered frames, selected overlays starting at 2,
  replay, fragile frames, handout and continuation pages.
- No extra frame-body side effects, page-setting leakage or stale cached
  geometry after editing/reordering a frame.
- Existing article page seeds and `\florathispage` semantics remain unchanged.

Investigation is complete enough to establish that a seed-only fix is
insufficient. Implementation and acceptance of the chosen behavior remain
separate follow-up work; this document does not give release clearance.
