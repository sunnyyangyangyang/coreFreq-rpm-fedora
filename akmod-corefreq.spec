%global debug_package %{nil}
%global kmod_name corefreq

Name:          akmod-%{kmod_name}
Version:       2.0.7
Release:       1%{?dist}
Summary:       Akmod package for the %{kmod_name} kernel module

License:       GPL-2.0-only
URL:           https://github.com/cyring/CoreFreq

Source0:       %{url}/archive/refs/tags/%{version}.tar.gz
Source1:       kmod-%{kmod_name}.spec.in

# This package requires the akmods service to function.
Requires:      akmods
BuildRequires: kmod-devel
BuildRequires: sed

# IMPORTANT: No 'Requires: corefreq' here, as that would create a circular dependency.

%description
This package installs the CoreFreq kernel module source and template RPMs.
The akmods service will use these to build a kmod-corefreq package for your
running kernel. This package is automatically installed as a dependency of
the main 'corefreq' package.

%install
mkdir -p %{buildroot}%{_usrsrc}/akmods/SOURCES
install -p -m 0644 %{SOURCE0} %{buildroot}%{_usrsrc}/akmods/SOURCES/CoreFreq-%{version}.tar.gz
install -p -m 0644 %{SOURCE1} %{buildroot}%{_usrsrc}/akmods/kmod-%{kmod_name}.spec
sed -i 's|@VERSION@|%{version}|g' %{buildroot}%{_usrsrc}/akmods/kmod-%{kmod_name}.spec
sed -i 's|@RELEASE@|%{release}|g' %{buildroot}%{_usrsrc}/akmods/kmod-%{kmod_name}.spec

%files
%dir %{_usrsrc}/akmods
%dir %{_usrsrc}/akmods/SOURCES
%{_usrsrc}/akmods/SOURCES/CoreFreq-%{version}.tar.gz
%{_usrsrc}/akmods/kmod-%{kmod_name}.spec

%changelog
* Sun Jul 28 2024 Your Name <youremail@example.com> - 2.0.7-1
- Initial akmods version, pulled in automatically by the corefreq package.