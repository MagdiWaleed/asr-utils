---
name: update
description: >
  Release a new version of one package in this asr-utils monorepo: bumps
  pyproject.toml version, writes packages/<name>/versions/<version>.md
  documenting what changed since the last version, runs tests, keeps
  packages/<name>/example.py and example.md current and in sync with
  each other, output verified, commits, and (after confirmation) tags
  and pushes. Use when the user says "/update <package>", "release
  <package>", "bump <package> version", or "new version of <package>".
---

Release one package under `packages/<name>/`. Args: `<package>`
(directory name under `packages/`) and either a bump keyword
(`major`/`minor`/`patch`) or an explicit version (`2.1.0`). If the user
gives neither, ask.

## Steps

1. **Resolve the package.** `packages/<package>/pyproject.toml` must
   exist. If not, list `packages/*/` and ask which one they meant.

2. **Read current version** from `[project] version` in that
   `pyproject.toml`.

3. **Find the last release tag** for this package:
   `git tag -l '<package>-v*' --sort=-v:refname | head -1`
   (may be none, if this is the first release).

4. **Compute the new version.** Explicit version: use as given. Bump
   keyword: semver bump off the current version (`major` resets
   minor/patch to 0, `minor` resets patch to 0, `patch` increments last
   number only). A namespace/import-path change or any change that
   breaks existing callers is always `major`, regardless of what the
   user asked for, tell them why if they asked for less.

5. **Summarize what changed** since the last release tag (or since the
   package's first commit if no tag exists):
   `git diff <last-tag>..HEAD -- packages/<package>/ ':!packages/<package>/versions'`
   Read the actual diff, don't guess from memory. Write plain bullet
   points: what was added, changed, removed, fixed. Call out breaking
   changes first and explicitly, with a before/after code snippet if
   the import path or a function signature changed.

6. **Write the changelog file** at
   `packages/<package>/versions/<new-version>.md`:
   ```
   # <new-version>

   Changed from <old-version>:

   - ...
   ```
   If that file already exists, stop and ask before overwriting, don't
   silently clobber a hand-written entry.

7. **Bump `pyproject.toml`** version field to `<new-version>`.

8. **Run the package's tests** if `packages/<package>/tests/` exists:
   fresh venv, `pip install -e packages/<package>`, run each
   `test_*.py`. All must pass. If any fail, stop, report the failure,
   do not commit a broken release. Clean up the venv after.

9. **Keep both `packages/<package>/example.py` and `example.md` current
   and in sync** — same set of examples, in the same order, in both.
   If neither exists yet, create both:
   - `example.py`: runnable (`python example.py`), a `main()` with one
     call per example, plain `print(...)`, no inline output comments.
   - `example.md`: starts with a "Function signatures" section showing
     every public function's full signature (all params, verbatim from
     source) so the whole API is visible before any example, including
     the literal value of any dict/list default (e.g. `MAP_LETTERS`).
     Then one section per param/behavior, each a fenced ```python```
     block ending in a `# ->` comment with its real output.
   - For any param that takes a dict/list override (like `map_letters`),
     both files show an add example **and** a remove example, not just
     add.

   If they already exist, check whether this release's diff added,
   removed, or changed a parameter/behavior they cover (or should now
   cover) and update both, including the signatures section in
   `example.md`.

   Either way, **never write an output you haven't actually run.** In
   the same venv as step 8, run `example.py` itself and use its real
   stdout, in order, as the `# ->` values in `example.md` — that also
   proves the two files agree, don't hand-copy outputs from memory or
   from a separate throwaway script. Fix anything that doesn't match.
   Clean up the venv after.

10. **Commit** `pyproject.toml`, the new `versions/<version>.md`, and
    `example.py`/`example.md` if either changed (plus any other
    already-staged changes for this package): `Bump <dist-name> to
    <new-version>`, one-line body only if the bump is breaking (state
    what breaks).

11. **Confirm before publishing.** Show the commit and the changelog
    entry, ask before tagging/pushing, this touches the shared remote
    other projects install from. On yes:
    ```
    git push origin main
    git tag <package>-v<new-version>
    git push origin <package>-v<new-version>
    ```
    Never move or force-push an existing tag, if `<package>-v<new-version>`
    already exists on the remote, stop and ask.
