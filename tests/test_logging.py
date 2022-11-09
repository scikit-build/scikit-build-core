from scikit_build_core._logging import fake_rich_print


def test_fake_rich_print(capsys):
    fake_rich_print("[red]hello[/red] world", end="")
    assert capsys.readouterr().out == "hello world"
