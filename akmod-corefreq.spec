# File: akmod-corefreq.spec
%global debug_package %{nil}
%global kmod_name corefreq

Name:          akmod-%{kmod_name}
Version:       2.0.7
Release:       1%{?dist}
Summary:       Akmod package for the %{kmod_name} kernel module

License:       GPL-2.0-only
URL:           https://github.com/cyring/CoreFreq

# Source0: The official upstream source tarball.
Source0:       %{url}/archive/refs/tags/%{version}.tar.gz
# Source1: The template file, downloaded from YOUR Git repo at the specific commit being built.
Source1:       https://raw.githubusercontent.com/sunnyyangyangyang/coreFreq-rpm-fedora/%{githash}/kmod-%{kmod_name}.spec.template

Requires:      akmods
BuildRequires: kmod-devel

%description
This package installs the CoreFreq kernel module source and template RPMs.
The akmods service will use these to build a kmod-corefreq package for your
running kernel.

%install
# Create the directories where akmods expects to find files.
install -d %{buildroot}%{_usrsrc}/akmods/SOURCES
install -d %{buildroot}%{_usrsrc}/akmods/

# Install the source tarball (Source0) into the SOURCES directory.
install -p -m 0644 %{SOURCE0} %{buildroot}%{_usrsrc}/akmods/SOURCES/

# Install the template spec (Source1) and replace the version placeholder.
install -p -m 0644 %{SOURCE1} %{buildroot}%{_usrsrc}/akmods/kmod-%{kmod_name}.spec
sed -i 's/__VERSION__/%{version}/g' %{buildroot}%{_usrsrc}/akmods/kmod-%{kmod_name}.spec

%files
%dir %{_usrsrc}/akmods
%dir %{_usrsrc}/akmods/SOURCES
%{_usrsrc}/akmods/SOURCES/CoreFreq-%{version}.tar.gz
%{_usrsrc}/akmods/kmod-%{kmod_name}.spec

%changelog
* Tue Jul 30 2024 sunnyyangyangyang <youremail@example.com> - 2.0.7-1
- Initial akmod package for COPR SCM build.