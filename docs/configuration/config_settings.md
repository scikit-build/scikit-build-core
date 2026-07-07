# Package config-settings

Packages can declare their own config-settings, giving users a documented,
package-level interface for configuring the build, with no need to expose raw
CMake defines like `-C cmake.define.ZMQ_PREFIX=...`. Declared settings can be
passed as PEP 517 config-settings (`-C name=value`), bound to an environment
variable, and forwarded to CMake.

:::{versionadded} 1.1

:::

## Declaring settings

Each setting is declared in the `tool.scikit-build.config-setting` table. Names
must have at least two dot-separated segments; using your import package name as
the first segment is recommended to avoid clashes with other tools'
config-settings:

```toml
[tool.scikit-build.config-setting."zmq.prefix"]
help = "Prefix to search for libzmq"
env = "ZMQ_PREFIX"
cmake = "ZMQ_PREFIX"

[tool.scikit-build.config-setting."zmq.libzmq"]
help = "Where libzmq comes from"
choices = ["bundled", "system"]
default = "system"
```

The supported keys are:

- `help`: A description of the setting, for documentation purposes.
- `type`: Either `"str"` (default) or `"bool"`. Boolean values are parsed like
  environment variables in overrides (case insensitive `true`, `on`, `yes`, `y`,
  `t`, or a positive number are truthy).
- `default`: The value used when the setting is not passed; must match the type.
  If not set, the setting is "unset" when not passed.
- `env`: An environment variable that is also read for this setting.
- `choices`: A list of allowed string values (`str` type only); other values
  produce an error.
- `cmake`: A CMake cache variable that is set to the resolved value (see below).

Users can then configure the build with either interface:

```console
$ pip install . -Czmq.libzmq=bundled
$ ZMQ_PREFIX=/opt/zmq pip install .
```

The environment variable takes precedence over the config-setting, which takes
precedence over the default (the same ordering used for scikit-build-core's own
settings). Declared names are matched verbatim, are exempt from `strict-config`
validation, and get "did you mean" suggestions when mistyped.

Declaring config-settings requires `minimum-version = "1.1"` (or unset).

## Passing values to CMake

There are two equivalent ways to forward a setting to CMake. The `cmake` key in
the declaration is the most compact:

```toml
[tool.scikit-build.config-setting."zmq.prefix"]
env = "ZMQ_PREFIX"
cmake = "ZMQ_PREFIX"
```

Alternatively, a `cmake.define` entry can reference the setting, similar to the
`{env = ...}` form:

```toml
[tool.scikit-build.cmake.define]
ZMQ_PREFIX = { config-setting = "zmq.prefix" }
```

In both forms, the define is left unset when the setting resolves to no value,
so `if(DEFINED ZMQ_PREFIX)` works in CMake, and an explicit define (in the
static table, an override, `-C cmake.define.NAME=...`, or
`SKBUILD_CMAKE_DEFINE`) wins over the declaration's `cmake` alias.

## Use in overrides

Declared settings can drive [overrides](./overrides.md) with the
`if.config-setting` condition, which matches the resolved value (so `-C` and the
bound environment variable behave identically):

```toml
[[tool.scikit-build.overrides]]
if.config-setting."zmq.libzmq" = "bundled"
cmake.define.ZMQ_LIBZMQ = "ON"
messages.after-success = "{green}Using bundled libzmq"
```

String conditions are regexes; boolean conditions match the truthiness of the
value (unset matches `false`).

:::{note}

Since scikit-build-core versions before 1.1 reject unknown `if` conditions, a
package that must remain buildable with older versions can guard the override
with `if.scikit-build-version = ">=1.1"` (though declaring the settings table
itself already requires 1.1 via `build-system.requires`).

:::

:::{warning}

Some build frontends (like pip) pass the same `-C` settings to every package
built in a single command, so a setting intended for one package may reach
another, where it is unrecognized and rejected under `strict-config`. Prefer
installing such packages in separate commands when passing config-settings.

:::
