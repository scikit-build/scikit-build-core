import dataclasses
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Type, TypeVar, Union

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib


T = TypeVar("T")


@dataclasses.dataclass
class CMakeSettings:
    min_version: str = dataclasses.field(default="3.15")


def read_config_settings(
    pyproject_toml: Path, config_settings: Dict[str, Union[str, List[str]]]
) -> CMakeSettings:
    with pyproject_toml.open("rb") as f:
        pyproject = tomllib.load(f)

    cmake_section = pyproject.get("tool", {}).get("cmake", {})

    settings = convert_settings(
        CMakeSettings,
        cmake_section,
        config_settings,
        conf_prefix="",
        env_prefix="SKBUILD",
    )

    return settings


def convert_settings(
    target: Type[T],
    cmake_section: Dict[str, Any],
    config_settings: Dict[str, Union[str, List[str]]],
    conf_prefix: str,
    env_prefix: str,
) -> T:
    prep = {}
    for field in dataclasses.fields(target):

        metadata = field.metadata.get("cmake", {})
        name_metadata = metadata.get("name", {})

        env_name = name_metadata.get(
            "env", "_".join([env_prefix, field.name.upper().replace("-", "_")])
        )
        conf_name = name_metadata.get(
            "conf", ".".join([conf_prefix, field.name]) if conf_prefix else field.name
        )
        toml_name = name_metadata.get("toml", field.name)

        if dataclasses.is_dataclass(field.type):
            prep[field.name] = convert_settings(
                field.type,
                cmake_section,
                config_settings,
                conf_prefix=conf_prefix + field.name + "_",
                env_prefix=env_prefix + field.name.upper() + "_",
            )
        elif env_name and env_name in os.environ:
            prep[field.name] = convert(os.environ[env_name], field.type)
        elif conf_name and conf_name in config_settings:
            prep[field.name] = convert(config_settings[conf_name], field.type)
        elif toml_name and toml_name in cmake_section:
            prep[field.name] = convert_toml(cmake_section[toml_name], field.type)

    return target(**prep)


def convert(item: Union[str, List[str]], target: Type[T]) -> T:
    if isinstance(item, list):
        return [convert(i, target.__args__[0]) for i in item]  # type: ignore[return-value,attr-defined]
    if hasattr(target, "__origin__"):
        if target.__origin__ == list:  # type: ignore[attr-defined]
            return [convert(i, target.__args__[0]) for i in item.split(";")]  # type: ignore[return-value,attr-defined]
        if target.__origin__ == Union:  # type: ignore[attr-defined]
            return convert(item, target.__args__[0])  # type: ignore[no-any-return,attr-defined]
    return target(item)  # type: ignore[call-arg]


def convert_toml(item: Any, target: Type[T]) -> T:
    if isinstance(target, type) and issubclass(target, Path):  # type: ignore[redundant-expr]
        return target(item)  # type: ignore[return-value]
    return item  # type: ignore[no-any-return]
