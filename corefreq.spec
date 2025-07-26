# File: corefreq.spec
%global debug_package %{nil}
%global srcname CoreFreq

Name:           corefreq
Version:        2.0.7
Release:        1%{?dist}
Summary:        CPU monitoring and tuning software (user-space tools)

License:        GPL-2.0-only
URL:            https://github.com/cyring/CoreFreq
Source0:        %{url}/archive/refs/tags/%{version}.tar.gz

BuildRequires:  gcc make
BuildRequires:  systemd-rpm-macros

Requires:       akmod-corefreq

%description
CoreFreq is a CPU monitoring software with BIOS-like functionalities.
This package provides the user-space tools and depends on the akmod-corefreq
package to provide the required kernel module.

%prep
%autosetup -n %{srcname}-%{version}

%build
# Explicitly create the build directory for robustness.
mkdir -p build
# Build only the user-space tools, not the kernel module.
make %{?_smp_mflags} CFLAGS="%{optflags}" corefreqd corefreq-cli

%install
# Install the daemon and the command-line client from the build directory.
install -D -m 0755 build/corefreqd %{buildroot}%{_sbindir}/corefreqd
install -D -m 0755 build/corefreq-cli %{buildroot}%{_bindir}/corefreq-cli
# Install the systemd service file.
install -D -m 0644 corefreqd.service %{buildroot}%{_unitdir}/corefreqd.service

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
* Tue Jul 30 2024 sunnyyangyangyang <youremail@example.com> - 2.0.7-1
- Finalized standard akmod packaging model.