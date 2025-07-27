# File: corefreq.spec
%global debug_package %{nil}
%global srcname CoreFreq

Name:           corefreq
Version:        2.0.7
Release:        1%{?dist}
Summary:        CPU monitoring and tuning software (user-space tools and kernel module)

License:        GPL-2.0-only
URL:            https://github.com/cyring/CoreFreq
Source0:        %{url}/archive/refs/tags/%{version}.tar.gz

# BuildRequires for this package's contents (the user-space tools)
BuildRequires:  gcc
BuildRequires:  make
BuildRequires:  systemd-rpm-macros

# THIS IS THE KEY: Installing 'corefreq' now pulls in 'corefreq-dkms'.
Requires:       corefreq-dkms = %{version}-%{release}

%description
CoreFreq is a CPU monitoring software with BIOS-like functionalities.

This package provides the user-space tools (corefreqd, corefreq-cli) and
systemd service. It depends on the corefreq-dkms package to automatically
build and install the required 'corefreqk' kernel module.

After installation, the module will be loaded and the service will be enabled.

%prep
%autosetup -n %{srcname}-%{version}

%build
mkdir -p build
# Build only the user-space tools. The kernel module is handled by DKMS.
make %{?_smp_mflags} CFLAGS="%{optflags}" corefreqd corefreq-cli

%install
# Install the daemon and the command-line client.
install -D -m 0755 build/corefreqd %{buildroot}%{_sbindir}/corefreqd
install -D -m 0755 build/corefreq-cli %{buildroot}%{_bindir}/corefreq-cli

# Install the systemd service file.
install -D -m 0644 corefreqd.service %{buildroot}%{_unitdir}/corefreqd.service

%post
# This enables the service to start on boot.
%systemd_post corefreqd.service

%preun
%systemd_preun corefreqd.service

%postun
# This restarts the service on upgrade, if it was running.
%systemd_postun_with_restart corefreqd.service

%files
%doc README.md
%license LICENSE
%{_sbindir}/corefreqd
%{_bindir}/corefreq-cli
%{_unitdir}/corefreqd.service

%changelog
* Tue Jul 30 2024 Your Name <youremail@example.com> - 2.0.7-1
- Unified package that depends on corefreq-dkms for a complete setup.