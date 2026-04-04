# AI Instructions

## Overview

**scikit-build-core**: Python 3.8+ adaptor for CMake 3.15+ to be used with
Python package builds.

---

## Core Commands

### Setup

If `uv`, `nox`, and `prek` commands are not available, they can be installed
from PyPI:

```bash
pip install uv prek nox
```

### Test & Lint

```bash
uv run pytest        # run tests
prek -a              # run all lint/format hooks
```

### Build

```bash
uv build
```

### Docs (only if needed)

```bash
nox -s docs
```

### Other things

```bash
nox -s pylint          # A bit slower than the normal lints
nox -t gen             # Several generation steps, like parts of the README
nox -s tests -- --cov  # A way to run coverage
```

---

---

## Development Workflow

1. Run baseline if needed:

   ```bash
   uv run pytest
   prek -a
   ```

2. Make changes

3. Validate:

   ```bash
   prek -a
   uv run pytest
   ```

4. If API/docs changed:

   ```bash
   nox -s docs
   ```

---

## PR Requirements

- Tests pass: `uv run pytest`
- Lint passes: `prek -a`

---

## Key Notes

- Python ≥3.8 (uses modern syntax)
- Pre-commit handles formatting, linting, typing
- Tests are a bit slow
