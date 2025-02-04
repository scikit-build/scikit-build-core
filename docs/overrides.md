# Overrides

Scikit-build-core has an override system, similar to cibuildwheel and mypy. You
specify a `tool.scikit-build.overrides` array with an `if` key. That `if` key
can take several values, including several based on [PEP 508][]. Inside the
override, you can set any value `tool.scikit-build` supports, and it will
override if the `if` condition is true.

## If conditions

There are three types of conditions. Booleans, strings, and version numbers.
Booleans take a bool; if the boolean matches the bool you give, the override
matches. If the value is a string (such as an environment variable), it will
match non false-like values, and if the variable is unset or empty, that counts
as false. Strings take a regex which will try to match. Version numbers take a
specifier set, like `>=1.0`.

If multiple conditions are given, they all must be true. Use `if.any` (below) if
you would rather matching on any one of multiple conditions being true.

At least one must be provided. Then you can specify any collection of valid
options, and those will override if all the items in the `if` are true. They
will match top to bottom, overriding previous matches.

If an override does not match, it's contents are ignored, including invalid
options. Combined with the `if.scikit-build-version` override, this allows using
overrides to support a range of scikit-build-core versions that added settings
you want to use.

### `scikit-build-version` (version)

The version of scikit-build-core itself. Takes a specifier set. If this is
provided, unknown overrides will not be validated unless it's a match.

### `python-version` (version)

The two-digit Python version. Takes a specifier set.

Example:

```toml
[[tool.scikit-build.overrides]]
if.python-version = ">=3.13"
wheel.cmake = false
```

### `platform-system` (string)

The value of `sys.platform`. Takes a regex. Like `sys.platform`, you should
allow suffixes. Common values:

| System         | `platform-system` (w/o suffix) |
| -------------- | ------------------------------ |
| AIX            | `aix`                          |
| Android[^1]    | `android`                      |
| FreeBSD        | `freebsd`                      |
| iOS            | `ios`                          |
| Linux          | `linux`                        |
| Mac OS X       | `darwin`                       |
| OpenBSD        | `openbsd`                      |
| Pyodide        | `emscripten`                   |
| WASI           | `wasi`                         |
| Windows        | `win32`                        |
| Windows/Cygwin | `cygwin`                       |
| Windows/MSYS2  | `msys`                         |

[^1]: Before CPython 3.13, this returned `linux`.

Example:

```toml
[[tool.scikit-build.overrides]]
if.platform-system = "^darwin"
cmake.version = ">=3.18"
```

### `platform-machine` (string)

The value of `platform.machine()`. Takes a regex. A few sample values:

| OS      | Machine      | `platform-system` |
| ------- | ------------ | ----------------- |
| Unix    | Intel 64-bit | `x86_64`          |
| Linux   | Intel 32-bit | `i686`            |
| macOS   | ARM          | `arm64`           |
| Linux   | ARM          | `aarch64`         |
| Linux   | Power PC     | `ppc64le`         |
| Linux   | s390x        | `s390x`           |
| Windows | Intel 64-bit | `AMD64`           |
| Windows | Intel 32-bit | `x86`             |
| Windows | ARM          | `ARM64`           |

### `abi-flags` (string)

A sorted list of the ABI flags. `t` is the free-threaded build.

### `platform-node` (string)

The value of `platform.node()`. This is generally your computer's name. Takes a
regex.

### `implementation-name` (string)

The value of `sys.implementation.name`. Takes a regex. Some common values:

| Implementation | `implementation-name` |
| -------------- | --------------------- |
| CPython        | `cpython`             |
| PyPy           | `pypy`                |

### `implementation-version` (version)

Derived from `sys.implementation.version`, following [PEP 508][]. Takes a
specifier set. This is the PyPy version on PyPy, for example.

### `env.*` (string or bool)

A table of environment variables mapped to either string regexs, or booleans.
Valid "truthy" environment variables are case insensitive `true`, `on`, `yes`,
`y`, `t`, or a number more than 0.

Example:

```toml
[[tool.scikit-build.overrides]]
if.env.CI = true
cmake.version = ">=3.30"
```

This is often combined with `if.any`.

:::{versionadded} 0.7

:::

### `state` (string)

The state of the build, one of `sdist`, `wheel`, `editable`, `metadata_wheel`,
and `metadata_editable`. Takes a regex.

Note that you can build directly to wheel; you don't have to go through an
SDist.

:::{versionadded} 0.8

:::

### `from-sdist` (bool)

This will be true if the `PKG-INFO` file exists, that is, if this is coming from
an SDist. Takes a bool.

:::{versionadded} 0.10

:::

### `system-cmake` (version)

This will match if there's a system CMake matching this version specification.

```toml
[[tool.scikit-build.overrides]]
if.system-cmake = ">=3.15"
cmake.version = ""
message.after-success = "Built using a system CMake, not a wheel"
```

:::{versionadded} 0.10

:::

### `cmake-wheel` (bool)

This matches true if a wheel is known to be provided for this platform, and
false otherwise. This is useful for specifying a pure Python fallback on systems
that don't have provided CMake wheels. Ninja wheels are available on all
platforms CMake is, so a separate override for Ninja isn't needed. Often
combined with `system-cmake`.

For example, this would be an optional build only on systems with CMake or
supported by wheels:

```toml
[tool.scikit-build]
wheel.cmake = false

[[tool.scikit-build.overrides]]
if.any.system-cmake = ">=3.15"
if.any.cmake-wheel = true
wheel.cmake = true
```

:::{versionadded} 0.10

:::

### `failed` (bool)

This override is a bit special. If a build fails, scikit-build-core will check
to see if there's a matching `failed = true` override. If there is, the the
build will be retried once with the new settings. This can be used to build a
pure-Python fallback if a build fails, for example:

```toml
[[tool.scikit-build.overrides]]
if.failed = true
wheel.cmake = false
```

:::{versionadded} 0.10

:::

If this override is present in your pyproject.toml file, scikit-build-core will
not provide the `prepare_metadata_*` hooks, as it can't know without building if
the build will fail.

## Any matching condition

If you use `if.any` instead of `if`, then the override is true if any one of the
items in it are true.

If you have both `if` and `if.any` conditions, then all the `if` conditions and
one of the `if.any` conditions must match.

Example:

```toml
[tool.scikit-build]
wheel.cmake = false

[[tool.scikit-build.overrides]]
if.any.env.CIBUILDWHEEL = true
if.any.env.BUILD_MY_LIB = true
wheel.cmake = true
```

Above, either `CIBUILDWHEEL` or `BUILD_MY_LIB` being truthy will trigger a
binary build.

:::{versionadded} 0.7

:::

## Inheriting for tables and arrays

If you specify `inherit.<thing> = "append"` or `"prepend"`, then an override
will append or prepend tables and lists, either from the base configuration or a
previous override. For a table, the difference is apparent when you have
matching keys; `"append"` means the override replaces the old key, while
`"prepend"` will leave the key alone.

Example:

```toml
[tool.scikit-build]
cmake.define.FOO = "0"
cmake.define.BAR = "0"

[[tool.scikit-build.overrides]]
if.env.SET_FOO = "ON"
inherit.cmake.define = "append"
cmake.define.FOO = "1"

[[tool.scikit-build.overrides]]
if.env.SET_BAR = "ON"
inherit.cmake.define = "append"
cmake.define.BAR = "1"
```

In the above example, setting `SET_FOO` will add `FOO` as a define, and likewise
for `SET_BAR` and `BAR`. Without the inherit, setting one would remove the
other, as the table would be replaced. And `"prepend"` wouldn't be useful at
all, since FOO and BAR are already defined, so the original definition would
win.

:::{versionadded} 0.9

:::

[pep 508]: https://peps.python.org/pep-0508/#environment-markers
