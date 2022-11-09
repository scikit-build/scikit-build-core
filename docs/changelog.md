# Changelog

## Version 0.1.0a1

This release brings a lot of further development. This is starting to be used by
downstream projects; it is a good idea to be a little careful with versions
still, configuration may change.

## What's Changed

- feat(pyproject): allow python packages to be specified by @henryiii in
  https://github.com/scikit-build/scikit-build-core/pull/58
- feat(pyproject): autocopy packages if names match by @henryiii in
  https://github.com/scikit-build/scikit-build-core/pull/53
- feat(pyproject): include/exclude by @henryiii in
  https://github.com/scikit-build/scikit-build-core/pull/59
- feat(pyproject): Color status messages for wheel by @henryiii in
  https://github.com/scikit-build/scikit-build-core/pull/60
- feat(pyproject): support reproducible sdist builds by @agoose77 in
  https://github.com/scikit-build/scikit-build-core/pull/64
- feat: cmake_source_dir from scikit-build classic by @henryiii in
  https://github.com/scikit-build/scikit-build-core/pull/45
- feat: extra_tags by @henryiii in
  https://github.com/scikit-build/scikit-build-core/pull/49
- feat: prettier logging with config setting by @henryiii in
  https://github.com/scikit-build/scikit-build-core/pull/40
- feat: support for setting python & abi tag (including limited API) by
  @henryiii in https://github.com/scikit-build/scikit-build-core/pull/47
- feat: use setup keyword support by @henryiii in
  https://github.com/scikit-build/scikit-build-core/pull/42

- fix: avoid copy, avoid failure if pre-existing by @henryiii in
  https://github.com/scikit-build/scikit-build-core/pull/41
- fix: better support for FindPython by @henryiii in
  https://github.com/scikit-build/scikit-build-core/pull/38
- fix: fallback to make if available (setting) by @henryiii in
  https://github.com/scikit-build/scikit-build-core/pull/57
- fix: handle `PermissionError` in reading `libdir.is_dir()` by @agoose77 in
  https://github.com/scikit-build/scikit-build-core/pull/43
- fix: include `--config` when installing by @henryiii in
  https://github.com/scikit-build/scikit-build-core/pull/61
- fix: incorrect min version of macOS by @henryiii in
  https://github.com/scikit-build/scikit-build-core/pull/50
- fix: lists and bool settings by @henryiii in
  https://github.com/scikit-build/scikit-build-core/pull/56
- fix: mkdir for sdist if missing, test polish by @henryiii in
  https://github.com/scikit-build/scikit-build-core/pull/44
- fix: simple example PyPy support workaround by @henryiii in
  https://github.com/scikit-build/scikit-build-core/pull/37

- refactor(pyproject): tags configuration group by @henryiii in
  https://github.com/scikit-build/scikit-build-core/pull/55
- refactor(setuptools): use native bdist_wheel setting for abi3 by @henryiii in
  https://github.com/scikit-build/scikit-build-core/pull/52
- refactor: rename `cmake_settings` to `skbuild_settings` by @henryiii in
  https://github.com/scikit-build/scikit-build-core/pull/46

* chore(pyproject): refactor wheel code a bit to read better by @henryiii in
  https://github.com/scikit-build/scikit-build-core/pull/65

- chore: better logging on macOS for deployment target by @henryiii in
  https://github.com/scikit-build/scikit-build-core/pull/48
- chore: format cmake files by @henryiii in
  https://github.com/scikit-build/scikit-build-core/pull/54

* tests: reproducible by @henryiii in
  https://github.com/scikit-build/scikit-build-core/pull/66

## Version 0.1.0a0

First experimental snapshot.
