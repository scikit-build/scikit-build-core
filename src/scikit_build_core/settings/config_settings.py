# No `from __future__ import annotations` here: `to_json_schema` reads real
# runtime types from the dataclass fields, like `skbuild_model.py`.

__lazy_modules__ = {
    "copy",
    "typing",
    f"{(__spec__.parent or '').rsplit('.', 1)[0]}._logging",
    f"{(__spec__.parent or '').rsplit('.', 1)[0]}._variants",
    f"{__spec__.parent}.skbuild_model",
    f"{__spec__.parent}.skbuild_overrides",
}

import copy
import dataclasses
import re
from typing import Any, Literal

from .._logging import rich_error
from .._variants import NULL_VARIANT_LABEL, _no_label_entry
from .skbuild_model import ScikitBuildSettings
from .skbuild_overrides import strtobool

TYPE_CHECKING = False
if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

__all__ = [
    "ConfigSettingDeclaration",
    "MetadataVariantKeys",
    "load_declarations",
    "resolve_config_settings",
    "resolve_define_references",
    "resolve_format_keys",
    "resolve_metadata_config_settings",
    "resolve_metadata_variant",
]


def __dir__() -> list[str]:
    return __all__


# At least two dotted segments; matched verbatim (no dash/underscore
# normalization), like env-table keys.
_NAME_REGEX = re.compile(r"^[A-Za-z0-9_-]+(\.[A-Za-z0-9_-]+)+$")

# A "choices" key (allowed values, str type only) was cut from the initial
# release to keep the surface minimal; see git history to re-add.
_DECLARATION_KEYS = frozenset({"help", "type", "default", "env"})


@dataclasses.dataclass(frozen=True)
class ConfigSettingDeclaration:
    """
    A single entry in the ``tool.scikit-build.config-setting`` table.

    Declares a package-specific config-setting key that users may pass via PEP
    517 config-settings (``-C name=value``) or, if ``env`` is set, an
    environment variable.
    """

    help: str = ""
    """
    A description of the setting.
    """

    type: Literal["str", "bool"] = "str"
    """
    The type of the setting.
    """

    default: str | bool | None = None
    """
    The value used when the setting is not passed; must match the type.
    """

    env: str | None = None
    """
    An environment variable also read for this setting; it takes precedence over `-C`.
    """


def _error_context(name: str) -> str:
    return f"tool.scikit-build.config-setting.{name!r}"


def load_declarations(raw: Any) -> dict[str, ConfigSettingDeclaration]:
    """
    Validate and load the raw ``tool.scikit-build.config-setting`` table.
    """
    if not isinstance(raw, dict):
        rich_error("tool.scikit-build.config-setting must be a table")
    if not raw:
        return {}

    reserved = {
        field.name.replace("_", "-")
        for field in dataclasses.fields(ScikitBuildSettings)
    } | {"overrides", "config-setting", "skbuild"}

    decls: dict[str, ConfigSettingDeclaration] = {}
    for name, entry in raw.items():
        if not _NAME_REGEX.match(name):
            rich_error(
                f"{_error_context(name)} must be two or more dotted segments of"
                " letters, digits, '-', and '_'"
            )
        first_segment = name.split(".", 1)[0]
        if first_segment in reserved:
            rich_error(
                f"{_error_context(name)} may not start with the reserved segment"
                f" {first_segment!r}"
            )
        if not isinstance(entry, dict):
            rich_error(f"{_error_context(name)} must be a table")
        unknown = set(entry) - _DECLARATION_KEYS
        if unknown:
            rich_error(
                f"{_error_context(name)} has unrecognized keys:"
                f" {', '.join(sorted(unknown))}"
            )

        help_text = entry.get("help", "")
        if not isinstance(help_text, str):
            rich_error(f"{_error_context(name)} 'help' must be a string")
        type_ = entry.get("type", "str")
        if type_ not in {"str", "bool"}:
            rich_error(f"{_error_context(name)} 'type' must be 'str' or 'bool'")
        env = entry.get("env")
        if env is not None and (not isinstance(env, str) or not env):
            rich_error(f"{_error_context(name)} 'env' must be a non-empty string")
        default = entry.get("default")
        if default is not None:
            # bool is checked first since bool is an int subclass.
            if type_ == "bool" and not isinstance(default, bool):
                rich_error(
                    f"{_error_context(name)} 'default' must be a boolean for"
                    " type = 'bool'"
                )
            if type_ == "str" and not isinstance(default, str):
                rich_error(
                    f"{_error_context(name)} 'default' must be a string for"
                    " type = 'str'"
                )

        decls[name] = ConfigSettingDeclaration(
            help=help_text,
            type=type_,
            default=default,
            env=env,
        )
    return decls


def resolve_config_settings(
    decls: "Mapping[str, ConfigSettingDeclaration]",
    config_settings: "Mapping[str, str | list[str] | bool]",
    env: "Mapping[str, str]",
) -> dict[str, str | bool | None]:
    """
    Resolve declared config-settings; precedence env var > config-setting >
    default, with ``None`` meaning "unset".
    """
    values: dict[str, str | bool | None] = {}
    for name, decl in decls.items():
        raw: str | bool | None
        if decl.env is not None and decl.env in env:
            raw = env[decl.env]
        elif name in config_settings:
            item = config_settings[name]
            if isinstance(item, list):
                if len(item) != 1:
                    rich_error(f"config-setting {name!r} was passed more than once")
                item = item[0]
            raw = item
        else:
            # Defaults are validated against the declared type at load time.
            values[name] = decl.default
            continue

        if decl.type == "bool":
            values[name] = raw if isinstance(raw, bool) else strtobool(raw)
            continue
        if isinstance(raw, bool):
            rich_error(f"config-setting {name!r} expected a string, got a boolean")
        values[name] = raw
    return values


def _referenced_value(
    context: str, name: object, values: "Mapping[str, str | bool | None]"
) -> "str | bool | None":
    if not isinstance(name, str) or name not in values:
        rich_error(f"{context} references undeclared config-setting {name!r}")
    return values[name]


def resolve_define_references(
    tool_skb: dict[str, Any], values: "Mapping[str, str | bool | None]"
) -> None:
    """
    Replace ``{config-setting = "..."}`` values in the raw ``cmake.define``
    table with the resolved values, in place. Unset settings drop the define
    (mirroring the ``{env = ...}`` form). Malformed non-table values are left
    for the normal settings conversion to report.
    """
    cmake_table = tool_skb.get("cmake", {})
    if not isinstance(cmake_table, dict):
        return
    define = cmake_table.get("define", {})
    if not isinstance(define, dict):
        return
    for key, entry in list(define.items()):
        if not isinstance(entry, dict) or "config-setting" not in entry:
            continue
        unknown = set(entry) - {"config-setting"}
        if unknown:
            rich_error(
                f"cmake.define.{key} config-setting reference has unrecognized"
                f" keys: {', '.join(sorted(unknown))} (put defaults in the"
                " declaration instead)"
            )
        value = _referenced_value(
            f"cmake.define.{key}", entry["config-setting"], values
        )
        if value is None:
            del define[key]
        else:
            define[key] = value


def resolve_format_keys(
    tool_skb: dict[str, Any], values: "Mapping[str, str | bool | None]"
) -> dict[str, str]:
    """
    Replace ``{config-setting = "...", default = "..."}`` values in the raw
    ``format-keys`` table with strings, in place.

    Returns an error message for each key that has no value. Such a key gets
    an empty string, and the caller reports the error only if no source of
    higher precedence sets the key.
    """
    unset: dict[str, str] = {}
    table = tool_skb.get("format-keys", {})
    if not isinstance(table, dict):
        return unset
    for key, entry in table.items():
        if isinstance(entry, str):
            continue
        if not isinstance(entry, dict):
            rich_error(f"format-keys.{key} must be a string or a table")
        unknown = set(entry) - {"config-setting", "default"}
        if unknown:
            rich_error(
                f"format-keys.{key} has unrecognized keys: {', '.join(sorted(unknown))}"
            )
        name = entry.get("config-setting")
        value = _referenced_value(f"format-keys.{key}", name, values)
        default = entry.get("default")
        if default is not None and not isinstance(default, str):
            rich_error(f"format-keys.{key} 'default' must be a string")
        if value is None:
            value = default
        if value is None:
            unset[key] = (
                f"format-keys.{key}: config-setting {name!r} is not set;"
                " set it or add a default"
            )
            value = ""
        table[key] = str(value).lower() if isinstance(value, bool) else value
    return unset


@dataclasses.dataclass(frozen=True)
class MetadataVariantKeys:
    """
    The plugin settings of one ``[[tool.dynamic-metadata]]`` entry that get the
    variant label and properties. ``resolve_metadata_variant`` fills them after
    the settings (and so the label) are resolved.
    """

    entry: dict[str, Any]
    label: str | None
    properties: str | None


def resolve_metadata_config_settings(
    entries: Any, values: "Mapping[str, str | bool | None]"
) -> tuple[bool, list[MetadataVariantKeys]]:
    """
    Apply ``tool.scikit-build.config-setting`` of each
    ``[[tool.dynamic-metadata]]`` entry, in place, and remove the reserved
    ``tool`` key. The table maps a plugin setting to a declared config-setting;
    a resolved value replaces the static one, and an unset setting keeps it.
    Returns True if an entry has a mapping, and the entries that map
    ``variant-label`` or ``variant-properties``.
    """
    used = False
    variant_keys: list[MetadataVariantKeys] = []
    if not isinstance(entries, list):
        return used, variant_keys
    for n, entry in enumerate(entries):
        if not isinstance(entry, dict) or "tool" not in entry:
            continue
        context = f"tool.dynamic-metadata[{n}].tool"
        tool = entry.pop("tool")
        if not isinstance(tool, dict):
            rich_error(f"{context} must be a table")
        # Other backends' tables are ignored.
        skb = tool.get("scikit-build", {})
        context += ".scikit-build"
        if not isinstance(skb, dict):
            rich_error(f"{context} must be a table")
        unknown = set(skb) - {"config-setting", "variant-label", "variant-properties"}
        if unknown:
            rich_error(f"{context} has unrecognized keys: {', '.join(sorted(unknown))}")

        # Plugin setting -> the reserved key that fills it
        targets: dict[str, str] = {}
        for name in ("variant-label", "variant-properties"):
            if name not in skb:
                continue
            key = skb[name]
            if not isinstance(key, str):
                rich_error(f"{context}.{name} must be a string")
            if key in {"provider", "tool"}:
                rich_error(f"{context}.{name} may not set {key!r}")
            if key in targets:
                rich_error(f"{context}.{name} and {targets[key]} both set {key!r}")
            targets[key] = name
        if targets:
            variant_keys.append(
                MetadataVariantKeys(
                    entry,
                    label=skb.get("variant-label"),
                    properties=skb.get("variant-properties"),
                )
            )

        mapping = skb.get("config-setting", {})
        context += ".config-setting"
        if not isinstance(mapping, dict):
            rich_error(f"{context} must be a table")
        used = used or bool(mapping)
        for key, name in mapping.items():
            if key in {"provider", "tool"}:
                rich_error(f"{context} may not set {key!r}")
            if key in targets:
                rich_error(f"{context}.{key} is also set by {targets[key]}")
            if not isinstance(name, str):
                rich_error(f"{context}.{key} must be a string")
            if name not in values:
                rich_error(
                    f"{context}.{key} references undeclared config-setting {name!r}"
                )
            value = values[name]
            if value is not None:
                entry[key] = value
    return used, variant_keys


def resolve_metadata_variant(
    variant_keys: "Sequence[MetadataVariantKeys]",
    label: str | None,
    variant_table: "Mapping[str, Any]",
) -> None:
    """
    Set the mapped plugin settings to the resolved variant label and its
    ``[variant.variants.<label>]`` properties (namespace -> feature -> list of
    values). With no variant, the static values stay. The ``null`` variant has
    no properties.
    """
    if not label or not variant_keys:
        return
    properties: dict[str, Any] = {}
    if label != NULL_VARIANT_LABEL:
        variants = variant_table.get("variants", {})
        found = variants.get(label) if isinstance(variants, dict) else None
        if not isinstance(found, dict):
            _no_label_entry(label)
        properties = found
    for keys in variant_keys:
        if keys.label is not None:
            keys.entry[keys.label] = label
        if keys.properties is not None:
            keys.entry[keys.properties] = copy.deepcopy(properties)
