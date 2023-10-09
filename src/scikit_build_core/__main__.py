def run_cli() -> None:
    """
    Entry point to skbuild command.

    Wraps the import and execution in a try-catch to detect any missing dependency
    """
    try:
        from .cli import skbuild

        skbuild()
    except ImportError as err:
        msg = "Could not import scikit-build-core cli"
        raise ImportError(msg) from err


if __name__ == "__main__":
    run_cli()
