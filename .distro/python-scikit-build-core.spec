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
Suggests:       ninja-build
Suggests:       gcc

BuildArch:      noarch

# Deprecated extras/optional-dependencies
# Provides python3dist() do not seem to be generated, defining them manually
# Note: the version can be a bit off if the python metadata version is different than RPM.
#   It shouldn't be an issue in this package.
%py_provides    python3-scikit-build-core+pyproject
Provides:       python3dist(scikit-build-core[pyproject]) = %{version}
Provides:       python%{python3_version}dist(scikit-build-core[pyproject]) = %{version}
Obsoletes:      python3-scikit-build-core+pyproject < 0.11.0-1%{?dist}

%description -n python3-scikit-build-core %_description


%prep
%autosetup -n scikit_build_core-%{version}


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
%license LICENSE
%doc README.md


%changelog
%autochangelog
