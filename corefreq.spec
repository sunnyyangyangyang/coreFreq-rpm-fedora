%global debug_package %{nil}
%global srcname CoreFreq

Name:           corefreq
Version:        2.0.7
Release:        1%{?dist}
Summary:        User-space daemon and CLI for CoreFreq

License:        GPL-2.0-only
URL:            https://github.com/cyring/CoreFreq
Source0:        %{url}/archive/refs/tags/%{version}.tar.gz

# DKMS and kernel dependencies are REMOVED.
BuildRequires:  gcc make systemd-rpm-macros

%description
This package provides the user-space daemon (corefreqd) and the
command-line interface (corefreq-cli). It is installed as a dependency
of the akmod-corefreq package.

%prep
%autosetup -n %{srcname}-%{version}

%build
mkdir -p build
make %{?_smp_mflags} CFLAGS="%{optflags}" corefreqd corefreq-cli

%install
# Install ONLY the user-space files. NO DKMS steps.
install -D -m 0755 build/corefreqd %{buildroot}%{_sbindir}/corefreqd
install -D -m 0755 build/corefreq-cli %{buildroot}%{_bindir}/corefreq-cli
install -D -m 0644 corefreqd.service %{buildroot}%{_unitdir}/corefreqd.service

# Use standard systemd macros. NO DKMS or modprobe logic.
%post
%systemd_post corefreqd.service

%preun
%systemd_preun corefreqd.service

%postun
%systemd_postun_with_restart corefreqd.service

%files
%doc README.md
%license LICENSE
%{_sbindir}/corefreqd
%{_bindir}/corefreq-cli
%{_unitdir}/corefreqd.service

%changelog
* Sun Jul 28 2024 Your Name <youremail@example.com> - 2.0.7-1
- Corrected logic: Removed all DKMS functionality to serve as a dependency for akmods.