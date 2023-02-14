# Changelog

## Version 0.2.0

This version adds local build directory support - you can now set `build-dir`
and reuse build targets. This does not yet default to on, so please test it out.
This can dramatically speed up rebuilds. If you want to mimic setuptools, you
can set this to `build/{cache_tag}`. Or you can chose some other directory, like
scikit-build classic's `_skbuild`. Along with this, we now have a native wheel
writer implementation and support `prepare_metadata_for_build_wheel`.

Scikit-build-core now also contains a backport of FindPython from CMake 3.26,
which fixes SOABI on PyPy and supports the Stable ABI / Limited API.

### What's Changed

Features:

- Local build directory setting & build reuse by @henryiii in #181
- Add `prepare_metadata_for_build_wheel` by @henryiii in #191
- Native wheel writer implementation by @henryiii in #188
- Use 3.26 dev version port of FindPython by @henryiii in #102

Tests:

- tests: allow pytest 7.0+ instead of 7.2+ by @henryiii in #200
- tests: include cmake and ninja if missing in nox by @henryiii in #190
- tests: simpler pytest-subprocess by @henryiii in #159

Other things:

- chore: Python 3.11 Self usage by @henryiii in #199
- chore: fix Ruff configuration by @henryiii in #186
- chore: minor adjustments to wheel returns by @henryiii in #195
- chore: remove duplicate Ruff code by @burgholzer in #184

## Version 0.1.6

### What's changed

Fixes:

- Handle local cmake dir for search by @henryiii in #179
- Avoid resolving cmake/ninja paths by @henryiii in #183

Other things:

- Use Ruff by @henryiii in #175
- Ruff related additions by @henryiii in #180
- Add `isolated` marker to `test_pep518_sdist` by @bnavigator in #182

## Version 0.1.5

### What's Changed

Fixes:

- Ninja path not being set correctly by @henryiii in #166
- Minor touchup to ninja / make by @henryiii in #167

## Version 0.1.4

### What's Changed

Fixes:

- `entrypoints.txt` should be `entry_points.txt` by @njzjz in #161
- `EXT_SUFFIX` is wrong before 3.8.7 by @henryiii in #160
- Make tests pass on native Windows ARM by @henryiii in #157
- Windows ARM experimental cross-compile support by @henryiii in #162

Other things:

- Fix spelling mistake by @maxbachmann in #156
- Add Python 3.12 alpha 3 to the CI by @henryiii in #120
- Fix issues mocking in tests with packaging 22 by @henryiii in #155

## Version 0.1.3

### What's Changed

Fixes:

- Issue with experimental extra directory targeting by @henryiii in #144
- Sort SDist filepaths for reproducibility by @agoose77 in #153

## Version 0.1.2

### What's changed

Features:

- Provide null directory (not installed) by @henryiii in #143

Fixes:

- Fix issue with 32-bit Windows in 0.1.1 by @henryiii in #142

## Version 0.1.1

### What's Changed

Fixes:

- Windows non-default generators by @henryiii in #137
- Compute the correct default generator for CMake by @henryiii in #139

Testing:

- Support make missing by @henryiii in #140
- Clear `CMAKE_GENERATOR` by @henryiii in #141

## Version 0.1.0

First non-prerelease! Scikit-build-core is ready to be used. The remaining
limitations (like support for editable mode and build caching) will be addressed
in future releases. If you set `tool.scikit-build.minimum-version = "0.1"`,
scikit-build-core will try to respect old defaults when new versions are
released.

## Version 0.1.0rc2

Still preparing for release. One small addition to the error printout.

### What's Changed

Features:

- Did you mean? for config-settings and pyproject.toml by @henryiii in #135

Testing:

- Split up isolated and virtualenv fixtures by @henryiii in #134

## Version 0.1.0rc1

Preparing for a non-beta release.

### What's Changed

Fixes:

- Paths on Windows by @henryiii in #126
- Support pre-set generators by @henryiii in #118
- Warn on scripts with invalid shebangs by @henryiii in #132
- Minimum constraints now set by @henryiii in #129

Refactoring:

- Rename pyproject -> build dir by @henryiii in #121

Testing:

- Add msys2 to the CI by @henryiii in #119
- Add test report header by @henryiii in #124
- Test min constraints without Windows by @henryiii in #129
- Remove pytest-virtualenv by @henryiii in #125 and #131
- Mark unimportant test xfail non-strict for conda-forge by @henryiii in #108

## Version 0.1.0b2

A quick fix for macOS universal2 tags not expanding when enabled.

### What's Changed

Fixes:

- Expand macos tags missing by @henryiii in #105

Other things:

- Add tests marker for PEP 518 by @henryiii in #104
- Require C++11 only in tests by @henryiii in #106
- Xfail a non-important test by @henryiii in #107

**Full Changelog**:
https://github.com/scikit-build/scikit-build-core/compare/v0.1.0b1...v0.1.0b2

## Version 0.1.0b1

### What's Changed

This release is focused on preparing for conda-forge and some macOS fixes.

Features:

- Configuration setting for FindPython backport by @henryiii in #103

Fixes:

- Conda prefix lib support by @henryiii in #95
- Guess single config for more generators by @henryiii in #101
- Universal2 tags computation was incorrect by @henryiii in #97
- Universal2 tags computation was incorrect again by @henryiii in #100

Refactoring:

- Rename extra color -> rich by @henryiii in #98

Other things:

- Run more tests without the cmake module by @henryiii in #96
- Support running without pytest-virtualenv by @henryiii in #94

## Version 0.1.0b0

This release adds a lot of configuration options, including `minimum-version`,
which can be set to 0.0 to ensure defaults remain consistent (similar to
`cmake_minimum_required`).

### What's Changed

Features:

- Dict options by @henryiii in #78
- Min version setting by @henryiii in #84
- Strict configuration checking by @henryiii in #75
- Support for args/define by @henryiii in #83
- Support for other wheel dirs by @henryiii in #82
- Support specifying a build type by @henryiii in #90

Fixes:

- Better logging by @henryiii in #88
- Better macOS deployment target handling by @henryiii in #74
- Don't touch mtime in non-reproducible mode by @henryiii in #76
- Fallback to ninja sooner if on known platform by @henryiii in #80

Refactoring:

- Rename CMakeConfig -> CMaker by @henryiii in #91
- Drop config prefix by @henryiii in #77
- Rename to `wheel.py-api` and expand, ignore on non-cpython / old cpython by
  @henryiii in #81

Other things:

- Add cygwin by @henryiii in #89

## Version 0.1.0a1

This release brings a lot of further development. This is starting to be used by
downstream projects; it is a good idea to be a little careful with versions
still, configuration may change.

### What's Changed

Features:

- Allow python packages to be specified by @henryiii in #58
- Autocopy packages if names match by @henryiii in #53
- Include/exclude by @henryiii in #59
- Color status messages for wheel by @henryiii in #60
- Support reproducible sdist builds by @agoose77 in #64
- Prettier logging with config setting by @henryiii in #40
- Add `extra-tags` by @henryiii in #49
- Support for setting python & abi tag (including limited API) by @henryiii in
  #47
- (setuptools) Use setup keyword support by @henryiii in #42
- (setuptools) `cmake_source_dir` from scikit-build classic by @henryiii in #45

Fixes:

- Avoid copy, avoid failure if pre-existing by @henryiii in #41
- Better support for FindPython by @henryiii in #38
- Fallback to make if available (setting) by @henryiii in #57
- Handle `PermissionError` in reading `libdir.is_dir()` by @agoose77 in #43
- Include `--config` when installing by @henryiii in #61
- Incorrect min version of macOS by @henryiii in #50
- Lists and bool settings by @henryiii in #56
- Mkdir for sdist if missing, test polish by @henryiii in #44
- Simple example PyPy support workaround by @henryiii in #37

Refactoring:

- Tags configuration group by @henryiii in #55
- (setuptools) Use native bdist_wheel setting for abi3 by @henryiii in #52
- Rename `cmake_settings` to `skbuild_settings` by @henryiii in #46
- Refactor wheel code a bit to read better by @henryiii in #65

Other things:

- Better logging on macOS for deployment target by @henryiii in #48
- Format cmake files by @henryiii in #54

## Version 0.1.0a0

First experimental snapshot.
