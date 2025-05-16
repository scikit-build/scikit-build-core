# Scikit-build-core

Scikit-build-core is a complete ground-up rewrite of scikit-build on top of
modern packaging APIs. It provides a bridge between CMake and the Python build
system, allowing you to make Python modules with CMake.

:::{admonition} Scikit-build community meeting

We have a public Scikit-build community meeting every month!
[Join us on Google Meet](https://meet.google.com/hzu-znrd-uef) on the third
Friday of every month at 12:00 PM EST. We also have a developer's meeting on the
first Friday of every month at the same time. Our past meeting minutes are
[available here](https://github.com/orgs/scikit-build/discussions/categories/community-meeting-notes).

:::

## Features

```{include} ../README.md
:start-after: <!-- SPHINX-START -->
```

## Contents

```{toctree}
:maxdepth: 2
:titlesonly:
:caption: Guide

guide/getting_started
guide/cmakelists
guide/dynamic_link
guide/crosscompile
guide/migration_guide
guide/build
guide/faqs
```

```{toctree}
:maxdepth: 1
:titlesonly:
:caption: Configuration

configuration/index
configuration/overrides
configuration/dynamic
configuration/formatted
configuration/search_paths
```

```{toctree}
:maxdepth: 1
:titlesonly:
:caption: Plugins

plugins/setuptools
plugins/hatchling
```

```{toctree}
:maxdepth: 1
:titlesonly:
:caption: About project

about/projects
about/changelog
```

```{toctree}
:maxdepth: 1
:titlesonly:
:caption: API docs

api/scikit_build_core
schema
reference/configs
reference/cli
```

## Indices and tables

- {ref}`genindex`
- {ref}`modindex`
- {ref}`search`

Generated using scikit-build-core {{ version }}.
