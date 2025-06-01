from __future__ import annotations

import os
import platform
import re
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal

import packaging.tags
from packaging.specifiers import SpecifierSet

from .. import __version__
from .._compat import tomllib
from .._logging import logger
from ..builder.sysconfig import get_abi_flags
from ..cmake import CMake
from ..errors import CMakeNotFoundError
from ..resources import resources

__all__ = ["process_overrides", "regex_match"]


def __dir__() -> list[str]:
    return __all__


if TYPE_CHECKING:
    from collections.abc import Mapping


def strtobool(value: str) -> bool:
    """
    Converts a environment variable string into a boolean value.
    """
    if not value:
        return False
    value = value.lower()
    if value.isdigit():
        return bool(int(value))
    return value not in {"n", "no", "off", "false", "f"}


def version_match(value: str, match: str, name: str) -> str:
    """
    Returns a non-empty string if a version matches a specifier.
    """
    matcher = SpecifierSet(match)
    did_match = matcher.contains(value)
    return f"{match!r} matched {name} {value}" if did_match else ""


def regex_match(value: str, match: str) -> str:
    """
    Returns a non-empty string if a value matches a regex.
    """
    did_match = re.compile(match).search(value) is not None
    return f"{match!r} matched {value!r}" if did_match else ""


def override_match(
    *,
    current_env: Mapping[str, str] | None,
    current_state: Literal[
        "sdist", "wheel", "editable", "metadata_wheel", "metadata_editable"
    ],
    has_dist_info: bool,
    retry: bool,
    python_version: str | None = None,
    implementation_name: str | None = None,
    implementation_version: str | None = None,
    platform_system: str | None = None,
    platform_machine: str | None = None,
    platform_node: str | None = None,
    env: dict[str, str] | None = None,
    state: str | None = None,
    from_sdist: bool | None = None,
    failed: bool | None = None,
    system_cmake: str | None = None,
    cmake_wheel: bool | None = None,
    abi_flags: str | None = None,
    scikit_build_version: str | None = None,
    **unknown: Any,
) -> tuple[dict[str, str], set[str], dict[str, Any]]:
    """
    Check if the current environment matches the overrides. Returns a dict of
    passed matches, with reasons for values, and a set of non-matches.
    """

    passed_dict = {}
    failed_set: set[str] = set()

    if current_env is None:
        current_env = os.environ

    if scikit_build_version is not None:
        current_version = __version__
        match_msg = version_match(
            current_version, scikit_build_version, "scikit-build-core"
        )
        if match_msg:
            passed_dict["scikit-build-version"] = match_msg
        else:
            failed_set.add("scikit-build-version")

    if python_version is not None:
        current_python_version = ".".join(str(x) for x in sys.version_info[:2])
        match_msg = version_match(current_python_version, python_version, "Python")
        if match_msg:
            passed_dict["python-version"] = match_msg
        else:
            failed_set.add("python-version")

    if implementation_name is not None:
        current_impementation_name = sys.implementation.name
        match_msg = regex_match(current_impementation_name, implementation_name)
        if match_msg:
            passed_dict["implementation-name"] = match_msg
        else:
            failed_set.add("implementation-name")

    if implementation_version is not None:
        info = sys.implementation.version
        version = f"{info.major}.{info.minor}.{info.micro}"
        kind = info.releaselevel
        if kind != "final":
            version += f"{kind[0]}{info.serial}"
        match_msg = version_match(
            version, implementation_version, "Python implementation"
        )
        if match_msg:
            passed_dict["implementation-version"] = match_msg
        else:
            failed_set.add("implementation-version")

    if platform_system is not None:
        current_platform_system = sys.platform
        match_msg = regex_match(current_platform_system, platform_system)
        if match_msg:
            passed_dict["platform-system"] = match_msg
        else:
            failed_set.add("platform-system")

    if platform_machine is not None:
        current_platform_machine = platform.machine()
        match_msg = regex_match(current_platform_machine, platform_machine)
        if match_msg:
            passed_dict["platform-machine"] = match_msg
        else:
            failed_set.add("platform-machine")

    if platform_node is not None:
        current_platform_node = platform.node()
        match_msg = regex_match(current_platform_node, platform_node)
        if match_msg:
            passed_dict["platform-node"] = match_msg
        else:
            failed_set.add("platform-node")

    if state is not None:
        match_msg = regex_match(current_state, state)
        if match_msg:
            passed_dict["state"] = match_msg
        else:
            failed_set.add("state")

    if failed is not None:
        if failed and retry:
            passed_dict["failed"] = "Previous run failed"
        elif not failed and not retry:
            passed_dict["failed"] = "Running on a fresh run"
        else:
            failed_set.add("failed")

    if from_sdist is not None:
        if has_dist_info:
            if from_sdist:
                passed_dict["from-sdist"] = "from sdist due to PKG-INFO"
            else:
                failed_set.add("from-sdist")
        elif not from_sdist:
            passed_dict["from-sdist"] = "not from sdist, no PKG-INFO"
        else:
            failed_set.add("from-sdist")

    if system_cmake is not None:
        try:
            cmake = CMake.default_search(
                version=SpecifierSet(system_cmake), module=False, env=current_env
            )
            passed_dict["system-cmake"] = (
                f"system cmake {cmake.version} found at {cmake.cmake_path} passing {system_cmake}"
            )
        except CMakeNotFoundError:
            failed_set.add("system-cmake")

    if cmake_wheel is not None:
        with resources.joinpath("known_wheels.toml").open("rb") as f:
            known_wheels_toml = tomllib.load(f)
        known_cmake_wheels = set(
            known_wheels_toml["tool"]["scikit-build"]["cmake"]["known-wheels"]
        )
        cmake_plat = known_cmake_wheels.intersection(packaging.tags.sys_tags())
        if cmake_plat:
            passed_dict["cmake-wheel"] = f"cmake wheel available on {cmake_plat}"
        else:
            failed_set.add("cmake-wheel")

    if abi_flags is not None:
        current_abi_flags = get_abi_flags()
        match_msg = regex_match(current_abi_flags, abi_flags)
        if match_msg:
            passed_dict["abi-flags"] = match_msg
        else:
            failed_set.add("abi-flags")

    if env:
        for key, value in env.items():
            if isinstance(value, bool):
                if strtobool(current_env.get(key, "")) == value:
                    passed_dict[f"env.{key}"] = f"env {key} is {value}"
                else:
                    failed_set.add(f"env.{key}")
            elif key not in current_env:
                failed_set.add(f"env.{key}")
            else:
                current_value = current_env[key]
                match_msg = regex_match(current_value, value)

                if match_msg:
                    passed_dict[f"env.{key}"] = f"env {key}: {match_msg}"
                else:
                    failed_set.add(f"env.{key}")

    if len(passed_dict) + len(failed_set) + len(unknown) < 1:
        msg = "At least one override must be provided"
        raise ValueError(msg)

    return passed_dict, failed_set, unknown


def inherit_join(
    value: list[str] | dict[str, str] | str | int | bool,
    previous: list[str] | dict[str, str] | str | int | bool | None,
    mode: str,
) -> list[str] | dict[str, str] | str | int | bool:
    if mode not in {"none", "append", "prepend"}:
        msg = "Only 'none', 'append', and 'prepend' supported for inherit"
        raise TypeError(msg)
    if mode == "none" or previous is None:
        return value
    if isinstance(previous, list) and isinstance(value, list):
        return [*previous, *value] if mode == "append" else [*value, *previous]
    if isinstance(previous, dict) and isinstance(value, dict):
        return {**previous, **value} if mode == "append" else {**value, **previous}
    msg = "Append/prepend modes can only be used on lists or dicts"
    raise TypeError(msg)


def process_overrides(
    tool_skb: dict[str, Any],
    *,
    state: Literal["sdist", "wheel", "editable", "metadata_wheel", "metadata_editable"],
    retry: bool,
    env: Mapping[str, str] | None = None,
) -> set[str]:
    """
    Process overrides into the main dictionary if they match. Modifies the input
    dictionary. Must be run from the package directory.
    """
    has_dist_info = Path("PKG-INFO").is_file()

    global_matched: set[str] = set()
    for override in tool_skb.pop("overrides", []):
        passed_any: dict[str, str] | None = None
        passed_all: dict[str, str] | None = None
        unknown: set[str] = set()
        failed_any: set[str] = set()
        failed_all: set[str] = set()
        if_override = override.pop("if", None)
        if not if_override:
            msg = "At least one 'if' override must be provided"
            raise KeyError(msg)
        if not isinstance(if_override, dict):
            msg = "'if' override must be a table"
            raise TypeError(msg)
        if "any" in if_override:
            any_override = if_override.pop("any")
            select = {k.replace("-", "_"): v for k, v in any_override.items()}
            passed_any, failed_any, unknown_any = override_match(
                current_env=env,
                current_state=state,
                has_dist_info=has_dist_info,
                retry=retry,
                **select,
            )
            unknown |= set(unknown_any)

        inherit_override = override.pop("inherit", {})
        if not isinstance(inherit_override, dict):
            msg = "'inherit' override must be a table"
            raise TypeError(msg)

        select = {k.replace("-", "_"): v for k, v in if_override.items()}
        if select:
            passed_all, failed_all, unknown_all = override_match(
                current_env=env,
                current_state=state,
                has_dist_info=has_dist_info,
                retry=retry,
                **select,
            )
            unknown |= set(unknown_all)

        # Verify no unknown options are present unless scikit-build-version is specified
        passed_or_failed = {
            *(passed_all or {}),
            *(passed_any or {}),
            *failed_all,
            *failed_any,
        }
        if "scikit-build-version" not in passed_or_failed and unknown:
            msg = f"Unknown overrides: {', '.join(unknown)}"
            raise TypeError(msg)

        # If no overrides are passed, do nothing
        if passed_any is None and passed_all is None:
            continue

        # If normal overrides are passed and one or more fails, do nothing
        if passed_all is not None and failed_all:
            continue

        # If any is passed, at least one always needs to pass.
        if passed_any is not None and not passed_any:
            continue

        local_matched = set(passed_any or []) | set(passed_all or [])
        global_matched |= local_matched
        if local_matched:
            if unknown:
                msg = f"Unknown overrides: {', '.join(unknown)}"
                raise TypeError(msg)

            all_str = " and ".join(
                [
                    *(passed_all or {}).values(),
                    *([" or ".join(passed_any.values())] if passed_any else []),
                ]
            )
            logger.info("Overrides {}", all_str)

            for key, value in override.items():
                inherit1 = inherit_override.get(key, {})
                if isinstance(value, dict):
                    for key2, value2 in value.items():
                        inherit2 = inherit1.get(key2, "none")
                        inner = tool_skb.get(key, {})
                        inner[key2] = inherit_join(
                            value2, inner.get(key2, None), inherit2
                        )
                        tool_skb[key] = inner
                else:
                    inherit_override_tmp = inherit_override or "none"
                    if isinstance(inherit_override_tmp, dict):
                        assert not inherit_override_tmp
                    tool_skb[key] = inherit_join(
                        value, tool_skb.get(key), inherit_override_tmp
                    )
    return global_matched
