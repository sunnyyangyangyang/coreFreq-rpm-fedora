# Filename: corefreq-kmod.spec
# This is the "inner" spec file used by the akmods system on the user's machine.
# It is NOT built directly by COPR.

%global kmod_name corefreq
%global corefreq_version 2.0.8

Name:          %{kmod_name}-kmod
Version:       %{corefreq_version}
Release:       1%{?dist}
Summary:       The %{kmod_name} kernel module for CoreFreq

License:       GPL-2.0-only
URL:           https://github.com/cyring/CoreFreq

# The sources will be provided by the akmods system from the tarball.
Source0:       %{kmod_name}-%{version}.tar.gz
Source1:       Makefile.akmod

BuildRequires: kmodtool
BuildRequires: gcc make
BuildRequires: kernel-devel

# This is the standard macro for building kmod packages.
%kmod_pkg

%description
This package provides the %{kmod_name} kernel module, built by the akmods system.

%prep
%autosetup -n CoreFreq-%{version} -p1
# Replace the original Makefile with our akmod-compatible one.
cp %{SOURCE1} Makefile

%build
# Standard macro to build the kernel module.
%make_kmod

%install
# Standard macro to install the built kernel module.
%install_kmod

%changelog
* Mon Sep 08 2025 Your Name <your@email.com> - 2.0.8-1
- Initial spec for building the kmod via akmods.