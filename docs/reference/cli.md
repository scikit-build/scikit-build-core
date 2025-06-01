# CLI Reference

Scikit-build-core has a few integrated CLI tools. These are not guaranteed to be
stable between releases yet, but can still be useful to investigate your
environment.

```{program-output} python -m scikit_build_core

```

## Build utilities

```{program-output} python -m scikit_build_core.build --help

```

### Build requirements

```{program-output} python -m scikit_build_core.build requires --help

```

Example:

```{command-output} python -m scikit_build_core.build requires
:cwd: ../examples/getting_started/c

```

### Project table

```{program-output} python -m scikit_build_core.build project-table --help

```

Example:

```{command-output} python -m scikit_build_core.build project-table
:cwd: ../examples/getting_started/c

```

## Building environment info

```{program-output} python -m scikit_build_core.builder.wheel_tag --help

```

Example:

```{command-output} python -m scikit_build_core.builder.wheel_tag

```

## File API tools

```{program-output} python -m scikit_build_core.file_api.query --help

```

```{program-output} python -m scikit_build_core.file_api.reply --help

```
