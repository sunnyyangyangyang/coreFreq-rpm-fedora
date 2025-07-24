%global debug_package %{nil}
%global kmod_name corefreq

Name:          akmod-%{kmod_name}
Version:       2.0.7
Release:       1.fc42
Summary:       Akmod package for the %{kmod_name} kernel module

License:       GPL-2.0-only
URL:           https://github.com/cyring/CoreFreq

Source0:       https://github.com/cyring/CoreFreq/archive/refs/tags/%{version}.tar.gz
Source1:       kmod-%{kmod_name}.spec.in

Requires:      akmods
Requires:      corefreq = %{version}-%{release}
BuildRequires: kmod-devel
BuildRequires: sed

%description
This package installs the CoreFreq kernel module source and template RPMs.
The akmods service will use these to build a kmod-corefreq package for your
running kernel.

%install
mkdir -p %{buildroot}%{_usrsrc}/akmods/SOURCES
install -p -m 0644 %{SOURCE0} %{buildroot}%{_usrsrc}/akmods/SOURCES/CoreFreq-%{version}.tar.gz
install -p -m 0644 %{SOURCE1} %{buildroot}%{_usrsrc}/akmods/kmod-%{kmod_name}.spec
sed -i 's|@VERSION@|%{version}|g' %{buildroot}%{_usrsrc}/akmods/kmod-%{kmod_name}.spec
sed -i 's|@RELEASE@|%{release}|g' %{buildroot}%{_usrsrc}/akmods/kmod-%{kmod_name}.spec

# NO SCRIPTLETS HERE. They are unreliable during the transaction.

%files
%dir %{_usrsrc}/akmods
%dir %{_usrsrc}/akmods/SOURCES
%{_usrsrc}/akmods/SOURCES/CoreFreq-%{version}.tar.gz
%{_usrsrc}/akmods/kmod-%{kmod_name}.spec

%changelog
* Thu Jul 25 2024 Your Name <youremail@example.com> - 2.0.7-14
- Final implementation: Removed unreliable %%post scriptlet trigger.
- The build is now triggered manually by the user post-install, or
  automatically on the next kernel update, which is the robust way.