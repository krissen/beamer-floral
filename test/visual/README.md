# Reusable visual acceptance suite

`template.tex` is the common document: short through very long title pages,
wrapping frame titles/subtitles, untitled/plain frames, blocks, nested lists,
columns, tables, changing-title overlays and palette changes.

Build the comparison set (Python 3, Pillow, LuaLaTeX/latexmk and Poppler):

```sh
python3 tools/visual_suite.py --engine ../tikz-flora
```

PDFs go to `build/visual-review/`, with a page guide, contact sheets and logs.
The default matrix covers floral alone and seven stock themes, in 16:9 and
4:3, using the package's own spacious defaults. Use `--themes floral Madrid` for a
smaller subset, `--jobs 3` to set concurrency, and `--output /tmp/my-review`
to choose the result folder. Stock-theme diagnostics trigger matching builds
without floral to help attribute introduced warnings.
Use `--aspects 169` to inspect one aspect ratio, and `--force` to rebuild a
selected case after changing a template.
The command fails for compilation errors or diagnostics absent from the
matching baseline. Existing stock-theme warnings remain visible in the
report and baseline PDFs; they are not silently suppressed.

For a single editable document, copy the template to the repository root and
compile with `latexmk -lualatex`. Defaults are floral, 16:9 and the package's
own margins. To select another case, define `\VisualTheme` and `\VisualAspect`
before `\input{test/visual/template.tex}`. Keep the theme
before the floral package when adapting it to your own presentation.

Inspect both PDFs and diagnostics. Successful compilation alone does not
approve a result; introduced overfull boxes or visible collisions need fixes.
All example text is English and discusses the visual design itself. The PDFs
and individual page previews can therefore also supply project screenshots.
The column scene uses Beamer's `onlytextwidth` option to keep its content
inside the margins reserved for text.
To update the documentation screenshots from exactly these acceptance PDFs:

```sh
python3 tools/visual_suite.py --engine ../tikz-flora --screenshots docs/img
```

Sidebar themes such as Berkeley are not part of the recommended matrix: their
panels cover the floral margin. Narrow inherited Beamer margins are likewise
unsuitable and are not offered as an example configuration.


## Optional ornament comparison

`ornaments.tex` compares three list depths, wrapping text, four palettes and
an explicit divider. The baseline uses circles. To select the experimental
Floral templates, define `\FloralMarkers` before input; define
`\VisualAspect` as `43` for the other aspect ratio. The optional templates
require the engine's public `\floraornament` command.

```tex
\def\FloralMarkers{1}
\def\VisualAspect{169}
\input{test/visual/ornaments.tex}
```

The theme exposes each template independently:

```tex
\setbeamertemplate{itemize item}[floral]
\setbeamertemplate{itemize subitem}[floral]
\setbeamertemplate{itemize subsubitem}[floral]
```

`\floraldivider` inserts a centred fleuron rule in the current text colour.
These are opt-in review candidates; the generic package does not replace
stock-theme templates. Export comparison images from these PDFs. Inspect
projected-size readability and diagnostics before adopting the templates.

The optional ornament README screenshots come from pages 2 and 9 of the
16:9 ornament comparison, after rebuilding with current settings:

```sh
pdftocairo -f 2 -l 2 -png -singlefile -scale-to 1800 build/ornament-review/169-floral.pdf docs/img/ornament-lists
pdftocairo -f 9 -l 9 -png -singlefile -scale-to 1800 build/ornament-review/169-floral.pdf docs/img/ornament-divider
```

These two optional images are exported separately from the main visual
suite's `--screenshots` matrix.

## Configuration catalogue

`ornament-catalogue.tex` supplies the three README option images, showing
list shapes, per-depth selection and divider styles. Background flora is
disabled to isolate the ornaments. Build and export from repository root:

```sh
latexmk -lualatex -outdir=build/ornament-catalogue test/visual/ornament-catalogue.tex
pdftocairo -f 1 -l 1 -png -singlefile -scale-to 1800 build/ornament-catalogue/ornament-catalogue.pdf docs/img/ornament-options-lists
pdftocairo -f 2 -l 2 -png -singlefile -scale-to 1800 build/ornament-catalogue/ornament-catalogue.pdf docs/img/ornament-options-depths
pdftocairo -f 3 -l 3 -png -singlefile -scale-to 1800 build/ornament-catalogue/ornament-catalogue.pdf docs/img/ornament-options-dividers
```
