# Entry-point configuration

An installed package can contribute scikit-build-core configuration to _every_
build in the environment through two entry-point groups. This is primarily
intended for Linux distributions and other packagers that need to set build
defaults (such as the CMake build type or symbol stripping) for all packages
without editing each one's `pyproject.toml`.

A provider is a callable that returns a `[tool.scikit-build]`-shaped table:

```{code-block} python
:caption: my_distro_config/__init__.py

def config(*, state, env):
    return {
        "cmake": {"build-type": "RelWithDebInfo"},
        "install": {"strip": False},
    }
```

The callable may also take no arguments; `state` (the build state, e.g.
`"wheel"`) and `env` (the environment mapping) are passed when accepted.

It is registered under one of two groups; the **group** selects the precedence
level, and the entry-point name is arbitrary:

```{code-block} toml
:caption: pyproject.toml of the provider package

[project.entry-points."scikit-build-core.config.default"]
my-distro = "my_distro_config:config"
```

Any installed package registering a provider is picked up automatically; the
project being built does not need to opt in.

## Precedence levels

The group controls where the contributed table lands in the configuration
precedence order:

- **`scikit-build-core.config.default`** — applied _below_ `pyproject.toml`,
  just above the built-in defaults. The provider suggests defaults; the
  project's own configuration always wins. This is the recommended level.
- **`scikit-build-core.config.override`** — applied _above_ `pyproject.toml`, so
  the project cannot accidentally undo it. It is still below the user's
  per-build environment variables and config-settings.

The full precedence order, highest to lowest, is:

1. `SKBUILD_*` environment variables
2. `-C`/config-settings
3. `override` entry-point providers
4. extra settings (build-frontend plugins, e.g. hatchling)
5. `pyproject.toml`
6. `default` entry-point providers
7. built-in defaults

A package may register providers in both groups, and the entry-point name is
free-form. When several providers are registered in the same group, they are
applied in sorted name order and the alphabetically-first name wins on
conflicts.

## Conditional configuration

Because the returned table is treated like a `[tool.scikit-build]` table, it may
contain [`overrides`](./overrides.md). Combined with environment matching, this
lets a provider apply configuration only in the relevant context. For example, a
distribution can request debug-friendly defaults only inside an RPM build:

```{code-block} python
:caption: provider returning conditional config

def config(*, state, env):
    return {
        "overrides": [
            {
                "if": {"env": {"RPM_BUILD_ROOT": True}},
                "cmake": {"build-type": "RelWithDebInfo"},
                "install": {"strip": False},
            }
        ]
    }
```

## Opting out

Set `SKBUILD_NO_ENTRYPOINT_CONFIG=1` to ignore all entry-point providers for a
build, which is useful for reproducible builds or debugging. Loaded providers
are reported in the debug log.
