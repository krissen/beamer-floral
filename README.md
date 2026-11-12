# beamer-floral

Procedural watercolour flora for [beamer](https://ctan.org/pkg/beamer),
drawn by [tikz-flora](https://github.com/wn-mitch/tikz-flora). Each slide
gets its own generated plant; the text block is measured so the flora
grows around the content and the margin follows the page.

![The flora growing on a title page](docs/img/growth-title.gif)

```tex
\documentclass{beamer}
\usetheme{floral}
\begin{document}
\begin{frame}{Floral}
  The border grows around the text.
\end{frame}
\end{document}
```

Compile with `latexmk -lualatex`. The [tour](docs/src/tour.tex) is a complete
presentation of the package, written with it.

## Getting started

You need LuaLaTeX and the engine,
[tikz-flora](https://github.com/krissen/tikz-flora). This package uses
integration hooks that are not in the upstream engine yet; they are
[proposed upstream](https://github.com/wn-mitch/tikz-flora/issues/2). Until
they land, use the `beamer-floral` branch of the fork, commit `39cfd26` or
later. The options below all take care of that.

### From the release archive

The simplest way. Download `beamer-floral-v0.1.0.zip` from the
[latest release](https://github.com/krissen/beamer-floral/releases/latest),
which includes a matching engine. Unzip it, put your document in the
`beamer-floral` folder and compile:

```sh
latexmk -lualatex slides.tex
```

The folder has working examples: `example.tex` for static flora and
`growth-example.tex` for growth.

### On Overleaf

Upload the ZIP as a new project, set the compiler to LuaLaTeX and choose your
main document. Static flora, overlay growth and vector playback compile
directly. [Raster playback](docs/user/growth.md) needs a cache built locally.

### From a Git checkout

Clone this repository and the engine's `beamer-floral` branch, then point TeX
at both when you compile:

```sh
git clone https://github.com/krissen/beamer-floral
git clone -b beamer-floral https://github.com/krissen/tikz-flora
TEXINPUTS=$PWD/beamer-floral:$PWD/tikz-flora/tex//: \
  FLORA_LUA=$PWD/tikz-flora/lua latexmk -lualatex slides.tex
```

To work on the package itself, put `TIKZFLORA=/path/to/tikz-flora` in a
gitignored `.env`; the repository's `latexmkrc` reads it.

## Documentation

Guides for writing presentations:

- [Settings](docs/user/settings.md): every key with its values and default,
  palettes, composition, layouts and the cache files
- [Growing flora](docs/user/growth.md): growth across overlays, timed
  playback, raster and GIF
- [Reusing one drawing](docs/user/reuse.md): faster builds and smaller PDFs
  for long decks
- [Layout and page types](docs/user/layout.md): the stage, section pages,
  long titles, the running-head mark and reserved space
- [Themes](docs/user/themes.md): the floral theme, and a stock theme with the
  package
- [Optional list markers and dividers](docs/user/ornaments.md)
- [Patterns](docs/user/patterns.md): geometric patterns instead of flora
  (experimental)

For developers:

- [Development](docs/dev/development.md): building, testing, CI, the engine
  pin, tools and bundles
- [Performance](docs/dev/performance.md): build times and file sizes, and how
  to repeat the measurements
- [Contributing](CONTRIBUTING.md): commit-message conventions

The [manual](docs/beamer-floral.tex) is the standalone reference; the CTAN
archive carries it as a PDF. The
[tour](https://github.com/krissen/beamer-floral/releases/latest/download/beamer-floral-tour.pdf)
is a presentation of the package written with it.

## Licence

MIT; see [LICENSE](LICENSE). The engine dependency retains its own MIT
licence and acknowledgements.
