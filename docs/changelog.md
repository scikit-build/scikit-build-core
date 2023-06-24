# Changelog

## Version 0.4.7

This version fixes a unused variable message in 0.4.6, along with a debug
logging improvement, and a few test fixes, including a regression in the recent
noxfile reworking.

- fix: remove `SKBUILD_STATE` unused message when building by @henryiii in #401
- fix: logging environment should use reprs by @henryiii in #409

Tests and CI:

- Support running tests with `NO_COLOR` by @henryiii in #407
- `noxfile.py` added to mypy, two fixes by @henryiii in #408
- Get packages of interest from `pyproject.toml` by @henryiii in #402
- Enable more tests in the spec file by @LecrisUT in #400

## Version 0.4.6

This release has one small new feature (access to `${SKBUILD_STATE}` from
CMake), and fixes an issue when adding read-only files on Windows with Python
3.7. Some testing and docs infrastructure updates should make it easier for
downstream packagers to ship scikit-build-core.

Fixes:

- Provide access to current state in CMake by @henryiii in #394
- Support building older versions of `setuptools_scm` by @henryiii in #390
- Workaround for Windows Python 3.7 `TemporaryDirectory` bug by @henryiii in
  #391

Tests:

- Rework testing extras by @henryiii in #395 and #393
- Add `network` marker by @henryiii in #379

CI:

- Add example tests to Fedora packaging by @LecrisUT in #378
- Fedora: Correct rsync rule by @LecrisUT in #389
- Use `not network` for spec by @henryiii in #383

Docs:

- Add migration guide by @vyasr in #356
- Support building the documentation as a man page by @henryiii in #372
- Add nanobind example by @henryiii in #375
- Use `UseSWIG` for swig by @henryiii in #377
- Fix or hide nitpicks by @henryiii in #370

## Version 0.4.5

This version fixes issues with output being incorrectly interleaved with logging
messages. Symlinks are now followed when making SDists. And finally,
`SKBUILD_SOABI` is now correctly set when cross-compiling on Windows (Warning!
FindPython still does not report the correct SOABI when cross-compiling to ARM).

Fixes:

- Proper printout ordering and more displayed details by @henryiii in #365
- Sort `RUNENV` debugging log output by @jameslamb in #357
- Follow symlinks when making SDists by @henryiii in #362
- Report correct ABI when cross-compiling by @henryiii in #366

Tests:

- Fedora downstream CI by @LecrisUT in #358
- Add downstream examples by @henryiii in #363
- Add testing for scripts processing by @henryiii in #364

## Version 0.4.4

This version fixes some issues cross-compiling to Windows ARM when making
Limited API / Stable ABI extensions, and supports multiple config generators in
editable mode.

- Conditional ABI3 logic fixed by @henryiii in #352
- Set `Python_SABI_LIBRARY` by @henryiii in #352
- Editable installs now support multiconfig generators by @henryiii in #353

## Version 0.4.3

This adds support for CPython 3.12.0b1, and improves Stable ABI / Limited API
support (supported by an upcoming nanobind for Python 3.12). An editable install
fix allows running from any directory.

Fixes:

- Allow CMake to detect if limited API is targeted by @henryiii in #333 and #342
- Make abi3 support conditional on Python version by @henryiii in #344
- Windows path correction for 3.12.0b1 by @henryiii in #346
- Editable path needs to be absolute by @henryiii in #345

Other:

- Add 3.12.0b1 by @henryiii in #341
- Refactor settings by @henryiii in #338
- Document that `CMAKE_ARGS` supports space separators by @henryiii in #339

## Version 0.4.2

This is a quick followup to LICENSE file handing to closer match the current
draft of [PEP 639](https://peps.python.org/pep-0639). It also removes the
automatic optional Rich logging, which doesn't work well with Pip's subprocess
piping, being cropped to a very narrow width regardless of terminal size.

Fixes:

- Add `License-file` metadata entry & update default by @henryiii in #329
- Drop optional Rich logging/error by @henryiii in #330

Other:

- Update PyPI links by @henryiii in #331

## Version 0.4.1

A fix for LICENCE files being placed in the wrong place in the wheel. Now we
follow hatchling's structure of placing them in `*.dist-info/licenses`.

Fixes:

- LICENCE files were placed in the wrong place by @henryiii in #325

Other:

- Fix rpm inspect test failures by @LecrisUT in #324

## Version 0.4.0

An important fix/feature: LICENSE files were not being included in the wheel's
metadata folder. You can configure the license file selection via a new
configuration option, and a reasonable default was added. You can now select a
source directory for your CMakeLists.txt. A lot of work was done on the still
experimental setuptools backend; it still should be seen as completely
experimental while it is being finished.

Features:

- `cmake.source-dir` for CMakeLists in subdirectories by @henryiii in #323
- Add `LICENSE` file option by @henryiii in #321

Fixes:

- Ninja wasn't being used if present by @henryiii in #310
- Wheels were not including the `LICENSE` file by @henryiii in #321

Setuptools plugin:

- Refactor plugin as custom setuptools command by @henryiii in #312
- Adding `cmake_args` by @henryiii in #314
- Add wrapper for `skbuild.setup` compat by @henryiii in #315

Other:

- Add rpmlint and smoke tests by @LecrisUT in #313

## Version 0.3.3

This version improves WebAssembly support (Pyodide) and fixes a reported bug in
the new editable mode.

Fixes:

- Support prefix dir if toolchain has `CMAKE_FIND_ROOT_PATH_MODE_PACKAGE ONLY`
  by @henryiii in #303
- Find wheel files before local files in editable installs by @henryiii in #305

Other:

- Use PyPI's new trusted publisher deployment by @henryiii in #306

## Version 0.3.2

Some small fixes for edge cases. Several docs improvements, too.

Fixes:

- Suppress Unicode errors in scripts dir and move on by @henryiii in #294
- Specify platform properly for non-MSVC Windows by @henryiii in #295

Docs:

- Doc updates by @zerothi in #287
- Add a bit to plugin instructions by @henryiii in #289
- Typos fixed by @afh in #291 and #292

## Version 0.3.1

This is a small release fixing a regression in some cases caused by adding
`Python_LIBRARY`. This has been reverted on non-Windows platforms, since it is
only needed on Windows.

Fixes:

- Support older setuptools-scm by @henryiii in #284
- Only set the lib for FindPython on Windows by @henryiii in #285

Docs:

- Fix incorrect tool name by @henryiii in #276
- Typo on tab Fortran (was Cython) by @zerothi in #279
- Fix wheel.packages by @henryiii in #282

Other:

- Change Fedora PR targets by @LecrisUT in #273

## Version 0.3.0

This version brings two new dynamic metadata plugins (wrappers for
`setuptools_scm` & `hatch-pypi-fancy-readme`). Third-party packages can now add
entry-points declaring `CMAKE_PREFIX_DIR` and `CMAKE_MODULE_DIR` entries.
Support has been added for requesting metadata without building. And
experimental support was added for editable installs, including an option for
automatic rebuilds.

Several fixes have been added as well, like SABI support, ARM cross-compiling
support for FindPython, scripts entries now process shebang lines, and setting a
`build-dir` with `{wheel_tag}` was not working before. The docs have been
started, with a quickstart for common situations, a page on configuration, and
some info on authoring a CMakeLists.

Features:

- Support dynamic metadata by @bennyrowland in #197 and rework by @henryiii in
  #251
- Support modules/prefix dirs by @henryiii in #255
- Add `get_requires_for_dynamic_metadata` by @henryiii in #235
- Make setuptools wrapper more generic by @henryiii in #225
- Experimental support for editable installs by @henryiii in #212, #268, and
  #271

Fixes:

- CMake 3.26.0 (exactly) needs the backport too by @henryiii in #238
- Add python library artifact for better Windows cross compiling by @henryiii in
  #263
- Include 3.26.1 SABI fix by @henryiii in #227
- Restructure `get_requires` & fix some ninja paths by @henryiii in #250
- Support script rewriting by @henryiii in #254
- Version not a string (typing updates) by @henryiii in #231
- `{wheel_tag}` was not working by @henryiii in #262
- `CMAKE_PREFIX_DIR` and `CMAKE_MODULE_DIR` are passed in the init cache file to
  remove a unused variable warning by @henryiii in #272
- Support color printouts without Rich (pip requires `FORCE_COLOR`) by @henryiii
  in #266

Other things:

- Add Fortran testing and CI by @henryiii in #86
- Avoid internet usage in non-isolated testing by @henryiii in #247
- Add an SDist checker & fix contents by @henryiii in #253
- Add more setuptools types by @henryiii in #233
- Add FedoraProject rpm spec file by @LecrisUT in #201 and #241
- Better coverage handling by @henryiii in #270

## Version 0.2.2

This release makes a small improvement to the wheel file permissions (in line
with wheel 0.40). It also ensures the test suite will still pass in an
environment with `SOURCE_DATE_EPOCH` already set. A few internal changes are
paving the way to 0.3.0.

Fixes:

- zipinfo should report regular files by @henryiii in #220

Tests:

- Support running in environments with `SOURCE_DATE_EPOCH` set by @LecrisUT in
  #221
- Report self version too by @henryiii in #222

Other things:

- refactor: use `from_pyproject` by @henryiii and @bennyrowland in #224
- chore: fix a mypy complaint on Windows by @henryiii in #217
- docs: add quickstart by @henryiii in #226

## Version 0.2.1

This release fixes the tag for Windows ARM wheels, and has some internal
refactoring to prepare for the next new features. A new `{wheel_tag}` value is
available for `build-dir`. Some basic setup was done on the docs, as well. Debug
logging and test output has been improved a little, as well.

Changes:

- Add `{wheel_tag}` for `build-dir` by @henryiii in #207
- Support for conda's `CMAKE_SYSTEM_PROCESSOR` by @henryiii in #207

Fixes:

- Windows ARM tag by @henryiii in #215
- Include Windows ARM in known wheels by @henryiii in #203
- Print out paths by @henryiii in #205

Other things:

- docs: update readme for 3.26 backport by @henryiii in #206
- tests: support running tests with system `cmake3` visible by @LecrisUT in #211
- tests: nicer exit, minor refactors by @henryiii in #213
- refactor: minor changes & nicer environment logging printout by @henryiii in
  #214

## Version 0.2.0

This version adds local build directory support - you can now set `build-dir`
and reuse build targets. This does not yet default to on, so please test it out.
This can dramatically speed up rebuilds. If you want to mimic setuptools, you
can set this to `build/{cache_tag}`. Or you can chose some other directory, like
scikit-build classic's `_skbuild`. Along with this, we now have a native wheel
writer implementation and support `prepare_metadata_for_build_wheel`.

Scikit-build-core now also contains a backport of FindPython from CMake 3.26,
which fixes SOABI on PyPy and supports the Stable ABI / Limited API.

Features:

- Local build directory setting & build reuse by @henryiii in #181
- Add `prepare_metadata_for_build_wheel` by @henryiii in #191
- Native wheel writer implementation by @henryiii in #188
- Use 3.26 dev version port of FindPython by @henryiii in #102

Tests:

- Allow pytest 7.0+ instead of 7.2+ by @henryiii in #200
- Include cmake and ninja if missing in nox by @henryiii in #190
- Simpler pytest-subprocess by @henryiii in #159

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

Fixes:

- Ninja path not being set correctly by @henryiii in #166
- Minor touchup to ninja / make by @henryiii in #167

## Version 0.1.4

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

Features:

- Did you mean? for config-settings and pyproject.toml by @henryiii in #135

Testing:

- Split up isolated and virtualenv fixtures by @henryiii in #134

## Version 0.1.0rc1

Preparing for a non-beta release.

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

Fixes:

- Expand macos tags missing by @henryiii in #105

Other things:

- Add tests marker for PEP 518 by @henryiii in #104
- Require C++11 only in tests by @henryiii in #106
- Xfail a non-important test by @henryiii in #107

**Full Changelog**:
https://github.com/scikit-build/scikit-build-core/compare/v0.1.0b1...v0.1.0b2

## Version 0.1.0b1

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
