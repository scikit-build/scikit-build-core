# Testing dependencies not satisfied on epel
# build, cattrs, hatch-fancy-pypi-readme, pytest-subprocess
%if 0%{?el10}
%bcond_with tests
%else
%bcond_without tests
%endif

%global debug_package %{nil}

Name:           python-scikit-build-core
Version:        0.0.0
Release:        %autorelease
Summary:        Build backend for CMake based projects

# The main project is licensed under Apache-2.0, but it has a vendored project
# src/scikit_build_core/_vendor/pyproject_metadata: MIT
# https://github.com/scikit-build/scikit-build-core/issues/933
License:        Apache-2.0 AND MIT
URL:            https://github.com/scikit-build/scikit-build-core
Source:         %{pypi_source scikit_build_core}

BuildRequires:  python3-devel
# Testing dependences
BuildRequires:  cmake
BuildRequires:  ninja-build
BuildRequires:  gcc
BuildRequires:  gcc-c++
BuildRequires:  git

%global _description %{expand:
A next generation Python CMake adapter and Python API for plugins
}

%description %_description

%package -n python3-scikit-build-core
Summary:        %{summary}
Requires:       cmake
Recommends:     (ninja-build or make)
Recommends:     python3-scikit-build-core+pyproject = %{version}-%{release}
Suggests:       ninja-build
Suggests:       gcc
Provides:       bundled(python3dist(pyproject-metadata))
BuildArch:      noarch
%description -n python3-scikit-build-core %_description


# Add %%pyproject_extras_subpkg results manually because BuildArch: noarch is not injected
# https://src.fedoraproject.org/rpms/python-rpm-macros/pull-request/174
# %%pyproject_extras_subpkg -n python3-scikit-build-core pyproject

%package -n python3-scikit-build-core+pyproject
Summary: Metapackage for python3-scikit-build-core: pyproject extras
Requires: python3-scikit-build-core = %{?epoch:%{epoch}:}%{version}-%{release}
BuildArch:      noarch
# Deprecated empty extras package
# Note: Cannot use Obsoletes + Provides here. python3dist() does not seem to be picked up
Provides:  deprecated()
%description -n python3-scikit-build-core+pyproject
This is a metapackage bringing in pyproject extras requires for
python3-scikit-build-core.
It makes sure the dependencies are installed.

%files -n python3-scikit-build-core+pyproject -f %{_pyproject_ghost_distinfo}


%prep
%autosetup -n scikit_build_core-%{version}
# Rename the bundled license so that it can be installed together
cp -p src/scikit_build_core/_vendor/pyproject_metadata/LICENSE LICENSE-pyproject-metadata


%generate_buildrequires
%pyproject_buildrequires %{?with_tests:-x test,test-meta,test-numpy}


%build
%pyproject_wheel


%install
%pyproject_install
%pyproject_save_files scikit_build_core


%check
%pyproject_check_import
%if %{with tests}
%pytest \
    -m "not network"
%endif


%files -n python3-scikit-build-core -f %{pyproject_files}
%license LICENSE LICENSE-pyproject-metadata
%doc README.md


%changelog
%autochangelog
