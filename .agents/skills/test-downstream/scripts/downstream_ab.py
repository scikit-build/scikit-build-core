#!/usr/bin/env python3
"""A/B downstream build check for scikit-build-core.

Builds one downstream project twice per mode: once against a released tag
(baseline) and once against the current checkout (your working tree, dirty
changes included). Both go through `nox -s downstream` so the harness matches
what a human would run by hand.

Both sides run in their own detached git worktree, so each gets a private
`.nox/downstream/` venv and clone tree. That isolation matters: the downstream
session installs scikit-build-core into `.nox` and clones the project under
`.nox/downstream/tmp/`, so two A/B runs sharing a checkout would `rm -rf` and
reinstall over each other mid-build. The current worktree is a faithful copy of
the working tree — the tracked diff vs HEAD plus untracked (non-ignored) files
are replayed into it — so dirty changes are still what's on trial.

The signal that matters is *parity*: a mode that built on the baseline but
fails on the current checkout is a regression your change introduced. Wheel
contents and log warnings are secondary, heuristic signals — full logs are
always kept so nothing is hidden.
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path


def run(
    cmd: list[str], *, check: bool = False, **kw: object
) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, text=True, check=check, **kw)


def capture(cmd: list[str], **kw: object) -> str:
    return subprocess.run(
        cmd, text=True, capture_output=True, check=True, **kw
    ).stdout.strip()


def add_worktree(repo: Path, dest: Path, ref: str) -> None:
    run(
        ["git", "-C", str(repo), "worktree", "add", "--detach", str(dest), ref],
        check=True,
    )


def remove_worktree(repo: Path, dest: Path) -> None:
    run(["git", "-C", str(repo), "worktree", "remove", "--force", str(dest)])


def replay_working_tree(repo: Path, dest: Path) -> None:
    """Make `dest` (a worktree at HEAD) match the repo's dirty working tree.

    Applies uncommitted tracked changes (staged + unstaged vs HEAD) and copies
    untracked, non-ignored files. Ignored paths like `.nox` are left out.
    """
    diff = subprocess.run(
        ["git", "-C", str(repo), "diff", "HEAD", "--binary"],
        text=True,
        capture_output=True,
        check=True,
    ).stdout
    if diff.strip():
        applied = subprocess.run(
            ["git", "-C", str(dest), "apply", "--whitespace=nowarn"],
            input=diff,
            text=True,
            check=False,
        )
        if applied.returncode != 0:
            sys.exit(
                "failed to replay uncommitted tracked changes into current worktree"
            )

    listing = subprocess.run(
        ["git", "-C", str(repo), "ls-files", "--others", "--exclude-standard", "-z"],
        text=True,
        capture_output=True,
        check=True,
    ).stdout
    for rel in filter(None, listing.split("\0")):
        src, dst = repo / rel, dest / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        if src.is_symlink() or src.is_file():
            shutil.copy2(src, dst, follow_symlinks=False)


def latest_release_tag(repo: Path) -> str:
    """Latest published release (not a prerelease). Prefer gh, fall back to tags."""
    try:
        return capture(
            ["gh", "release", "view", "--json", "tagName", "-q", ".tagName"], cwd=repo
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        pass
    tags = capture(
        ["git", "tag", "-l", "v*", "--sort=-v:refname"], cwd=repo
    ).splitlines()
    for tag in tags:
        # Skip prereleases (rc/a/b/dev suffixes after the version).
        if not any(x in tag for x in ("rc", "a", "b", "dev")):
            return tag
    if tags:
        return tags[0]
    sys.exit("No version tags found; pass --tag explicitly.")


def nox_downstream(
    workdir: Path,
    project: str,
    *,
    editable: bool,
    subdir: str | None,
    config_settings: list[str],
    code: str | None,
    requires: list[str],
    prepare: str | None,
    extra: list[str],
    logpath: Path,
) -> int:
    """Run one `nox -s downstream` invocation, teeing combined output to logpath."""
    posargs: list[str] = [project]
    if subdir:
        posargs += ["--subdir", subdir]
    if editable:
        posargs.append("--editable")
        if code:
            posargs += ["-c", code]
    for c in config_settings:
        posargs += ["-C", c]
    for r in requires:
        posargs += ["--requires", r]
    if prepare:
        posargs += ["--prepare", prepare]
    posargs += extra
    cmd = ["nox", "-s", "downstream", "--", *posargs]

    with logpath.open("w") as log:
        log.write(f"$ (cwd={workdir}) {' '.join(cmd)}\n\n")
        log.flush()
        proc = subprocess.Popen(
            cmd,
            cwd=workdir,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        assert proc.stdout is not None
        for line in proc.stdout:
            sys.stdout.write(line)
            log.write(line)
        return proc.wait()


def find_wheel(workdir: Path) -> Path | None:
    tmp = workdir / ".nox" / "downstream" / "tmp"
    wheels = sorted(tmp.rglob("*.whl"), key=lambda p: p.stat().st_mtime)
    return wheels[-1] if wheels else None


def wheel_names(wheel: Path) -> set[str]:
    with zipfile.ZipFile(wheel) as zf:
        return set(zf.namelist())


def heuristic_warnings(log: Path) -> set[str]:
    """Lines that look like scikit-build-core / cmake diagnostics, for eyeballing."""
    out: set[str] = set()
    keys = ("scikit_build_core", "scikit-build", "skbuild", "cmake")
    signals = ("warn", "deprecated", "deprecation", "error")
    for raw in log.read_text(errors="replace").splitlines():
        low = raw.lower()
        if any(s in low for s in signals) and any(k in low for k in keys):
            out.add(raw.strip())
    return out


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("project", help="git URL or local path (forwarded to nox)")
    p.add_argument("--tag", help="baseline tag (default: latest release)")
    p.add_argument("--subdir", help="subdirectory to build (nox --subdir)")
    p.add_argument(
        "--mode",
        default="build,editable",
        help="comma list: build,editable (default both)",
    )
    p.add_argument("-C", dest="config_settings", action="append", default=[])
    p.add_argument("-c", dest="code", help="import check code (editable mode only)")
    p.add_argument(
        "--requires",
        action="append",
        default=[],
        help="extra package(s) to install into the build env (repeatable), "
        "e.g. a dynamic-metadata provider like hatch-fancy-pypi-readme",
    )
    p.add_argument(
        "--prepare",
        help="repo-local prep command run in the clone root before the build "
        "(e.g. 'nox -s prepare'); see SKILL.md for the container safety rule",
    )
    p.add_argument(
        "--repo", type=Path, help="scikit-build-core repo (default: git root of cwd)"
    )
    p.add_argument(
        "--out", type=Path, help="output dir for logs/summary (default: temp)"
    )
    p.add_argument(
        "--keep", action="store_true", help="keep both worktrees for inspection"
    )
    p.add_argument(
        "extra", nargs="*", help="extra args forwarded to git clone (e.g. --branch X)"
    )
    args = p.parse_args()

    repo = (
        args.repo or Path(capture(["git", "rev-parse", "--show-toplevel"]))
    ).resolve()
    tag = args.tag or latest_release_tag(repo)
    modes = [m.strip() for m in args.mode.split(",") if m.strip()]
    out = (args.out or Path(tempfile.mkdtemp(prefix="downstream-ab-"))).resolve()
    out.mkdir(parents=True, exist_ok=True)

    print(f"repo:     {repo}")
    print(f"baseline: {tag}")
    print(f"project:  {args.project}")
    print(f"modes:    {', '.join(modes)}")
    print(f"logs:     {out}\n")

    base_wt = out / "_baseline_worktree"
    cur_wt = out / "_current_worktree"
    add_worktree(repo, base_wt, tag)
    add_worktree(repo, cur_wt, "HEAD")
    replay_working_tree(repo, cur_wt)

    results: dict[tuple[str, str], int] = {}
    wheels: dict[str, set[str]] = {}
    try:
        for label, workdir in (("baseline", base_wt), ("current", cur_wt)):
            for mode in modes:
                print(f"\n===== {label} / {mode} =====")
                rc = nox_downstream(
                    workdir,
                    args.project,
                    editable=(mode == "editable"),
                    subdir=args.subdir,
                    config_settings=args.config_settings,
                    code=args.code,
                    requires=args.requires,
                    prepare=args.prepare,
                    extra=args.extra,
                    logpath=out / f"{label}-{mode}.log",
                )
                results[(label, mode)] = rc
                if mode == "build" and rc == 0:
                    wheel = find_wheel(workdir)
                    if wheel:
                        wheels[label] = wheel_names(wheel)
    finally:
        if not args.keep:
            remove_worktree(repo, base_wt)
            remove_worktree(repo, cur_wt)

    # ---- Report ----
    lines: list[str] = ["# Downstream A/B report", ""]
    lines.append(f"- project: `{args.project}`")
    lines.append(f"- baseline tag: `{tag}`  vs  current checkout")
    lines.append("")
    lines.append("| mode | baseline | current | verdict |")
    lines.append("| --- | --- | --- | --- |")
    regressed = False
    for mode in modes:
        b = results.get(("baseline", mode))
        c = results.get(("current", mode))
        bs = "ok" if b == 0 else f"FAIL({b})"
        cs = "ok" if c == 0 else f"FAIL({c})"
        if b == 0 and c != 0:
            verdict = "🔴 REGRESSION"
            regressed = True
        elif b != 0 and c == 0:
            verdict = "🟢 fixed"
        elif b != 0 and c != 0:
            verdict = "⚪ both fail"
        else:
            verdict = "✅ parity"
        lines.append(f"| {mode} | {bs} | {cs} | {verdict} |")
    lines.append("")

    if "baseline" in wheels and "current" in wheels:
        added = sorted(wheels["current"] - wheels["baseline"])
        removed = sorted(wheels["baseline"] - wheels["current"])
        if added or removed:
            lines.append("## Wheel contents changed (build mode)")
            lines += [f"- + `{f}` (only in current)" for f in added]
            lines += [f"- - `{f}` (only in baseline)" for f in removed]
        else:
            lines.append("## Wheel contents: identical file list ✅")
        lines.append("")

    for mode in modes:
        bl = out / f"baseline-{mode}.log"
        cl = out / f"current-{mode}.log"
        if bl.exists() and cl.exists():
            new = sorted(heuristic_warnings(cl) - heuristic_warnings(bl))
            if new:
                lines.append(
                    f"## New scikit-build-core diagnostics in current ({mode}) — heuristic"
                )
                lines += [f"- {w}" for w in new[:40]]
                lines.append("")

    lines.append(f"Full logs: `{out}`")
    report = "\n".join(lines)
    (out / "summary.md").write_text(report + "\n")
    print("\n" + report)
    return 1 if regressed else 0


if __name__ == "__main__":
    raise SystemExit(main())
