# beamer-floral

Procedural watercolour flora for [beamer](https://ctan.org/pkg/beamer),
drawn by [tikz-flora](https://github.com/krissen/tikz-flora). Each slide
gets its own generated plant; the text block is measured so the flora
grows around the content and the margin follows the page.

## Requirements

- LuaLaTeX
- the [krissen/tikz-flora](https://github.com/krissen/tikz-flora) fork,
  branch `beamer-floral`, commit `4dd4812` or later. The upstream engine
  predates the beamer hooks and tune keys this package uses. CI pins
  `818e50d`.

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
`\floraon` and `\floraoff` switch the flora and its margins before a
frame, which is how title and section pages keep plain margins.

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

*A title page with the crown held at the top (`top_inset=0`), so the border
frames the page instead of underlining a running head.*

### Layout and density

![Left layout](docs/img/layout-left.png)

*`layout=left`: the flora grows in the left margin and along the foot.*

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
\florasetup{layout=surround, seed=3}
```

The stock theme keeps its own header, block, alert and example colours;
beamer-floral adds the plants and the palette. If the theme has no header
bar, set `gesture.top_inset` so the crown starts below the frame title:

```tex
\florasetup{tune={gesture={top_inset=28}}}
```

![Madrid with beamer-floral](docs/img/stock-madrid.png)

*Madrid keeps its blue header and block colours; the flora grows around the
text block.*

![Berlin with beamer-floral](docs/img/stock-berlin.png)

*Berlin keeps its headline and footline; the flora fills the side margins.*

![Default beamer with beamer-floral](docs/img/stock-default.png)

*The default theme with `top_inset=28`: the crown sits between the frame
title and the first block.*

## Settings

| Key | Values |
|---|---|
| `layout` | `left`, `right`, `centered`, `split`, `title`, `surround` |
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

`\florapalette` also sets the block title, alert, example and
description-label colours. Alerts take a deeper ink from the same family:
yama-budo for warm, murasaki-shikibu for blue, edo-murasaki for green.

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

CI checks out the pinned engine, runs its layout and reserve tests, and
builds `test/smoke.tex` with LuaLaTeX. The `tune` keys are validated by the
engine against its tuner index, so a typo names the key and its valid
siblings.

The documentation screenshots are built from `docs/src/*.tex` with the same
commands.

## Licence

The engine dependency is MIT; this package's licence is to be decided
before a CTAN release.
