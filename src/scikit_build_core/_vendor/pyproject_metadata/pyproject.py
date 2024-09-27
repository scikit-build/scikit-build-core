from __future__ import annotations

import dataclasses
import pathlib
import re
import typing

import packaging.requirements

from .errors import ErrorCollector


__all__ = [
    'License',
    'Readme',
]


def __dir__() -> list[str]:
    return __all__


@dataclasses.dataclass(frozen=True)
class License:
    text: str
    file: pathlib.Path | None


@dataclasses.dataclass(frozen=True)
class Readme:
    text: str
    file: pathlib.Path | None
    content_type: str


if typing.TYPE_CHECKING:
    from collections.abc import Generator, Iterable, Sequence

    from packaging.requirements import Requirement

    from .project_table import ContactTable, ProjectTable


@dataclasses.dataclass
class PyProjectReader(ErrorCollector):
    def ensure_str(self, value: str, key: str) -> str | None:
        if isinstance(value, str):
            return value

        msg = f'Field "{key}" has an invalid type, expecting a string (got "{value}")'
        self.config_error(msg, key=key)
        return None

    def ensure_list(self, val: list[str], key: str) -> list[str] | None:
        if not isinstance(val, list):
            msg = f'Field "{key}" has an invalid type, expecting a list of strings (got "{val}")'
            self.config_error(msg, key=key)
            return None
        for item in val:
            if not isinstance(item, str):
                msg = f'Field "{key}" contains item with invalid type, expecting a string (got "{item}")'
                self.config_error(msg, key=key)
                return None

        return val

    def ensure_dict(self, val: dict[str, str], key: str) -> dict[str, str] | None:
        if not isinstance(val, dict):
            msg = f'Field "{key}" has an invalid type, expecting a dictionary of strings (got "{val}")'
            self.config_error(msg, key=key)
            return None
        for subkey, item in val.items():
            if not isinstance(item, str):
                msg = f'Field "{key}.{subkey}" has an invalid type, expecting a string (got "{item}")'
                self.config_error(msg, key=f'{key}.{subkey}')
                return None
        return val

    def ensure_people(
        self, val: Sequence[ContactTable], key: str
    ) -> list[tuple[str, str | None]]:
        if not (
            isinstance(val, list)
            and all(isinstance(x, dict) for x in val)
            and all(
                isinstance(item, str)
                for items in [_dict.values() for _dict in val]
                for item in items
            )
        ):
            msg = (
                f'Field "{key}" has an invalid type, expecting a list of '
                f'dictionaries containing the "name" and/or "email" keys (got "{val}")'
            )
            self.config_error(msg, key=key)
            return []
        return [(entry.get('name', 'Unknown'), entry.get('email')) for entry in val]

    def get_license(
        self, project: ProjectTable, project_dir: pathlib.Path
    ) -> License | str | None:
        val = project.get('license')
        if val is None:
            return None
        if isinstance(val, str):
            return val

        if isinstance(val, dict):
            _license = self.ensure_dict(val, 'project.license')  # type: ignore[arg-type]
            if _license is None:
                return None
        else:
            msg = f'Field "project.license" has an invalid type, expecting a string or dictionary of strings (got "{val}")'
            self.config_error(msg, key='project.license')
            return None

        for field in _license:
            if field not in ('file', 'text'):
                msg = f'Unexpected field "project.license.{field}"'
                self.config_error(msg, key=f'project.license.{field}')
                return None

        file: pathlib.Path | None = None
        filename = _license.get('file')
        text = _license.get('text')

        if (filename and text) or (not filename and not text):
            msg = f'Invalid "project.license" value, expecting either "file" or "text" (got "{_license}")'
            self.config_error(msg, key='project.license')
            return None

        if filename:
            file = project_dir.joinpath(filename)
            if not file.is_file():
                msg = f'License file not found ("{filename}")'
                self.config_error(msg, key='project.license.file')
                return None
            text = file.read_text(encoding='utf-8')

        assert text is not None
        return License(text, file)

    def get_license_files(
        self, project: ProjectTable, project_dir: pathlib.Path
    ) -> list[pathlib.Path] | None:
        license_files = project.get('license-files')
        if license_files is None:
            return None
        if self.ensure_list(license_files, 'project.license-files') is None:
            return None

        return list(self._get_files_from_globs(project_dir, license_files))

    def get_readme(  # noqa: C901
        self, project: ProjectTable, project_dir: pathlib.Path
    ) -> Readme | None:
        if 'readme' not in project:
            return None

        filename: str | None = None
        file: pathlib.Path | None = None
        text: str | None = None
        content_type: str | None = None

        readme = project['readme']
        if isinstance(readme, str):
            # readme is a file
            text = None
            filename = readme
            if filename.endswith('.md'):
                content_type = 'text/markdown'
            elif filename.endswith('.rst'):
                content_type = 'text/x-rst'
            else:
                msg = f'Could not infer content type for readme file "{filename}"'
                self.config_error(msg, key='project.readme')
                return None
        elif isinstance(readme, dict):
            # readme is a dict containing either 'file' or 'text', and content-type
            for field in readme:
                if field not in ('content-type', 'file', 'text'):
                    msg = f'Unexpected field "project.readme.{field}"'
                    self.config_error(msg, key=f'project.readme.{field}')
                    return None

            content_type_raw = readme.get('content-type')
            if content_type_raw is not None:
                content_type = self.ensure_str(
                    content_type_raw, 'project.readme.content-type'
                )
                if content_type is None:
                    return None
            filename_raw = readme.get('file')
            if filename_raw is not None:
                filename = self.ensure_str(filename_raw, 'project.readme.file')
                if filename is None:
                    return None

            text_raw = readme.get('text')
            if text_raw is not None:
                text = self.ensure_str(text_raw, 'project.readme.text')
                if text is None:
                    return None

            if (filename and text) or (not filename and not text):
                msg = f'Invalid "project.readme" value, expecting either "file" or "text" (got "{readme}")'
                self.config_error(msg, key='project.readme')
                return None
            if not content_type:
                msg = 'Field "project.readme.content-type" missing'
                self.config_error(msg, key='project.readme.content-type')
                return None
        else:
            msg = (
                f'Field "project.readme" has an invalid type, expecting either, '
                f'a string or dictionary of strings (got "{readme}")'
            )
            self.config_error(msg, key='project.readme')
            return None

        if filename:
            file = project_dir.joinpath(filename)
            if not file.is_file():
                msg = f'Readme file not found ("{filename}")'
                self.config_error(msg, key='project.readme.file')
                return None
            text = file.read_text(encoding='utf-8')

        assert text is not None
        return Readme(text, file, content_type)

    def get_dependencies(self, project: ProjectTable) -> list[Requirement]:
        requirement_strings: list[str] | None = None
        requirement_strings_raw = project.get('dependencies')
        if requirement_strings_raw is not None:
            requirement_strings = self.ensure_list(
                requirement_strings_raw, 'project.dependencies'
            )
        if requirement_strings is None:
            return []

        requirements: list[Requirement] = []
        for req in requirement_strings:
            try:
                requirements.append(packaging.requirements.Requirement(req))
            except packaging.requirements.InvalidRequirement as e:
                msg = (
                    'Field "project.dependencies" contains an invalid PEP 508 '
                    f'requirement string "{req}" ("{e}")'
                )
                self.config_error(msg, key='project.dependencies')
                return []
        return requirements

    def get_optional_dependencies(
        self,
        project: ProjectTable,
    ) -> dict[str, list[Requirement]]:
        val = project.get('optional-dependencies')
        if not val:
            return {}

        requirements_dict: dict[str, list[Requirement]] = {}
        if not isinstance(val, dict):
            msg = (
                'Field "project.optional-dependencies" has an invalid type, expecting a '
                f'dictionary of PEP 508 requirement strings (got "{val}")'
            )
            self.config_error(msg, key='project.optional-dependencies')
            return {}
        for extra, requirements in val.copy().items():
            assert isinstance(extra, str)
            if not isinstance(requirements, list):
                msg = (
                    f'Field "project.optional-dependencies.{extra}" has an invalid type, expecting a '
                    f'dictionary PEP 508 requirement strings (got "{requirements}")'
                )
                self.config_error(msg, key=f'project.optional-dependencies.{extra}')
                return {}
            requirements_dict[extra] = []
            for req in requirements:
                if not isinstance(req, str):
                    msg = (
                        f'Field "project.optional-dependencies.{extra}" has an invalid type, '
                        f'expecting a PEP 508 requirement string (got "{req}")'
                    )
                    self.config_error(msg, key=f'project.optional-dependencies.{extra}')
                    return {}
                try:
                    requirements_dict[extra].append(
                        packaging.requirements.Requirement(req)
                    )
                except packaging.requirements.InvalidRequirement as e:
                    msg = (
                        f'Field "project.optional-dependencies.{extra}" contains '
                        f'an invalid PEP 508 requirement string "{req}" ("{e}")'
                    )
                    self.config_error(msg, key=f'project.optional-dependencies.{extra}')
                    return {}
        return dict(requirements_dict)

    def get_entrypoints(self, project: ProjectTable) -> dict[str, dict[str, str]]:
        val = project.get('entry-points', None)
        if val is None:
            return {}
        if not isinstance(val, dict):
            msg = (
                'Field "project.entry-points" has an invalid type, expecting a '
                f'dictionary of entrypoint sections (got "{val}")'
            )
            self.config_error(msg, key='project.entry-points')
            return {}
        for section, entrypoints in val.items():
            assert isinstance(section, str)
            if not re.match(r'^\w+(\.\w+)*$', section):
                msg = (
                    'Field "project.entry-points" has an invalid value, expecting a name '
                    f'containing only alphanumeric, underscore, or dot characters (got "{section}")'
                )
                self.config_error(msg, key='project.entry-points')
                return {}
            if not isinstance(entrypoints, dict):
                msg = (
                    f'Field "project.entry-points.{section}" has an invalid type, expecting a '
                    f'dictionary of entrypoints (got "{entrypoints}")'
                )
                self.config_error(msg, key=f'project.entry-points.{section}')
                return {}
            for name, entrypoint in entrypoints.items():
                assert isinstance(name, str)
                if not isinstance(entrypoint, str):
                    msg = (
                        f'Field "project.entry-points.{section}.{name}" has an invalid type, '
                        f'expecting a string (got "{entrypoint}")'
                    )
                    self.config_error(msg, key=f'project.entry-points.{section}.{name}')
                    return {}
        return val

    def get_dynamic(self, project: ProjectTable) -> list[str]:
        dynamic: list[str] = project.get('dynamic', [])  # type: ignore[assignment]

        self.ensure_list(dynamic, 'project.dynamic')

        if 'name' in dynamic:
            msg = 'Unsupported field "name" in "project.dynamic"'
            self.config_error(msg, key='project.dynamic')
            return []

        return dynamic

    def _get_files_from_globs(
        self, project_dir: pathlib.Path, globs: Iterable[str]
    ) -> Generator[pathlib.Path, None, None]:
        for glob in globs:
            if glob.startswith(('..', '/')):
                msg = f'"{glob}" is an invalid "project.license-files" glob: the pattern must match files within the project directory'
                self.config_error(msg)
                break
            files = [f for f in project_dir.glob(glob) if f.is_file()]
            if not files:
                msg = f'Every pattern in "project.license-files" must match at least one file: "{glob}" did not match any'
                self.config_error(msg)
                break
            for f in files:
                yield f.relative_to(project_dir)
