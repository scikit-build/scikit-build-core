# Changelog

## Version 0.1.0rc2

Still preparing for release. One small addition to the error printout.

# ## What's Changed

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
