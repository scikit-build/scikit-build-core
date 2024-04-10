%global debug_package %{nil}

Name:           python-scikit-build-core
Version:        0.0.0
Release:        %autorelease
Summary:        Build backend for CMake based projects

License:        Apache-2.0
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
BuildArch:      noarch
%description -n python3-scikit-build-core %_description


# Add %%pyproject_extras_subpkg results manually because BuildArch: noarch is not injected
# https://src.fedoraproject.org/rpms/python-rpm-macros/pull-request/174
# %%pyproject_extras_subpkg -n python3-scikit-build-core pyproject

%package -n python3-scikit-build-core+pyproject
Summary: Metapackage for python3-scikit-build-core: pyproject extras
Requires: python3-scikit-build-core = %{?epoch:%{epoch}:}%{version}-%{release}
BuildArch:      noarch
%description -n python3-scikit-build-core+pyproject
This is a metapackage bringing in pyproject extras requires for
python3-scikit-build-core.
It makes sure the dependencies are installed.

%files -n python3-scikit-build-core+pyproject -f %{_pyproject_ghost_distinfo}


%prep
%autosetup -n scikit_build_core-%{version}


%generate_buildrequires
%pyproject_buildrequires -x test,test-meta,test-numpy,pyproject


%build
%pyproject_wheel


%install
%pyproject_install
%pyproject_save_files scikit_build_core


%check
%pytest \
    -m "not network"


%files -n python3-scikit-build-core -f %{pyproject_files}
%license LICENSE
%doc README.md


%changelog
%autochangelog
