%global debug_package %{nil}

# Whether to run additional tests, enabled by default
%bcond optional_tests 1

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
Requires:       ninja-build
BuildArch:      noarch

Provides:       bundled(python3dist(pyproject-metadata)) = 0.9.1

Obsoletes:      python3-scikit-build-core+pyproject < 0.10.7-3

%description -n python3-scikit-build-core %_description


%prep
%autosetup -n scikit_build_core-%{version}
# Rename the bundled license so that it can be installed together
cp -p src/scikit_build_core/_vendor/pyproject_metadata/LICENSE LICENSE-pyproject-metadata


%generate_buildrequires
export HATCH_METADATA_CLASSIFIERS_NO_VERIFY=1
%pyproject_buildrequires -g test%{?with_optional_tests:,test-meta,test-numpy,test-pybind11}


%build
export HATCH_METADATA_CLASSIFIERS_NO_VERIFY=1
%pyproject_wheel


%install
%pyproject_install
%pyproject_save_files scikit_build_core


%check
%pyproject_check_import
# Additional tests from optional_tests are automatically skipped/picked-up by pytest
%pytest \
    -m "not network"


%files -n python3-scikit-build-core -f %{pyproject_files}
%license LICENSE LICENSE-pyproject-metadata
%doc README.md


%changelog
%autochangelog
