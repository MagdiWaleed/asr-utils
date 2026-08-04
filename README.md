# asr-utils

Private, personal monorepo of reusable packages shared across projects.
Each category is its own installable package with its own version, so
projects pin only what they use.

```
packages/
  normalization/         asr-normalization
  noise_simulation/       asr-noise-simulation
```

## Use in another project

Install one package, pinned to its own tag, via subdirectory:

```
pip install "git+ssh://git@github.com/<you>/asr-utils.git@normalization-v0.1.0#subdirectory=packages/normalization"
```

## Add a new category

```
packages/<name>/
  pyproject.toml   # name="asr-<name>", version="0.1.0"
  src/asr_<name>/__init__.py
  tests/
```

## Release a package

Bump its `pyproject.toml` version, then tag `<name>-v<version>`
(e.g. `normalization-v0.2.0`) and push the tag. Only that package's
tag changes — other packages stay pinned to their own tags.
