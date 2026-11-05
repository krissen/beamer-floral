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

## Reserving space

Keep the flora out of a rectangle with paper coordinates in points, origin
at the lower-left corner:

```tex
\florareserve{0}{0}{\the\paperwidth}{\the\dimexpr 1cm\relax}
\floraclearreserve
```

This is useful for a footline, a logo or a caption. The same mechanism
backs the title-page inset above.

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
