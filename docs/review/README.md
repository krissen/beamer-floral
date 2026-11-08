# Pre-announcement quality and feature review

Review date: 2026-11-05. Original baseline: beamer-floral `5c51fa9`, engine
`898fcd3`, CI engine pin `2c1fc8e`. Tested locally with LuaHBTeX 1.21.0 /
TeX Live 2025 and Beamer 3.72 on macOS.

## Current example and margin policy

The screenshot-ready acceptance template is now entirely English and discusses
botanical borders, typography, colour and page composition. The recommended
matrix contains 16 PDFs (256 pages): floral and seven stock themes, in 16:9
and 4:3. Sidebar themes and inherited narrow-margin variants are excluded from
the recommended matrix. Earlier 20-PDF counts below describe the historical
review that identified those unsuitable configurations.

Both the floral theme and the generic package now supply 2.5 cm left and 1 cm
right margins by default. The visual template does not manually set those
margins for package-enabled cases: it exercises the real package defaults.
Custom margins may be set after loading. The old phrase “default margins”
referred to inherited Beamer settings and was misleading for this project.

`--screenshots docs/img` exports title, palette and stock-theme images from
the same acceptance PDFs. These are not separately authored screenshot-only
examples. The English frame-title regression reproduces the original
justification failure (badness 3861) with an isolated old title template.

## Outcome

The review identified and addressed the principal release blockers: an
undeclared licence, missing standalone distribution, unstable overlays,
incomplete CI coverage and white reservation knockouts over coloured bands.
The owner chose MIT and explicitly approved implementation of frame-stable
flora. Engine changes were coordinated with the tikz session; the shared
engine pin is now `a3553bf6e449026a2e2e62b16e10210e82e9c1ad`, available on the
fork's remote. No upstream PR or announcement was published by this session.

Local verification is described below. The quality work was merged as PR #16 (`e40656f`), with green CI and
Codex review. The exact-commit candidate is recorded in
`build/release-candidate/verification.json`. It remains unpublished; these
checks do not establish broader TeX-version compatibility.

## Quality findings and disposition

| Finding | Severity | Disposition |
|---|---|---|
| No declared package licence | High | MIT LICENSE added with owner approval |
| No standalone release artifact | High | Deterministic ZIP builder, exact engine pin, extracted installation test |
| Different flora on overlays of one frame | High | Frame adapter and geometry cache implemented; convergence and full-spec equality tested |
| Reservation paints white over coloured background | Medium | Engine fixed clipping; Beamer reproducer verified before/after; fix in new pin |
| Executable documentation and stock themes excluded from CI | Medium | CI compiles examples and integration fixtures, runs adapter tests, saves failure artifacts |
| Fragile internal Beamer title patches only warn on failure | Medium | Failed patches now raise package errors instead of silently giving incorrect clearance |
| Suspected frozen horizontal margins | Cleared | Initial review interpretation was wrong; delayed expressions read changed margins correctly |
| Vector output size and rendering cost | Informational | Measured examples are substantial; no evidence of a regression or agreed size budget |

### Frame-stable composition

`beamer-floral.lua` owns invocation identity and stores the union of measured
content rectangles for each frame in a versioned numeric TSV `.floral-cache`.
The cache never executes saved Lua or TeX. The complete union, maximum title
clearance, header extent, effective settings and logical seed are shared by
all overlays after convergence. Corrupt caches rebuild; deleted frame entries
are discarded; changes in geometry request a rerun. Atomic replacement and
explicit recorder registration let latexmk notice generated-cache changes.

`\florathisframe` and the Beamer `\florathispage` alias affect the next painted
frame and all its overlays. Document settings, dimensions, reservations and
on/off state must stay constant within a frame. Changes, including floral background-band settings, are rejected rather
than producing inconsistent painting. An existing engine preparation callback
is chained before the adapter callback. A replay is a new invocation; unnumbered
frames and continuation pages have independent identities. Split parity follows
these logical identities. The engine's ordinary article defaults remain
physical-page based; its only new integration capability is a versioned
optional `prepare_spec` callback.

First uncached output is provisional. Run latexmk until the geometry rerun
warning clears. No extra execution of frame bodies is used to measure future
overlays. See [overlays.md](overlays.md) for the original investigation.

### Reservation background defect

`reserve-background.tex` demonstrated a white hole in an orange top band.
The engine now clips the flora instead of repainting the reserved rectangle.
The tikz session added tests for overlapping reservations and clear behavior.
Beamer evidence: [before](evidence/reserve-preview.png),
[after](evidence/reserve-fixed-preview.png). This fix is included in the shared
engine pin.

### Cleared margin suspicion and settings lifetime

The original review claimed that `\AtBeginDocument` froze margin dimensions.
That was incorrect: `\floratextblockx` stores expressions with `\def`. The
instrumented lifecycle reproduction sent x0=28.45274 pt initially and
71.13188 pt after a direct margin change. No core fix was needed.

That partial downstream-style margin fixture also produced a 42.67914 pt
output hbox warning; it does not update every Beamer layout length, and is a
diagnostic fixture rather than a supported margin-switching implementation.
The documented preamble `\setbeamersize` usage passes.

The lifecycle trace confirmed restored defaults and zero title clearance on
an untitled following frame. Pending settings survive disabled pages until
the next painted frame. `test/frame-settings.tex` asserts frame override
persistence/restoration, changing title geometry and exactly the expected two
body executions for two overlays.

## Verification and reproduction

- All three original tests and all four executable documentation sources were
  built. New integration fixtures cover 4:3/16:9, nested lists, columns,
  images, all six layouts, all four palettes, ordinary/plain/fragile frames,
  on/off, long wrapping titles, untitled transitions and frame continuations.
- Overlay examples exercise `only`, `uncover`, `pause`, unnumbered frames,
  selected replay and handout. In converged verification mode they compare
  the complete serialized composition specification between overlays.
- Replay-label warnings also occur in the same fixture using stock Beamer;
  they are not introduced by floral. The diagnostic `lifecycle.tex` has the
  separate partial-margin warning described above. These exceptions are not
  reported as warning-free tests.
- Unit tests cover union/convergence, logical identities, restored nil-valued
  settings, rejected midframe mutations, malformed/reversed cache data and
  reinitialization after cache removal.
- Isolated installation was initially tested against both original engine
  revisions without rc files or development paths. The final standalone
  archive is tested by extraction and compilation against the new exact pin.
- Two final ZIP builds produced identical bytes; archive contents and engine
  provenance were checked. Both original licences and engine acknowledgements
  are included. No `.env` or development caches enter the archive.
- The initial 32-page set and 12-page layout/palette coverage were rasterized
  for contact inspection, with selected full-size inspections. This checks
  gross layout/readability and does not establish pixel-level collision
  freedom for every possible document or seed. `layout=title` is less polished
  on ordinary content frames; use the demonstrated title-page setup.
- A warm-cache isolated one-page baseline build took 4.06 seconds wall time.
  Baseline PDF sizes were about 4.5 MB for smoke/3 pages, 18 MB for showcase/8
  pages and 12 MB for long titles/2 pages. These are single local observations,
  not performance guarantees.

From repository root, with TIKZFLORA configured as in the main README:

```sh
texlua test/overlays.lua /path/to/tikz-flora
latexmk -lualatex test/smoke.tex test/stock.tex test/titles.tex
latexmk -lualatex docs/review/overlays.tex test/frame-settings.tex
FLORAL_VERIFY_STABLE=1 latexmk -g -lualatex docs/review/overlays.tex test/frame-settings.tex
python3 tools/dist.py --engine /path/to/tikz-flora --test
```

Do not use verification mode on a first uncached build: its purpose is to
assert equality after the normal passes have converged. CI performs the
normal builds followed by this verification pass.

## Feature inventory and priority

| Capability | Current coverage | Recommendation after the quality work |
|---|---|---|
| Margins, layouts, density, mix | Exposed engine settings | Improve the visual catalogue and explain suitable slide types |
| Palettes and semantic colours | Four presets with theme hook | Demonstrate custom palettes; preserve stock-theme separation |
| Background bands and reservations | Exposed engine API, tested fix | Document footline/logo use and lifetime |
| Visitors, ink spin and ornament weights | Exposed but lightly demonstrated | Add examples before inventing more wrappers |
| Title markers, specimen sheet and gallery | Available engine commands | Assess Beamer-specific usefulness |
| Floral itemize markers | Standard circles today | First feature prototype: three depths, readable at projected size |
| Title/section flourishes and closing ornaments | Automatic page-layout ornaments | Evaluate explicit template placement |
| Dividers and block ornaments | No dedicated integration | Second prototype using a standalone ornament renderer |
| Floral navigation marks | Standard navigation | Lower priority; small-size clarity and PDF size matter |

The engine has eight ornament slots and internal
`ornaments.draw(kind, painter, rng, box, options)`. Public TeX commands draw
entire galleries/specimen sheets, but there is no public single-ornament
command. A stable standalone renderer should therefore be designed jointly
before replacing list bullets. Define kind names, font-relative size,
baseline/bounds, paint reach, colour policy and an independent seed. Inline
symbols must not consume page RNG or pending frame settings. Reject unknown
kinds clearly and retain ordinary templates for stock themes.

Prototype simple gilt/rosette/leaf forms before shrinking complex cartouches.
Judge legibility, nesting, overlay/handout stability, build cost and PDF size
from rendered examples. No ornamental feature expansion was implemented in
this quality pass.

## Coordination

Initial coordination used `~/bin/scripts/coms`, channel `latex/floral-review`.
Direct `send_message_to_thread` then became available. The tikz session
implemented, tested, committed and pushed reservation clipping and the generic
spec-preparation hook; it also reviewed this adapter. The Beamer adapter,
fixtures, packaging and CI changes belong to this repo. Its upstream PR remains
held pending the agreed readiness checks; no public announcement was sent.

Final candidate archive SHA256: `a3384e13d341da8ef93ec0426c3fdc72e538f533e1bb0f19c630da6cbdeba8b9`.

Final verification: the complete-spec equality check passed after convergence
for changing-title overlays and callback chaining, with a clean final log.
Rendered evidence: [overlay 1](evidence/overlay-1.png),
[overlay 2](evidence/overlay-2.png). The first verification attempt after a
cache-signature change deliberately failed because it was run before the
normal convergence pass; normal convergence followed by verification passed.
The final standalone ZIP's extracted example compiled successfully and a
second build produced the identical SHA256 recorded above.

## Broad visual acceptance suite

`test/visual/template.tex` and `tools/visual_suite.py` now provide a repeatable
20-PDF / 320-page matrix: floral plus eight stock themes, 16:9 and 4:3,
with additional standard-margin floral variants. The result set contains a
page guide, linked HTML index, contact sheets, complete logs and baseline
comparisons. All documents compile; zero introduced diagnostics remain.

This suite found an underfull justified frame title in our 4:3 theme. The
frametitle minipage is now ragged-right. All four floral variants were rebuilt
without diagnostics; `test/frametitle-wrap.tex` plus `test/check_boxes.lua`
keep the case in CI, including failing the check on box warnings.
Berkeley has two box warnings per aspect ratio (including an 18.19995 pt
vbox for the longest 4:3 heading), identically reproduced without floral.
Those inherited limitations remain visible in the report and baseline PDFs.
The visual suite fails on compilation errors or unmatched diagnostics.

## User visual review: headline and sidebar findings

User inspection found two failures that successful compilation had missed.
On Berlin PDF page 9, an untitled frame placed the hero partly behind the
running headline. The adapter now supplies the body boundary for non-plain,
untitled body-mode frames without claiming a frametitle exists. `test/headline.tex`
checks the whole hero's upper bound, clipping of the floral composition, and
preservation of an unrestricted plain frame. It passes and is included in CI.

Berkeley's sidebar overlays the same margin where the flora grows. This
combination is explicitly not visually supported; it is no longer presented
as a successful visual combination. README documents the limitation, the
package warns when a sidebar is present, and the visual index marks it as
unsupported independently of stock-theme box diagnostics. Title-page success
does not imply content-frame compatibility.

Berlin untitled-frame evidence: [before](evidence/berlin-untitled-before.png), [after](evidence/berlin-untitled-after.png). The actual visual-review PDF page 9 was inspected after rebuilding in both aspect ratios; its hero is now complete below the headline.

All stock-theme visual-review PDFs were rebuilt after the untitled-headline fix. The 20-PDF index has zero unmatched compilation diagnostics and explicitly marks both Berkeley variants as visually unsupported. User visual acceptance of the remaining themes is still pending.

The recommended English template now separates the block/palette scene from the nested-list scene to keep screenshot content clear of the lower border. The screenshot export reuses the block scene directly from the acceptance PDF.

Integration follow-up for downstream themes: margin snapshots taken after requiring beamer-floral now capture floral margins. A theme restoring its original undecorated layout must snapshot before requiring the package. The sola-floral integration was adapted in kau-tex PR #11 (`f84b7c3`), as recorded in the handover. This session does not edit that separate repository.

The final recommended English suite passed: 16 PDFs / 256 pages, no diagnostics. PDF text bounds confirm the nested-list column respects the default left margin in every case. All twelve README screenshots were regenerated from the acceptance PDFs and the CI-tested documentation showcase. Margin defaults, post-load custom overrides and converged overlay-spec equality also passed.

## Optional ornament implementation review

The engine pin is now `28c394a80b8a27a71d0ce979ce7b328b34a341cb`,
coordinated with the tikz session. It supplies a public isolated monochrome
ornament command. Floral adds optional three-depth list templates and a
configurable divider; circle markers remain the default.

Local comparison PDFs in `build/ornament-review/` cover 16:9 and 4:3, four
palettes and two-overlay list frames. All four PDFs compile without box or
package warnings. Selected list and divider pages were rasterized and
inspected; projection-size approval remains with the user. The first divider
render exposed right alignment, corrected before the final comparison.

Final nine-page PDF sizes: 16:9 baseline 9,004,444 bytes, ornaments 9,000,336;
4:3 baseline 9,413,401, ornaments 9,409,124. Baselines also replace the divider
with a plain rule; these totals show no material size increase for this
fixture, not a general size guarantee. End-to-end build timing has not yet
been controlled for cache state. The earlier isolated Lua microbenchmark
is not an end-to-end build-time measurement.

A separate handout fixture (`test/ornament-settings.tex`) verifies explicit
colour and form overrides with background flora disabled. It compiled
without diagnostics. Adapter overlay unit tests passed against the new
engine. The release candidate in `build/release-candidate/` remains the old
exact-merge artifact and must not be mistaken for a bundle of these changes.

User visual review selected the same `gilt_rosette` for all three list
depths and a divider with nominal width `0.5\linewidth`. Both aspect-ratio
comparisons were rebuilt without diagnostics after these adjustments.
Each list depth remains independently configurable.

Headpiece follow-up: the user identified crowded end rosettes in the
configuration catalogue. Engine commit `73c3d6e` separates the band and
rosettes and handles short proportions within the same nominal box. The
engine session verified measured bounds/gaps across five aspect ratios and
five seeds. The Beamer catalogue was rebuilt without diagnostics and its
divider screenshot regenerated and visually inspected. The engine pin now
includes this correction.
