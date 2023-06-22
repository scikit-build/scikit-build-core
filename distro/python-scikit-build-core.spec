Name:           python-scikit-build-core
Version:        0.0.0
Release:        %autorelease
Summary:        Build backend for CMake based projects

License:        Apache-2.0
URL:            https://github.com/scikit-build/scikit-build-core
Source:         %{pypi_source scikit_build_core}

BuildArch:      noarch
BuildRequires:  python3-devel
# Testing dependences
BuildRequires:  cmake
BuildRequires:  ninja-build
BuildRequires:  gcc
BuildRequires:  gcc-c++
BuildRequires:  git

%global _description %{expand:
A next generation Python CMake adaptor and Python API for plugins
}

%description %_description

%package -n python3-scikit-build-core
Summary:        %{summary}
Requires:       cmake
Recommends:     (ninja-build or make)
Recommends:     python3dist(pyproject-metadata)
Recommends:     python3dist(pathspec)
Suggests:       ninja-build
Suggests:       gcc
%description -n python3-scikit-build-core %_description


%prep
%autosetup -n scikit_build_core-%{version}


%generate_buildrequires
%pyproject_buildrequires -x test,test-meta,test-numpy


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
