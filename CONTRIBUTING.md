# Contributing

See the [README](README.md#development) for build requirements and checks.

## Checks

`.github/workflows/ci.yml` is the list of what is built and checked, and a
pull request must pass it. It checks out the engine at the revision in
`engine-ref.txt`; the `pre_compile` step runs the Lua and Python unit checks
in `test/` (after linking the engine's `lua/` directory as `./lua`), then every
document in `root_file` is compiled with LuaLaTeX, and the `post_compile`
step checks the logs and PDFs and builds the raster and GIF animations through
`tools/build_animation.py`. Run the same commands against your own engine
checkout, for example `TIKZFLORA=../tikz-flora latexmk -lualatex
test/smoke.tex`. CI skips changes that touch only `.md` and image files, and
does not build the manual: after changing `docs/beamer-floral.tex`, run
`latexmk -lualatex beamer-floral.tex` in `docs/`.

## Engine pin

`engine-ref.txt` names the tikz-flora commit the package is tested with. Every
"`<commit>` or later" requirement in the sources and documents names that
commit. `test/engine-pin.py` fails on a requirement that names another
commit, and when the number of requirements per file changes, so a moved pin
updates `engine-ref.txt` and all of them in one commit. Measured figures in
`docs/performance.md` state the engine they were measured with.

## Commit messages

Use Conventional Commits for all commits, including amended commits:

```text
type(scope): imperative summary
```

The scope is optional. Follow the existing history for types and scopes;
common types are `feat`, `fix`, `docs`, `test`, `refactor`, `build`, `ci`,
and `chore`. Write concise English summaries starting with a lowercase verb
and describe the actual change.

Examples:

```text
fix(header): keep untitled frames below the headline
docs: explain the default floral margins
```

Mark breaking changes to public interfaces or documented behavior with `!`
or a `BREAKING CHANGE:` footer. Check the format before committing and retain
it when amending. Pull request titles intended for squash merging should use
the same format.
