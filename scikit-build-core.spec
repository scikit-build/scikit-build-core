%global forgeurl https://github.com/scikit-build/scikit-build-core
# TODO: Retrieve version dynamically. Might not work in copr though

Name:           python-scikit-build-core
Version:        0.2.1
Release:        1%{?dist}
Summary:        Build backend for CMake based projects
%forgemeta

License:        ASL 2.0
URL:            %{forgeurl}
Source0:        %{forgesource}

BuildArch:      noarch
BuildRequires:  python3-devel
BuildRequires:  python3dist(hatchling)
BuildRequires:  python3dist(hatch-vcs)
# TODO: Remove when irrelevant
# Required by commit https://github.com/pypa/setuptools_scm/commit/4c2cf6e3a369afa05131d6fb3d790822b019abf0
BuildRequires:  python3-setuptools_scm >= 7.1.0
BuildRequires:  cmake
BuildRequires:  ninja-build
BuildRequires:  gcc
BuildRequires:  gcc-c++
BuildRequires:  git
Recommends:     (ninja-build or make)
Suggests:       gcc
Suggests:       clang
Requires:       python3dist(pyproject-metadata)
Requires:       python3dist(pathspec)

%global _description %{expand:
A next generation Python CMake adaptor and Python API for plugins}

%description %_description

%package -n python3-scikit-build-core
Summary:        %{summary}
%description -n python3-scikit-build-core %_description

%prep
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
%license

%changelog
%autochangelog
