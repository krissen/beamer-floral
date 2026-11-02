# beamer-floral

Procedural watercolour flora for [beamer](https://ctan.org/pkg/beamer),
drawn by [tikz-flora](https://github.com/krissen/tikz-flora). The flowers
are generated, not an image: each page gets its own plant, and the text
block is measured so the flora grows around it.

## Requirements

- LuaLaTeX
- the [krissen/tikz-flora](https://github.com/krissen/tikz-flora) fork,
  branch `beamer-floral`, commit `4dd4812` or later. The upstream engine
  lacks the beamer hooks and tune keys this package uses. CI pins
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
  \frametitle{Flora}
  The border grows around the text.
\end{frame}
\end{document}
```

The theme paints no header colour of its own; the flora supplies the
colour there. Block, example and description-label colours come from the
selected ink palette; alerts are a fixed violet.

## Settings

`\florasetup{...}` sets the document; `\florathispage{...}` the next page.

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

Named palettes: `\florapalette{warm}`, `\florapalette{blue}`,
`\florapalette{green}`, `\florapalette{green-stems}`. `warm` is the
default.

`\floraon` and `\floraoff` switch the flora and the floral margins before
a frame, for title and section pages:

```tex
\floraoff
\begin{frame}\titlepage\end{frame}
\floraon
```

In `layout=surround` the upper crown stops `gesture.top_inset` below the
paper top, so it underlines the running head. A title page whose title is
vertically centred wants the crown back at the top:

```tex
\florathispage{tune={gesture={top_inset=0}}}
\begin{frame}\titlepage\end{frame}
```

Keep the flora out of a rectangle (a footline, a logo, a caption) with
paper coordinates in points, origin at the lower-left corner:

```tex
\florareserve{0}{0}{\the\paperwidth}{\the\dimexpr 1cm\relax}
\floraclearreserve
```

## Development

```sh
latexmk -lualatex test/smoke.tex
```

CI checks out the pinned engine, runs its layout tests and builds
`test/smoke.tex` with LuaLaTeX. The theme's `tune` keys are validated by
the engine against its tuner index, so a typo names the key and its valid
siblings.

## Licence

The engine dependency is MIT; this package's licence is to be decided
before a CTAN release.
