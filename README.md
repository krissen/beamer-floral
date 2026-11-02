# beamer-floral

Procedural watercolour flora for [beamer](https://ctan.org/pkg/beamer),
drawn by [tikz-flora](https://github.com/krissen/tikz-flora). Each slide
gets its own generated plant; the text block is measured so the flora
grows around the content and the margin follows the page.

## Requirements

- LuaLaTeX
- the [krissen/tikz-flora](https://github.com/krissen/tikz-flora) fork,
  branch `beamer-floral`, commit `2c1fc8e` or later. The upstream engine
  lacks the header modes and tune keys this package uses. CI pins the same
  commit.

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

`\florasetup{...}` sets the document; `\florathispage{...}` the next page.
`\floraon` and `\floraoff` switch the painting off or on before a frame; a
theme may also switch margins with them, which is how title and section
pages keep plain margins.

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

![A long Linné-inspired title](docs/img/title-long.png)

*Titles wrap inside the title block. The flora is measured against the text
and grows around it; this deliberately long Linné-inspired title leaves the
border in the margins.*

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

```sh
latexmk -lualatex test/smoke.tex
```

CI checks out the pinned engine, runs its layout tests, and builds
`test/smoke.tex`, `test/stock.tex` and `test/titles.tex` with LuaLaTeX. The
`tune` keys are validated by the engine against its tuner index, so a typo
names the key and its valid siblings.

Most documentation screenshots are built from `docs/src/*.tex` with the same
commands; the long-title image comes from `test/titles.tex`.

## Licence

The engine dependency is MIT; this package's licence is to be decided
before a CTAN release.
