%global debug_package %{nil}
%global srcname CoreFreq

Name:           corefreq
Version:        2.0.7
Release:        1%{?dist}
Summary:        CPU monitoring and tuning software with kernel module support

License:        GPL-2.0-only
URL:            https://github.com/cyring/CoreFreq
Source0:        %{url}/archive/refs/tags/%{version}.tar.gz

BuildRequires:  gcc make systemd-rpm-macros

# This is the key to the one-command install experience.
# It tells DNF to automatically install 'akmod-corefreq' as well.
Requires:       akmod-corefreq

%description
CoreFreq is a CPU monitoring software with BIOS-like functionalities.

This package provides the user-space daemon (corefreqd) and the
command-line interface (corefreq-cli). It automatically installs the
'akmod-corefreq' package to build and manage the required 'corefreqk'
kernel module.

%prep
%autosetup -n %{srcname}-%{version}

%build
mkdir -p build
# Build only the user-space tools. The kernel module is handled by akmod.
make %{?_smp_mflags} CFLAGS="%{optflags}" corefreqd corefreq-cli

%install
install -D -m 0755 build/corefreqd %{buildroot}%{_sbindir}/corefreqd
install -D -m 0755 build/corefreq-cli %{buildroot}%{_bindir}/corefreq-cli
install -D -m 0644 corefreqd.service %{buildroot}%{_unitdir}/corefreqd.service

# Use standard systemd macros for clean service management.
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
- Final version using akmods for a seamless one-command install.
- Added hard dependency on akmod-corefreq.
- Implemented standard systemd macros for service management.