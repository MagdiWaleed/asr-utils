# asr-utils

Reusable utilities for automatic speech-recognition (ASR) projects.
Each category is its own installable package with its own version, so
projects pin only what they use.

```
packages/
  normalization/         asr-normalization      v1.1.0
  noise_simulation/      asr-noise-simulation    v0.1.0 (skeleton, no code yet)
```

## Install

Tag the release first, see "Release a package" below, then:

**normalization**
```
pip install "git+https://github.com/MagdiWaleed/asr-utils.git@normalization-v1.1.0#subdirectory=packages/normalization"
```
```python
from asr_normalization import normalize_text, normalize_numbers
```

**noise_simulation** (skeleton only, nothing to import yet)
```
pip install "git+https://github.com/MagdiWaleed/asr-utils.git@noise_simulation-v0.1.0#subdirectory=packages/noise_simulation"
```

Drop `@<tag>` to track `main` instead of a pinned release.

## Add a new category

```
packages/<name>/
  pyproject.toml   # name="asr-<name>", version="0.1.0"
  src/asr_<name>/__init__.py
  tests/
```

## Release a package

Bump its `pyproject.toml` version, then tag `<name>-v<version>` and push:

```
git tag normalization-v1.1.0
git push origin normalization-v1.1.0
```

Only that package's tag changes, other packages stay pinned to their own tags.
