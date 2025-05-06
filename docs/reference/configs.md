# Config Reference

The following are the available configurations in `pyproject.toml` for the
`[tool.scikit-build]` table. These can be passed in one of the following ways

````{tab} pyproject.toml

```toml
[tool.scikit-build]
build.verbose = true
```

````

`````{tab} config-settings

````{tab} pip

```console
$ pip install . --config-settings=build.verbose=true
```

````

````{tab} build

```console
$ pipx run build --wheel -Cbuild.verbose=true
```

````

````{tab} cibuildwheel

```toml
[tool.cibuildwheel.config-settings]
"build.verbose" = true
```

````

`````

````{tab} Environment

```console
$ export SKBUILD_BUILD_VERBOSE="true"
```

````

<!-- [[[cog
from scikit_build_core.settings.skbuild_docs_sphinx import mk_skbuild_docs

print()
print(mk_skbuild_docs())
]]] -->

## (top-level)

```{eval-rst}
.. confval:: build-dir
  :type: ``str``

  The build directory. Defaults to a temporary directory, but can be set.
```

```{eval-rst}
.. confval:: experimental
  :type: ``bool``
  :default: false

  Enable early previews of features not finalized yet.
```

```{eval-rst}
.. confval:: fail
  :type: ``bool``
  :default: false

  Immediately fail the build. This is only useful in overrides.
```

```{eval-rst}
.. confval:: metadata
  :type: ``dict[str,dict[str,Any]]``

  List dynamic metadata fields and hook locations in this table.
```

```{eval-rst}
.. confval:: minimum-version
  :type: ``Version``
  :default: "0.11"  # current version

  If set, this will provide a method for backward compatibility.
```

```{eval-rst}
.. confval:: strict-config
  :type: ``bool``
  :default: true

  Strictly check all config options. If False, warnings will be printed for unknown options. If True, an error will be raised.
```

## backport

```{eval-rst}
.. confval:: backport.find-python
  :type: ``Version``
  :default: "3.26.1"

  If CMake is less than this value, backport a copy of FindPython. Set to 0 disable this, or the empty string.
```

## build

```{eval-rst}
.. confval:: build.requires
  :type: ``list[str]``

  Additional ``build-system.requires``. Intended to be used in combination with ``overrides``.
```

```{eval-rst}
.. confval:: build.targets
  :type: ``list[str]``

  The build targets to use when building the project. Empty builds the default target.
```

```{eval-rst}
.. confval:: build.tool-args
  :type: ``list[str]``

  Extra args to pass directly to the builder in the build step.
```

```{eval-rst}
.. confval:: build.verbose
  :type: ``bool``
  :default: false

  Verbose printout when building.
```

## cmake

```{eval-rst}
.. confval:: cmake.args
  :type: ``list[str]``

  A list of args to pass to CMake when configuring the project. Setting this in config or envvar will override toml. See also ``cmake.define``.
```

```{eval-rst}
.. confval:: cmake.build-type
  :type: ``str``
  :default: "Release"

  The build type to use when building the project. Valid options are: "Debug", "Release", "RelWithDebInfo", "MinSizeRel", "", etc.
```

```{eval-rst}
.. confval:: cmake.define
  :type: ``EnvVar``

  A table of defines to pass to CMake when configuring the project. Additive.
```

```{eval-rst}
.. confval:: cmake.minimum-version
  :type: ``Version``

  DEPRECATED in 0.8; use version instead.
```

```{eval-rst}
.. confval:: cmake.source-dir
  :type: ``Path``
  :default: "."

  The source directory to use when building the project. Currently only affects the native builder (not the setuptools plugin).
```

```{eval-rst}
.. confval:: cmake.targets
  :type: ``list[str]``

  DEPRECATED in 0.10; use build.targets instead.
```

```{eval-rst}
.. confval:: cmake.verbose
  :type: ``bool``

  DEPRECATED in 0.10, use build.verbose instead.
```

```{eval-rst}
.. confval:: cmake.version
  :type: ``SpecifierSet``

  The versions of CMake to allow. If CMake is not present on the system or does not pass this specifier, it will be downloaded via PyPI if possible. An empty string will disable this check. The default on 0.10+ is "CMakeLists.txt", which will read it from the project's CMakeLists.txt file, or ">=3.15" if unreadable or <0.10.
```

## editable

```{eval-rst}
.. confval:: editable.mode
  :type: ``"redirect" | "inplace"``
  :default: "redirect"

  Select the editable mode to use. Can be "redirect" (default) or "inplace".
```

```{eval-rst}
.. confval:: editable.rebuild
  :type: ``bool``
  :default: false

  Rebuild the project when the package is imported. The build-directory must be set.
```

```{eval-rst}
.. confval:: editable.verbose
  :type: ``bool``
  :default: true

  Turn on verbose output for the editable mode rebuilds.
```

## generate[]

```{eval-rst}
.. confval:: generate[].location
  :type: ``"install" | "build" | "source"``
  :default: "install"

  The place to put the generated file. The "build" directory is useful for CMake files, and the "install" directory is useful for Python files, usually. You can also write directly to the "source" directory, will overwrite existing files & remember to gitignore the file.
```

```{eval-rst}
.. confval:: generate[].path
  :type: ``Path``

  The path (relative to platlib) for the file to generate.
```

```{eval-rst}
.. confval:: generate[].template
  :type: ``str``

  The template to use for the file. This includes string.Template style placeholders for all the metadata. If empty, a template-path must be set.
```

```{eval-rst}
.. confval:: generate[].template-path
  :type: ``Path``

  The path to the template file. If empty, a template must be set.
```

## install

```{eval-rst}
.. confval:: install.components
  :type: ``list[str]``

  The components to install. If empty, all default components are installed.
```

```{eval-rst}
.. confval:: install.strip
  :type: ``bool``
  :default: true

  Whether to strip the binaries. True for release builds on scikit-build-core 0.5+ (0.5-0.10.5 also incorrectly set this for debug builds).
```

## logging

```{eval-rst}
.. confval:: logging.level
  :type: ``"NOTSET" | "DEBUG" | "INFO" | "WARNING" | "ERROR" | "CRITICAL"``
  :default: "WARNING"

  The logging level to display, "DEBUG", "INFO", "WARNING", and "ERROR" are possible options.
```

## messages

```{eval-rst}
.. confval:: messages.after-failure
  :type: ``str``

  A message to print after a build failure.
```

```{eval-rst}
.. confval:: messages.after-success
  :type: ``str``

  A message to print after a successful build.
```

## ninja

```{eval-rst}
.. confval:: ninja.make-fallback
  :type: ``bool``
  :default: true

  If Ninja is not present on the system or is older than required, it will be downloaded via PyPI if this is false.
```

```{eval-rst}
.. confval:: ninja.minimum-version
  :type: ``Version``

  DEPRECATED in 0.8; use version instead.
```

```{eval-rst}
.. confval:: ninja.version
  :type: ``SpecifierSet``
  :default: ">=1.5"

  The versions of Ninja to allow. If Ninja is not present on the system or does not pass this specifier, it will be downloaded via PyPI if possible. An empty string will disable this check.
```

## sdist

```{eval-rst}
.. confval:: sdist.cmake
  :type: ``bool``
  :default: false

  If set to True, CMake will be run before building the SDist.
```

```{eval-rst}
.. confval:: sdist.exclude
  :type: ``list[str]``

  Files to exclude from the SDist even if they are included by default. Supports gitignore syntax.
```

```{eval-rst}
.. confval:: sdist.include
  :type: ``list[str]``

  Files to include in the SDist even if they are skipped by default. Supports gitignore syntax.
```

```{eval-rst}
.. confval:: sdist.reproducible
  :type: ``bool``
  :default: true

  If set to True, try to build a reproducible distribution (Unix and Python 3.9+ recommended).  ``SOURCE_DATE_EPOCH`` will be used for timestamps, or a fixed value if not set.
```

## search

```{eval-rst}
.. confval:: search.site-packages
  :type: ``bool``
  :default: true

  Add the python build environment site_packages folder to the CMake prefix paths.
```

## wheel

```{eval-rst}
.. confval:: wheel.build-tag
  :type: ``str``

  The build tag to use for the wheel. If empty, no build tag is used.
```

```{eval-rst}
.. confval:: wheel.cmake
  :type: ``bool``
  :default: true

  If set to True (the default), CMake will be run before building the wheel.
```

```{eval-rst}
.. confval:: wheel.exclude
  :type: ``list[str]``

  A set of patterns to exclude from the wheel. This is additive to the SDist exclude patterns. This applies to the final paths in the wheel, and can exclude files from CMake output as well.  Editable installs may not respect this exclusion.
```

```{eval-rst}
.. confval:: wheel.expand-macos-universal-tags
  :type: ``bool``
  :default: false

  Fill out extra tags that are not required. This adds "x86_64" and "arm64" to the list of platforms when "universal2" is used, which helps older Pip's (before 21.0.1) find the correct wheel.
```

```{eval-rst}
.. confval:: wheel.install-dir
  :type: ``str``

  The install directory for the wheel. This is relative to the platlib root. You might set this to the package name. The original dir is still at SKBUILD_PLATLIB_DIR (also SKBUILD_DATA_DIR, etc. are available). EXPERIMENTAL: An absolute path will be one level higher than the platlib root, giving access to "/platlib", "/data", "/headers", and "/scripts".
```

```{eval-rst}
.. confval:: wheel.license-files
  :type: ``list[str]``

  A list of license files to include in the wheel. Supports glob patterns. The default is ``["LICEN[CS]E*", "COPYING*", "NOTICE*", "AUTHORS*"]``. Must not be set if ``project.license-files`` is set.
```

```{eval-rst}
.. confval:: wheel.packages
  :type: ``list[str]``
  :default: ["src/<package>", "python/<package>", "<package>"]

  A list of packages to auto-copy into the wheel. If this is not set, it will default to the first of ``src/<package>``, ``python/<package>``, or ``<package>`` if they exist.  The prefix(s) will be stripped from the package name inside the wheel. If a dict, provides a mapping of package name to source directory.
```

```{eval-rst}
.. confval:: wheel.platlib
  :type: ``bool``

  Target the platlib or the purelib. If not set, the default is to target the platlib if wheel.cmake is true, and the purelib otherwise.
```

```{eval-rst}
.. confval:: wheel.py-api
  :type: ``str``

  The Python tags. The default (empty string) will use the default Python version. You can also set this to "cp38" to enable the CPython 3.8+ Stable ABI / Limited API (only on CPython and if the version is sufficient, otherwise this has no effect). Or you can set it to "py3" or "py2.py3" to ignore Python ABI compatibility. The ABI tag is inferred from this tag.
```

<!-- [[[end]]] -->
