---
orphan:
nosearch:
---

# Scikit-build-core

Scikit-build-core is a complete ground-up rewrite of scikit-build on top of
modern packaging APIs. It provides a bridge between CMake and the Python build
system, allowing you to make Python modules with CMake.

## Synopsis

**scikit-build** [*COMMAND*] ...

Scikit-build-core is normally used as a PEP 517 build backend and invoked by a
build frontend such as `pip` or `build`. It also ships a `scikit-build` command
(also runnable as `python -m scikit_build_core`) that exposes a few utilities
for inspecting the build environment:

- **scikit-build build requires** -- show the build requirements.
- **scikit-build build project-table** -- show the project table (with dynamic
  metadata).
- **scikit-build builder** -- show information about the system.
- **scikit-build builder wheel-tag** -- show the computed wheel tag.
- **scikit-build builder sysconfig** -- show information from sysconfig.
- **scikit-build file-api query** -- request the CMake file API.
- **scikit-build file-api reply** -- process the CMake file API.
- **scikit-build init** -- generate a starter project for a binding backend.

See the CLI reference for the full set of options.

## Features

```{include} ../README.md
:start-after: <!-- SPHINX-START -->
```

Generated using scikit-build-core {{ version }}.
