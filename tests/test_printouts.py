from scikit_build_core.builder.__main__ import main


def test_builder_printout(capsys):
    main()
    out, err = capsys.readouterr()
    assert "Detected Python Library" in out
