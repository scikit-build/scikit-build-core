from scikit_build_core._logging import rich_print


def test_rich_print_nocolor(capsys, monkeypatch):
    monkeypatch.setenv("NO_COLOR", "1")
    monkeypatch.delenv("FORCE_COLOR", raising=False)
    rich_print("[red]hello[/red] world", end="")
    assert capsys.readouterr().out == "hello world"


def test_rich_print_nocolor_forcecolor(capsys, monkeypatch):
    monkeypatch.setenv("NO_COLOR", "1")
    monkeypatch.setenv("FORCE_COLOR", "1")
    rich_print("[red]hello[/red] world", end="")
    assert capsys.readouterr().out == "hello world"


def test_rich_print_forcecolor(capsys, monkeypatch):
    monkeypatch.setenv("FORCE_COLOR", "1")
    monkeypatch.delenv("NO_COLOR", raising=False)
    rich_print("[red bold]hello[/bold] world", end="")
    assert capsys.readouterr().out == "\33[91m\33[1mhello\33[22m world\33[0m"
