from __future__ import annotations

import contextlib
import os
import string
import sysconfig
import tempfile
from collections.abc import Generator, MutableMapping
from pathlib import Path

from .._logging import logger
from ..resources import resources

__all__ = ["set_cross_compile_env"]


def __dir__() -> list[str]:
    return __all__


@contextlib.contextmanager
def auto_cross_compile_env(
    env: MutableMapping[str, str]
) -> Generator[None, None, None]:
    if "SETUPTOOLS_EXT_SUFFIX" not in env:
        yield
        return

    with set_cross_compile_env(env["SETUPTOOLS_EXT_SUFFIX"], env):
        yield


@contextlib.contextmanager
def set_cross_compile_env(
    ext_suffix: str,
    env: MutableMapping[str, str],
) -> Generator[None, None, None]:
    """
    Generate python file and set environment variables to cross-compile Python
    extensions. Do not call if _PYTHON_SYSCONFIGDATA_NAME is already set.
    """

    if "_PYTHON_SYSCONFIGDATA_NAME" in env:
        logger.debug(
            "Not setting up cross compiling explicitly due to _PYTHON_SYSCONFIGDATA_NAME already set."
        )
        yield
        return

    sysconf_name = getattr(sysconfig, "_get_sysconfigdata_name", "")
    if not sysconf_name:
        logger.warning(
            "Cross-compiling is not supported due to sysconfig._get_sysconfigdata_name missing."
        )
        yield
        return

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_dir = Path(tmpdir).resolve()
        cross_compile_file = (
            tmp_dir / f"_cross_compile_{ext_suffix.replace('.', '_')}.py"
        )
        input_txt = resources.joinpath("_cross_compile.py").read_text(encoding="utf-8")
        output_text = string.Template(input_txt).substitute(
            host_name=sysconf_name,
            SOABI=ext_suffix.rsplit(maxsplit=1)[0],
            EXT_SUFFIX=ext_suffix,
        )
        cross_compile_file.write_text(output_text)
        current_path = env.get("PYTHONPATH", "")
        env["PYTHONPATH"] = (
            os.pathsep.join([current_path, str(tmp_dir)])
            if current_path
            else str(tmp_dir)
        )
        env["_PYTHON_SYSCONFIGDATA_NAME"] = cross_compile_file.stem
        logger.info("Cross-compiling is enabled to {!r}.", ext_suffix)
        logger.debug(
            "Setting _PYTHON_SYSCONFIGDATA_NAME to {!r}.",
            env["_PYTHON_SYSCONFIGDATA_NAME"],
        )
        logger.debug("Setting PYTHONPATH to {!r}.", env["PYTHONPATH"])
        logger.debug("Cross compile output file contents: {}", output_text)
        try:
            yield
        finally:
            del env["_PYTHON_SYSCONFIGDATA_NAME"]
            if current_path:
                env["PYTHONPATH"] = current_path
            else:
                del env["PYTHONPATH"]
