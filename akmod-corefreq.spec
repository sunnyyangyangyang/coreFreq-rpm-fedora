%global kmod_name corefreq

Name:          akmod-%{kmod_name}
Version:       2.0.7
Release:       1%{?dist}
Summary:       Metapackage to install CoreFreq kernel module sources and akmods

License:       GPL-2.0-only
URL:           https://github.com/cyring/CoreFreq

Requires:      akmods
Requires:      corefreq-kmod-source = %{version}-%{release}

%description
This is a metapackage that enables the automatic building of the
CoreFreq kernel module for your system using the akmods service.

%files
# This package owns no files.