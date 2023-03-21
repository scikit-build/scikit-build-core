Name:           python-scikit-build-core
Version:        0.2.2
Release:        %{autorelease}
Summary:        Build backend for CMake based projects

License:        Apache-2.0
URL:            https://github.com/scikit-build/scikit-build-core
Source0:        https://github.com/scikit-build/scikit-build-core/archive/refs/tags/v%{version}.tar.gz

BuildArch:      noarch
BuildRequires:  python3-devel
BuildRequires:  cmake
BuildRequires:  ninja-build
BuildRequires:  gcc
BuildRequires:  gcc-c++
Requires:       cmake
Recommends:     (ninja-build or make)
Recommends:     python3dist(pyproject-metadata)
Recommends:     python3dist(pathspec)
Suggests:       ninja-build
Suggests:       gcc

%global _description %{expand:
A next generation Python CMake adaptor and Python API for plugins}

%description %_description

%package -n python3-scikit-build-core
Summary:        %{summary}
%description -n python3-scikit-build-core %_description

%prep
# This assumes the source is not retrieved from tar ball, but built in place
# This makes it possible to build with `tito build --test`
# Change to `%%autosetup -n %%{pypi_name}-%%{version}` for release
# TODO: There should be a format to satisfy both
%setup -q
# TODO: Remove when tito upstream issue is fixed
# https://github.com/rpm-software-management/tito/issues/444
if grep -q "describe-name: \$Format" .git_archival.txt; then
   sed -i "s/describe-name:.*/describe-name: v%{version}/g" .git_archival.txt
fi

%generate_buildrequires
%pyproject_buildrequires -x test

%build
%pyproject_wheel


%install
%pyproject_install
%pyproject_save_files scikit_build_core


%check
%pytest \
    -m "not isolated"


%files -n python3-scikit-build-core -f %{pyproject_files}
%license LICENSE
%doc README.md

%changelog
%autochangelog
