# CLI Reference

Scikit-build-core has a few integrated CLI tools, useful for scaffolding a
project and investigating your environment.

These are available through the `scikit-build` command (also runnable as
`python -m scikit_build_core`), with the modules exposed as subcommands.

```{program-output} scikit-build

```

## Build utilities

```{program-output} scikit-build build --help

```

### Build requirements

```{program-output} scikit-build build requires --help

```

Example:

```{command-output} scikit-build build requires
:cwd: ../examples/generated/c

```

### Project table

```{program-output} scikit-build build project-table --help

```

Example:

```{command-output} scikit-build build project-table
:cwd: ../examples/generated/c

```

### Config-settings

Lists the config-settings the current project accepts: the built-in
scikit-build-core settings plus any the project declares in
`tool.scikit-build.config-setting`.

```{program-output} scikit-build build config-settings --help

```

## Building environment info

```{program-output} scikit-build builder --help

```

Example:

```{command-output} scikit-build builder

```

### Wheel tag

```{program-output} scikit-build builder wheel-tag --help

```

Example:

```{command-output} scikit-build builder wheel-tag

```

### Sysconfig

```{program-output} scikit-build builder sysconfig --help

```

## File API tools

```{program-output} scikit-build file-api query --help

```

```{program-output} scikit-build file-api reply --help

```

## Starter projects

The `init` command generates a minimal CMake + scikit-build-core project for the
selected binding backend. Run it without `--backend` to pick one interactively.

```{program-output} scikit-build init --help

```
