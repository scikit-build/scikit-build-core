---
name: test-downstream
description: >-
  Test a downstream project against scikit-build-core to check whether the
  current checkout regresses it versus a released baseline. Builds the project
  twice per mode — once against a released tag (baseline, via a git worktree)
  and once against the working tree — in both a normal wheel build and an
  editable install, then reports parity, wheel-content, and warning diffs. Use
  this whenever the user wants to test/build/try a downstream or real-world
  project against their changes, check that a fix or PR doesn't break
  downstream, run `nox -s downstream`, compare current-vs-released behavior,
  reproduce a downstream build issue, or validate against projects in
  docs/data/projects.toml — even if they only name a project (e.g. "test
  iminuit", "does gemmi still build").
---

# Test a downstream project (baseline vs current)

## What this does and why

scikit-build-core is a build backend, so the failure mode that matters most is
_breaking a project that used to build_. This skill answers one question: does
the current checkout (your uncommitted changes included) build a given
downstream project as well as the last released version did?

It builds the project **twice per mode**, each side in its own detached git
worktree:

- **baseline** — a worktree checked out at a released tag, so installing `.`
  reproduces the released backend.
- **current** — a worktree at HEAD with your uncommitted changes replayed onto
  it (tracked diff vs HEAD + untracked, non-ignored files), so dirty changes are
  still what's on trial.

Both sides get a **private worktree** on purpose. The `downstream` session
installs scikit-build-core into `.nox/downstream/` and clones the project under
`.nox/downstream/tmp/`; two runs sharing one checkout would `rm -rf` and
reinstall over each other mid-build. Separate worktrees give each run its own
`.nox`, so **A/B runs on the same repo are safe to run in parallel**.

…across **both modes** the backend supports: a normal wheel build
(`python -m build`) and an editable install (`pip install -e`). Everything goes
through `nox -s downstream`, the same harness a human uses, so results are
trustworthy and easy to reproduce by hand.

The primary signal is **parity**: a mode that built on the baseline but fails on
the current checkout is a regression you introduced. Wheel-content and warning
diffs are secondary, heuristic signals — full logs are always kept so you can
dig in.

## Preconditions

- Run from inside the scikit-build-core repo (or a worktree of it). The
  "current" side is materialized from whatever `git rev-parse --show-toplevel`
  resolves to — its committed HEAD plus uncommitted changes — so if the user is
  testing changes in a worktree, run there.
- `nox` and `git` on PATH; network access to clone the project; a compiler
  toolchain (these builds actually compile). CMake/Ninja are auto-installed by
  the session if missing.
- Don't stash or commit the user's changes — testing the dirty tree is the
  point.

## Step 1 — Resolve the project

The user usually names a project, not a URL. Resolve it via
`docs/data/projects.toml`, the curated list of known-good downstream projects.
Each entry has:

```toml
[[project]]
pypi = "iminuit"            # what the user is likely to say
github = "scikit-hep/iminuit"   # -> https://github.com/scikit-hep/iminuit
path = "awkward-cpp/pyproject.toml"   # optional -> --subdir awkward-cpp
requires = ["hatch-fancy-pypi-readme"]  # optional -> --requires (repeatable)
prepare = "nox -s prepare"    # optional -> --prepare (repo-local prep command)
```

- The `project` argument to nox is a git URL: `https://github.com/<github>`.
- If `path` is present, pass `--subdir <dirname of path>` (strip the trailing
  `/pyproject.toml`).
- If `requires` is present, forward each as `--requires <pkg>`.
- If `prepare` is present, forward it as `--prepare "<command>"`.

If the user gives a full URL or local path, use it directly. If a named project
isn't in the list, use the obvious GitHub URL and mention it wasn't in the
curated set (it may need submodules or extra clone args).

## Step 2 — Run the A/B check

The bundled script does the whole dance — pick the baseline tag, create and tear
down the worktree, run all four builds, capture logs, and diff results:

```bash
python3 <skill>/scripts/downstream_ab.py <project-url> [--subdir DIR] [-C key=val ...]
```

The baseline tag defaults to the latest published release (via `gh`, falling
back to the newest non-prerelease `v*` tag). Override with `--tag v0.11.6` when
the user names a specific version to compare against.

Useful options (all forwarded to `nox -s downstream`):

- `--subdir DIR` — build a subdirectory (from `path` in projects.toml).
- `-C key=val` — a config-setting, repeatable (e.g. `-C cmake.verbose=true`).
- `-c "import foo; foo.test()"` — import/smoke check, editable mode only.
- `--requires PKG` — extra package to install into the build env, repeatable.
  Use for a scikit-build-core dynamic-metadata provider a project needs but
  doesn't list in `build-system.requires` (e.g. ninja needs
  `--requires hatch-fancy-pypi-readme`, or editable mode fails to find the
  provider). See the safety rule below before using it for system packages.
- `--prepare "CMD"` — a repo-local prep command run once in the clone root
  before configure (and before any `--subdir` chdir). Use for generated sources,
  e.g. awkward-cpp (built from the `awkward-cpp/` subdir) needs the parent
  repo's `--prepare "nox -s prepare"` to produce kernel headers, or CMake fails
  early. **Not for mutating the host** — see below.
- `--mode build` or `--mode editable` — run just one mode instead of both.
- `extra` positional args are forwarded to `git clone` (e.g. `--branch v2`).
- `--keep` — keep the baseline worktree for inspection; `--out DIR` — choose the
  log directory.

Exit code is non-zero if any mode regressed (baseline ok, current failed).

**Example** — test `iminuit` (in projects.toml, no subdir) against the current
checkout, both modes:

```bash
python3 <skill>/scripts/downstream_ab.py https://github.com/scikit-hep/iminuit
```

## Step 3 — Interpret and report

The script prints (and writes to `<out>/summary.md`) a parity table like:

```
| mode     | baseline | current | verdict       |
| build    | ok       | FAIL(1) | 🔴 REGRESSION |
| editable | ok       | ok      | ✅ parity     |
```

Report back to the user concisely:

- **Lead with regressions.** A 🔴 REGRESSION is the headline — the current
  checkout broke a build the release handled. Open the relevant
  `<out>/current-<mode>.log`, find the actual error (not just the nox exit
  line), and quote it. This is where your change is on trial.
- **⚪ both fail** usually means the project needs something the environment
  lacks (a submodule, a system lib) or is already broken upstream — not your
  fault, but say so rather than staying silent.
- **Wheel-content diff** (build mode): files added/removed between baseline and
  current wheels. Often intentional (you changed packaging) — flag it and let
  the user judge.
- **Warning diff** is a keyword heuristic over the logs; treat new lines as
  leads to verify in the full log, not conclusions.

Point the user at the log directory so they can inspect anything you didn't
quote.

## Manual fallback

If the script doesn't fit (a project needs bespoke setup, or you want to iterate
on one mode), the underlying commands are simple. Current checkout — run it
directly in the repo only if nothing else is using its `.nox/downstream/` at the
same time:

```bash
nox -s downstream -- <project-url> [--subdir DIR] [--editable] [-C key=val]
```

Baseline is the same command run from a worktree at the tag:

```bash
git worktree add --detach /tmp/skbc-base v0.12.2
( cd /tmp/skbc-base && nox -s downstream -- <project-url> ... )
git worktree remove --force /tmp/skbc-base
```

The script does this dance for **both** sides (current in a worktree at HEAD
with your dirty changes replayed onto it) so each run has a private `.nox` and
parallel runs don't clobber one another.

`--editable` switches to `pip install -e`; `-c CODE` runs a Python snippet after
an editable install (it errors in build mode). Built wheels land under
`.nox/downstream/tmp/<slug>/[subdir]/dist/`.

## Safety: `--prepare` must not mutate the host

`--prepare` is for **repo-local** prep only — generating sources, running a
project's own `nox -s prepare`, and similar steps scoped to the clone. In normal
use it must never mutate the host system.

**Do NOT run host-mutating commands (`brew install`, `apt-get install`, `sudo`,
etc.) via `--prepare` unless this skill is running inside a container.** Some
projects need system libraries (e.g. spherely needs `s2`); installing those is
only acceptable in a disposable containerized run, never on a developer's
machine. If a project needs a system package and you are not in a container, say
so and stop — do not install it.

## Things that bite

- **Large projects are slow.** Each of the four runs clones fresh and compiles
  from scratch — a big C++ project can take many minutes ×4. Warn the user for
  heavy projects; offer `--mode build` to halve the work, or a smaller project
  to smoke-test first.
- **Submodules.** The session clones with `--recurse-submodules`, but projects
  not in projects.toml may still need extra clone args (pass them as trailing
  `extra` args).
- **Old baseline tags** carry their own noxfile; if a very old tag's
  `downstream` session lacks a flag you passed, the baseline run may fail on
  args — pick a newer `--tag` or drop the flag.
