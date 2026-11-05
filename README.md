# beamer-floral

Procedural watercolour flora for [beamer](https://ctan.org/pkg/beamer),
drawn by [tikz-flora](https://github.com/krissen/tikz-flora). Each slide
gets its own generated plant; the text block is measured so the flora
grows around the content and the margin follows the page.

## Requirements

- LuaLaTeX
- the [krissen/tikz-flora](https://github.com/krissen/tikz-flora) fork,
  branch `beamer-floral`, commit `a3553bf` or later. The upstream engine
  lacks the integration hook this package uses. `engine-ref.txt` pins the
  revision used by CI and standalone bundles.

For a local checkout, point `TIKZFLORA` at it, or put the path in a
gitignored `.env`:

```sh
TIKZFLORA=/path/to/tikz-flora
```

Without `TIKZFLORA`, an installed `tikzflora` is used.

## Use

```tex
\documentclass{beamer}
\usetheme{floral}

\begin{document}
\begin{frame}
  \frametitle{Floral}
  The border grows around the text.
\end{frame}
\end{document}
```

`\florasetup{...}` sets the document; `\florathisframe{...}` the next painted
frame, including all its overlays. `\florathispage` is an alias with the same
frame semantics in Beamer. The engine's article API keeps its page semantics.
`\floraon` and `\floraoff` switch the painting off or on before a frame; a
theme may also switch margins with them, which is how title and section
pages keep plain margins.

Both `\usetheme{floral}` and `\usepackage{beamer-floral}` reserve 2.5 cm on
the left and 1 cm on the right by default. These are the package's floral
margins, not Beamer's narrower inherited margins. The latter give the border
too little room and should be avoided. To customise the space, call
`\setbeamersize` after loading the theme or package.

Theme authors that restore a pre-floral layout on undecorated frames should
capture that layout before requiring `beamer-floral`, since loading it now
establishes the floral margins.

The flora stays fixed through a frame's overlays. The package collects the
union of their measured text regions in a `.floral-cache` file beside the
build outputs. LuaLaTeX requests a rerun when that geometry changes;
`latexmk` runs the necessary passes. On a first uncached run the decoration
is provisional. Keep floral settings, reservations, margins and on/off state
constant within a frame; change them before the next frame. An `againframe`
replay gets a new garden, and `allowframebreaks` continuations each get their
own. Split-layout parity follows those logical frame invocations rather than
the overlay page counter. Settings queued while flora is off remain pending
until a frame is painted.

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

## Screenshots

### The theme on its own

![Warm palette](docs/img/palette-warm.png)

*Warm palette: a gold hero, warm blooms and earth foliage. The block accent
is momiji, the alert yama-budo and the example yama-guri.*

![Blue palette](docs/img/palette-blue.png)

*Blue palette: blooms, leaves and leaflets in the iroshizuku blues. Alerts
use murasaki-shikibu and examples tsuki-yo.*

![Green palette](docs/img/palette-green.png)

*Green palette: blue blooms with green foliage. Alerts use edo-murasaki and
examples chiku-rin.*

![Title page](docs/img/title.png)

*A title page with the left layout: the flora fills the left margin and the
foot, leaving the right margin paper.*

### Layout and density

![Left layout](docs/img/layout-left.png)

*`layout=left`: the flora grows in the left margin and across the top and foot; the right margin is paper.*

![Surround layout](docs/img/layout-surround.png)

*`layout=surround`: the crown stops under the running head and the foot
closes the border.*

![Light density](docs/img/density-light.png)

*`density=0.6`: more paper between the stems and blooms.*

![Dense](docs/img/density-dense.png)

*`density=2.0`: a fuller margin with the same layout and seed.*

## With a stock theme

Themes with sidebars or other theme content in the page margins, such as
Berkeley, are **not visually supported**: their margin panels can cover the
flora. The package warns when a Beamer sidebar is present. Prefer floral or a
theme with free side margins; alternatively switch the flora off on those
frames.

Load the stock theme first and beamer-floral after it:

```tex
\usetheme{Madrid}
\usepackage{beamer-floral}
\florasetup{seed=3, density=1.2}
```

The package defaults to `header=body`: it measures the frame title and
starts the flora below it, while the stock theme keeps its own header,
block, alert and example colours. The border and stems are the floral
package's own.

Use `header=margin` when the theme leaves room in the left margin and you
want the hero beside the title instead:

```tex
\florasetup{header=margin, layout=surround}
```

`\usetheme{floral}` selects margin mode itself.

![Madrid with beamer-floral](docs/img/stock-madrid.png)

*Madrid keeps its blue header and block colours; the flora starts below the
frame title.*

![Berlin with beamer-floral](docs/img/stock-berlin.png)

*Berlin keeps its headline and footline; the flora fills the side margins
below the title.*

![Default beamer with beamer-floral](docs/img/stock-default.png)

*The default theme with body mode: the border starts below the title.*

## Long titles

![A long title about floral composition](docs/img/title-long.png)

*A long title and supporting subtitle share the page with the border. This
page comes from the same English visual template used for acceptance tests.*

## Settings

| Key | Values |
|---|---|
| `layout` | `left`, `right`, `centered`, `split`, `title`, `surround` |
| `header` | `body`, `margin` |
| `seed` | a number, or `random` |
| `density` | `0`–`10` |
| `mix` | `{leaves=3, leaflets=2, ...}` |
| `visitors` | weight for bees, butterflies, birds, snails |
| `palette` | `{hero=gold, blooms=blue, ...}` |
| `spin` | re-pick random inks |
| `ornaments` | `{moon=2, night=0, ...}` |
| `tune` | engine overrides, e.g. `{compose={hero=0.295}}` |

Named palettes:

```tex
\florapalette{warm}         % gold, warm blooms, earth foliage
\florapalette{blue}         % gold hero, blue blooms and foliage
\florapalette{green}        % gold hero, blue blooms, green foliage
\florapalette{green-stems}  % as green, with green stems
```

With `\usetheme{floral}`, `\florapalette` also sets the block title,
alert, example and description-label colours. Alerts take a deeper ink
from the same family: yama-budo for warm, murasaki-shikibu for blue,
edo-murasaki for green. A stock theme keeps its own block colours.

## Choosing the composition

Start with `layout=left` or the package's `surround` default. `right`,
`centered` and `split` need enough room on each painted side: changing the
layout does not exchange the package's 2.5 cm left and 1 cm right margins.
Set deliberate custom margins after loading when exploring these layouts.
Use the demonstrated left-layout title page before trying `layout=title`;
that engine layout crowns measured text and is not selected by `\titlepage`.

A quieter, foliage-led composition uses existing engine settings:

```tex
\florasetup{density=0.6, mix={leaves=2, bloom=0, soft=0, lily=0,
  ghost=0, umbel=0, cyme=0, gyps=0}}
```

A custom palette changes the flora; it does not automatically redefine the
Floral theme's block, alert or text colours. Set those with `\setbeamercolor`
when designing a custom colour scheme:

```tex
\florasetup{palette={hero=kon-peki, blooms=warm, leaves=teal}}
```

`ornaments={...}` adjusts the relative weights of registered ornament kinds,
not explicit positions. To suppress a whole slot, set every kind in that slot
to zero. For example, the header slot has four kinds:

```tex
\florasetup{ornaments={compass=0, rosette=0, sunburst=0, quatrefoil=0}}
```

Visitors are optional accents. Keep them sparse, for example
`\florasetup{visitors=0.2, mix={bird=0, snail=0}}`. With a fixed seed,
`palette={blooms=random}` and `spin=1` explore another ink without moving
stems or blossoms. Keep settings constant across a frame's overlays.

The engine's `\florasheet{3}` and `\floragallery[1]`, inside a
`tikzpicture`, are design reference sheets. Inspect them separately rather
than shrinking an entire sheet onto a presentation slide.

## Optional list markers and dividers

![Optional floral list markers](docs/img/ornament-lists.png)

*The optional list templates use the same rosette at all three depths.
The current text size and Beamer item colour determine their appearance.*

![Optional floral divider](docs/img/ornament-divider.png)

*The divider is centred in the text block with a nominal width of half
the current line width.*

The Floral theme keeps circle markers by default. Select the optional
ornament templates independently:

```tex
\setbeamertemplate{itemize item}[floral]
\setbeamertemplate{itemize subitem}[floral]
\setbeamertemplate{itemize subsubitem}[floral]
\floralornamentsetup{item=gilt_rosette, subitem=gilt_rosette,
  subsubitem=gilt_rosette, width=.85em, height=.85em, baseline=.18em,
  seed=3, color=., divider=fleuron_rule, divider width=0.5\linewidth,
  divider height=1em, divider baseline=0pt, divider color=.,
  divider skip=\medskipamount}
```

These are the defaults: all three list depths use the same rosette.
Set `subitem=gilt_trefoil` or `subsubitem=gilt_lozenge`, for example,
to choose other forms independently. `\floraldivider` inserts a centred ornament with
space above and below. Dimensions are nominal drawing-box dimensions;
the engine includes paint reach in the actual TeX box. The baseline is
measured above the nominal box bottom. `color=.` follows the current text
colour; explicit xcolor expressions are also accepted. Settings obey TeX
groups, so a local variant need not change later slides. Registered ornament
names are accepted, but detailed cartouches are unsuitable at bullet size.
The templates use the engine's isolated seed and do not change frame flora.

These commands belong to `\usetheme{floral}`. The generic package preserves
stock-theme list templates. In particular, kau-tex’s `sola-floral` loads
only `beamer-floral` and retains its own list markers. For custom
stock-theme integrations, the engine
also exposes `\floraornament[width=1em,height=1em,baseline=0pt,seed=1,color=.]{gilt_rosette}`.
The optional templates require tikz-flora commit `28c394a` or later.
See the [comparison fixture](test/visual/README.md#optional-ornament-comparison)
for visual review; these candidates do not establish projection readability.

### Alternative forms and colours

![Alternative list markers](docs/img/ornament-options-lists.png)

*Rosettes, trefoils and lozenges at the same nominal size. The lozenge has
finer strokes and needs particular care at projected size.*

After selecting the floral templates above, choose a shape with
`\floralornamentsetup{item=gilt_trefoil}` (or `gilt_rosette` or
`gilt_lozenge`). `item` changes the first depth; `subitem` and
`subsubitem` independently change the other depths.

![Different shapes by depth](docs/img/ornament-options-depths.png)

```tex
\floralornamentsetup{item=rosette, subitem=gilt_trefoil,
  subsubitem=gilt_lozenge, color=blue!70!black}
```

*The header ornament `rosette` is a pointed form, distinct from the smaller
four-dot `gilt_rosette`. Explicit colours override the inherited Beamer ink.*

![Alternative dividers](docs/img/ornament-options-dividers.png)

The first divider uses the defaults. The other two use:

```tex
\floralornamentsetup{divider=swash, divider width=.35\linewidth,
  divider height=1em, divider color=blue!70!black}
\floraldivider
\floralornamentsetup{divider=headpiece, divider width=.7\linewidth,
  divider height=1.2em, divider color=green!40!black}
\floraldivider
```

All three catalogue images come from the executable English
[configuration catalogue](test/visual/ornament-catalogue.tex).
Its background flora is disabled to make the individual shapes easy to compare.

## Reserving space

Keep the flora out of a rectangle with paper coordinates in points, origin
at the lower-left corner:

```tex
\florareserve{0}{0}{\the\paperwidth}{\the\dimexpr 1cm\relax}
\floraclearreserve
```

This is useful for a footline, a logo or a caption. Reservations persist
until `\floraclearreserve`; set and clear them between frames, not between
overlays. They clip the flora and preserve the underlying background.
`\florabackground[bottom]{blue!10}{1cm}` adds a band before the flora;
use height `0pt` to disable it. A reservation protects content over that band.
Neither command measures a logo automatically.

## Development

See [CONTRIBUTING.md](CONTRIBUTING.md) for contribution and commit-message conventions.

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
reusable [visual template](test/visual/README.md):

```sh
python3 tools/visual_suite.py --engine ../tikz-flora
```

This produces comparison PDFs, a page guide, contact sheets and build
diagnostics under `build/visual-review/`. Stock-theme warnings trigger matching
builds without floral to help identify regressions. Inspect the output before
approving changes; compilation success alone is insufficient.

Use `--screenshots docs/img` to refresh all documentation screenshots from
those acceptance and documentation PDFs. All example content is English.

## Licence

MIT; see [LICENSE](LICENSE). The engine dependency retains its own MIT
licence and acknowledgements.
