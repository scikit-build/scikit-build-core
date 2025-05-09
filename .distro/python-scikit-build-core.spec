%global debug_package %{nil}

# On epel python hatch/trove classifier check may fail because of old package
# Fedora checks should be sufficient though.
%bcond no_classifier_check 0%{?rhel}

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
%if %{with no_classifier_check}
export HATCH_METADATA_CLASSIFIERS_NO_VERIFY=1
%endif
%pyproject_buildrequires -x test,test-meta,test-numpy


%build
%if %{with no_classifier_check}
export HATCH_METADATA_CLASSIFIERS_NO_VERIFY=1
%endif
%pyproject_wheel


%install
%pyproject_install
%pyproject_save_files scikit_build_core


%check
%pyproject_check_import
%pytest \
    -m "not network"


%files -n python3-scikit-build-core -f %{pyproject_files}
%license LICENSE LICENSE-pyproject-metadata
%doc README.md


%changelog
%autochangelog
