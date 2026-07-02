# Entry-point configuration

> [!CAUTION] This is an advanced feature primarily for Linux distributions and
> other packagers that need to set build defaults, like the CMake build type or
> symbol stripping.

An installed package can contribute scikit-build-core configuration to _every_
build in the environment through two entry-point groups. This can affect all
packages without editing each one's `pyproject.toml`.

A provider is a callable that returns a `[tool.scikit-build]`-shaped table:

```{code-block} python
:caption: my_distro_config/__init__.py

def config(*, state, env):
    return {
        "cmake": {"build-type": "RelWithDebInfo"},
        "install": {"strip": False},
    }
```

Each argument is passed only when the callable accepts it: `state` (the build
state, e.g. `"wheel"`) and `env` (the environment mapping) are matched by
parameter name, and a `**kwargs` provider receives both. A provider may accept
any subset -- both, either one, or none. The callable is invoked exactly once.

The callable is registered under either the `scikit-build-core.config.default`
or the `scikit-build-core.config.override` entry-point group; the group selects
the precedence level. The entry-point name is arbitrary (it only affects
ordering, see below):

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

A package may register providers in both groups. When several providers are
registered in the same group, they are applied in sorted name order and the
alphabetically-first name wins on conflicts.

## Validation

Because entry-point config comes from the machine environment rather than the
project, it is treated like `SKBUILD_*` environment variables and
`-C`/config-settings for validation purposes, not like static `pyproject.toml`
content:

- Override-only fields (such as `cmake.toolchain-file`) may be set directly,
  without wrapping them in an [`overrides`](./overrides.md) block. This is the
  distro cross-compile use case this feature targets.
- The project's `minimum-version` pin does not gate machine-level config, so a
  provider may set newer fields even when a project pins an older
  `minimum-version`.

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

Note that `inherit.append`/`inherit.prepend` in a provider's `overrides` joins
with the provider's _own_ table only. Merging with the project's configuration
happens later, per the precedence order above: tables merge key-by-key across
levels, but a list is taken wholesale from the highest-precedence level that
sets it.

## Opting out

Set `SKBUILD_NO_ENTRYPOINT_CONFIG=1` to ignore all entry-point providers for a
build, which is useful for reproducible builds or debugging. Loaded providers
are reported in the debug log.
