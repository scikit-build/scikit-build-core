from __future__ import annotations

import importlib
import importlib.machinery
import importlib.util
import inspect
import pkgutil
from pathlib import Path
from typing import Generator


def on_all_modules(
    name: str, base_path: Path | None = None, *, pkg: bool
) -> Generator[str, None, None]:
    if base_path is None:
        base_module = importlib.import_module(name)
        base_path = Path(inspect.getfile(base_module)).parent
    for module_info in pkgutil.iter_modules([str(base_path)]):
        package_name = f"{name}.{module_info.name}"
        if module_info.ispkg:
            if pkg:
                yield package_name
            yield from on_all_modules(
                package_name, base_path / module_info.name, pkg=pkg
            )
        else:
            yield package_name


def test_all_modules_filter_all():
    all_modules = on_all_modules("scikit_build_core", pkg=False)
    all_modules = (n for n in all_modules if not n.split(".")[-1].startswith("__"))
    for name in all_modules:
        module = importlib.import_module(name)

        try:
            dir_module = set(dir(module))
        except Exception:
            print(f"dir() failed on {name}")
            raise
        items = ["annotations", "os", "sys"]
        for item in items:
            assert item not in dir_module, f"{module.__file__} has {item!r}"


def test_all_modules_has_all():
    all_modules = on_all_modules("scikit_build_core", pkg=True)
    all_modules = (n for n in all_modules if not n.split(".")[-1].startswith("_"))
    for name in all_modules:
        module = importlib.import_module(name)

        dir_module = module.__dict__
        items = ["__all__"]
        for item in items:
            assert item in dir_module, f"{module.__file__} missing {item!r}"
