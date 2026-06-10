from pathlib import Path

from scikit_build_core.build._scripts import process_script_dir


def test_script_dir(tmp_path: Path) -> None:
    script_dir = tmp_path / "scripts"
    script_dir.mkdir()
    script_1 = script_dir / "script1"
    script_1.write_text("#!/usr/bin/env python3\n\nprint('hello world')")
    script_1.chmod(0o644)
    orig_mode_1 = script_1.stat().st_mode

    script_2 = script_dir / "script2"
    script_2.write_text("#!/usr/bin/env pypy3\n\nprint('hello world')")
    script_2.chmod(0o755)
    orig_mode_2 = script_2.stat().st_mode

    script_3 = script_dir / "script3"
    script_3.write_text("#!/usr/bin/env pythonw3.11\n\nprint('hello world')")

    script_4 = script_dir / "script4"
    script_4.write_text("#!/usr/bin/python3.11\n\nprint('hello world')")

    script_5 = script_dir / "script5"
    script_5.write_text("#!/usr/bin/other\n\nprint('hello world')")

    script_6 = script_dir / "script6"
    script_6.write_text("#!/usr/bin/env python3.11 other\n\nprint('hello world')")

    script_7 = script_dir / "script7"
    script_7.write_text("#!/usr/bin/env other\n\nprint('hello world')")

    process_script_dir(script_dir)

    assert script_1.read_text(encoding="utf-8") == "#!python\n\nprint('hello world')"
    assert script_1.stat().st_mode == orig_mode_1

    assert script_2.read_text(encoding="utf-8") == "#!python\n\nprint('hello world')"
    assert script_2.stat().st_mode == orig_mode_2

    assert script_3.read_text(encoding="utf-8") == "#!python\n\nprint('hello world')"

    assert script_4.read_text(encoding="utf-8") == "#!python\n\nprint('hello world')"

    assert (
        script_5.read_text(encoding="utf-8")
        == "#!/usr/bin/other\n\nprint('hello world')"
    )

    assert (
        script_6.read_text(encoding="utf-8") == "#!python other\n\nprint('hello world')"
    )

    assert (
        script_7.read_text(encoding="utf-8")
        == "#!/usr/bin/env other\n\nprint('hello world')"
    )


def test_script_dir_with_subdirectory(tmp_path: Path) -> None:
    """
    A subdirectory installed into the scripts dir must be skipped, not opened
    (which would raise IsADirectoryError / PermissionError on Windows).
    """
    script_dir = tmp_path / "scripts"
    script_dir.mkdir()

    script_1 = script_dir / "script1"
    script_1.write_text("#!/usr/bin/env python3\n\nprint('hello world')")

    nested = script_dir / "nested"
    nested.mkdir()
    nested_script = nested / "script2"
    nested_script.write_text("#!/usr/bin/env python3\n\nprint('nested')")

    # Must not raise on the subdirectory.
    process_script_dir(script_dir)

    assert script_1.read_text(encoding="utf-8") == "#!python\n\nprint('hello world')"
    # Nested files are not rewritten by this function (packaging handles them).
    assert nested_script.read_text(encoding="utf-8") == (
        "#!/usr/bin/env python3\n\nprint('nested')"
    )
