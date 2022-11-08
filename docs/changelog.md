# Changelog

## Version 0.1.0a1

This is a second experimental snapshot. Two key fixes include better Pyodide
support and corrected macOS minimum version tags. The provisional setuptools
extension is beginning to look more like scikit-build classic with initial
custom keyword support. Two new features include `tool.scikit-build.extra-tags`,
which adds native tags when universal2 is used, and
`tool.scikit-build.py-abi-tag`, which lets you set the tags used to build.
Support for controlling the logging in pyproject mode was added, as well.

## What's Changed

- feat: `extra_tags` by @henryiii in
  https://github.com/scikit-build/scikit-build-core/pull/49
- feat: support for setting python & abi tag (including limited API) by
  @henryiii in https://github.com/scikit-build/scikit-build-core/pull/47
- feat(pyproject): prettier logging with config setting by @henryiii in
  https://github.com/scikit-build/scikit-build-core/pull/40
- feat(setuptools): use setup keyword support by @henryiii in
  https://github.com/scikit-build/scikit-build-core/pull/42
- feat(setuptools): `cmake_source_dir` from scikit-build classic by @henryiii in
  https://github.com/scikit-build/scikit-build-core/pull/45

- fix: incorrect min version of macOS by @henryiii in
  https://github.com/scikit-build/scikit-build-core/pull/50
- fix: avoid copy, avoid failure if pre-existing by @henryiii in
  https://github.com/scikit-build/scikit-build-core/pull/41
- fix: better support for FindPython by @henryiii in
  https://github.com/scikit-build/scikit-build-core/pull/38
- fix: handle `PermissionError` in reading `libdir.is_dir()` by @agoose77 in
  https://github.com/scikit-build/scikit-build-core/pull/43
- fix: mkdir for sdist if missing, test polish by @henryiii in
  https://github.com/scikit-build/scikit-build-core/pull/44
- fix: simple example PyPy support workaround by @henryiii in
  https://github.com/scikit-build/scikit-build-core/pull/37

- chore: better logging on macOS for deployment target by @henryiii in
  https://github.com/scikit-build/scikit-build-core/pull/48
- refactor: rename `cmake_settings` to skbuild_settings by @henryiii in
  https://github.com/scikit-build/scikit-build-core/pull/46

## New Contributors

- @agoose77 made their first contribution in
  https://github.com/scikit-build/scikit-build-core/pull/43

**Full Changelog**:
https://github.com/scikit-build/scikit-build-core/compare/v0.1.0.a0...v0.1.0a1

## Version 0.1.0a0

First experimental snapshot.
