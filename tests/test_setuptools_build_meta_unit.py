from __future__ import annotations

import setuptools.build_meta

from scikit_build_core.setuptools import build_meta as bm


def test_dir():
    assert "build_wheel" in bm.__dir__()


def test_get_requires_for_build_sdist_no_cmake(monkeypatch):
    monkeypatch.setattr(
        setuptools.build_meta, "get_requires_for_build_sdist", lambda _cs: []
    )

    class FakeSettings:
        class sdist:  # noqa: N801
            cmake = False

    class FakeRequires:
        settings = FakeSettings()

        def cmake(self):
            return ["cmake>=3.15"]

        def ninja(self):
            return ["ninja>=1.5"]

    monkeypatch.setattr(
        bm,
        "GetRequires",
        type("GR", (), {"from_config_settings": staticmethod(lambda _cs: FakeRequires())}),
    )
    reqs = bm.get_requires_for_build_sdist()
    assert "cmake>=3.15" not in reqs


def test_get_requires_for_build_sdist_with_cmake(monkeypatch):
    monkeypatch.setattr(
        setuptools.build_meta, "get_requires_for_build_sdist", lambda _cs: []
    )

    class FakeSettings:
        class sdist:  # noqa: N801
            cmake = True

    class FakeRequires:
        settings = FakeSettings()

        def cmake(self):
            return ["cmake>=3.15"]

        def ninja(self):
            return ["ninja>=1.5"]

    monkeypatch.setattr(
        bm,
        "GetRequires",
        type("GR", (), {"from_config_settings": staticmethod(lambda _cs: FakeRequires())}),
    )
    reqs = bm.get_requires_for_build_sdist()
    assert "cmake>=3.15" in reqs
    assert "ninja>=1.5" in reqs


def test_get_requires_for_build_wheel(monkeypatch):
    monkeypatch.setattr(
        setuptools.build_meta, "get_requires_for_build_wheel", lambda _cs: ["wheel"]
    )

    class FakeSettings:
        pass

    class FakeRequires:
        settings = FakeSettings()

        def cmake(self):
            return ["cmake>=3.15"]

        def ninja(self):
            return ["ninja>=1.5"]

    monkeypatch.setattr(
        bm,
        "GetRequires",
        type("GR", (), {"from_config_settings": staticmethod(lambda _cs: FakeRequires())}),
    )
    reqs = bm.get_requires_for_build_wheel()
    assert "wheel" in reqs
    assert "cmake>=3.15" in reqs
    assert "ninja>=1.5" in reqs


def test_get_requires_for_build_editable(monkeypatch):
    if not hasattr(setuptools.build_meta, "get_requires_for_build_editable"):
        return

    monkeypatch.setattr(
        setuptools.build_meta, "get_requires_for_build_editable", lambda _cs: ["wheel"]
    )

    class FakeSettings:
        pass

    class FakeRequires:
        settings = FakeSettings()

        def cmake(self):
            return ["cmake>=3.15"]

        def ninja(self):
            return ["ninja>=1.5"]

    monkeypatch.setattr(
        bm,
        "GetRequires",
        type("GR", (), {"from_config_settings": staticmethod(lambda _cs: FakeRequires())}),
    )
    reqs = bm.get_requires_for_build_editable()
    assert "wheel" in reqs
    assert "cmake>=3.15" in reqs
