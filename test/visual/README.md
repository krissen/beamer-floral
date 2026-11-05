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
