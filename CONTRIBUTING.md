# Contributing

See the [README](README.md#development) for build requirements and checks.

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
