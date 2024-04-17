# Hatchling

A [hatchling][] plugin is being developed for scikit-build-core. This is
currently in a highly experimental state, but feedback is welcome.

:::{warning}

This plugin is experimental, and will probably be moved to a separate package.
If using it, it is highly recommended to upper-cap scikit-build-core until it
moves.

:::

## Basic usage

To use the plugin, make sure hatchling and scikit-build-core are in your
`build-system.requires`. A recent version of hatchling is best; you need 1.23 to
get `cmake` and `ninja` auto-added if needed, and 1.24 if you want to write out
custom scripts, metadata, or shared data.

You need a `tool.hatch.build.targets.wheel.hooks.scikit-build` section to
activate the plugin. Currently, you need at least the `experimental` option to
use the plugin, which means you acknowledge that this might move in the next
release of scikit-build-core. It was added in 0.9.

```toml
[build-system]
requires = ["hatchling", "scikit-build-core~=0.9.0"]
build-backend = "hatchling.build"

[project]
name = "hatchling_example"
version = "0.1.0"

[tool.hatch.build.targets.wheel.hooks.scikit-build]
experimental = true
```

:::{note}

Note that this is equivalent:

```toml
[tool.hatch.build.targets.wheel.hooks.scikit-build]

[tool.scikit-build]
experimental = true
```

:::

## Options

Most of scikit-build-core's configuration can be used with hatchling if it is
applicable. Things like metadata and wheel options generally are not applicable,
unless they pertain to setting the tag (which scikit-build-core controls). You
can specify settings in either
`tool.hatch.build.targets.wheel.hooks.scikit-build` or `tool.scikit-build` or
via environment variables. You cannot use config-settings, as that's not
supported by hatchling for plugins.

Key limitations:

- You need to leave `cmake.wheel` on. No `wheel.platlib = False` builds.
- Using cmake in SDist step is not supported yet.
- Editable installs are not supported yet.
- `scikit-build.generate` and `scikit-build.metadata` is not supported.
- `${SKBUILD_HEADER_DIR}` is not supported, request support in Hatching if
  needed.
- Anything in `${SKBUILD_METADATA_DIR}` must be placed in an `extra_metadata`
  folder.
- Python 3.8 highly recommended as features are missing from the last Hatchling
  to support 3.7.

## Writing CMakeLists.txt

The hatchling version is available as `${SKBUILD_HATCHLING}`.

[hatchling]: https://hatch.pypa.io
