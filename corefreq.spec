%global debug_package %{nil}
%global srcname CoreFreq

Name:           corefreq
Version:        2.0.7
Release:        1%{?dist}
Summary:        CPU monitoring and tuning software with kernel module support

License:        GPL-2.0-only
URL:            https://github.com/cyring/CoreFreq
Source0:        %{url}/archive/refs/tags/%{version}.tar.gz

# We only need systemd macros for the service, and gcc/make to build.
BuildRequires:  gcc make systemd-rpm-macros

# This is the key. It makes the install simple for the user.
Requires:       akmod-corefreq

%description
CoreFreq is a CPU monitoring software with BIOS-like functionalities.
This package provides the user-space tools and automatically installs the
'akmod-corefreq' package to manage the kernel module.

%prep
%autosetup -n %{srcname}-%{version}

%build
# Create the build directory, as required by the Makefile.
mkdir -p build
# Build ONLY the user-space tools.
make %{?_smp_mflags} CFLAGS="%{optflags}" corefreqd corefreq-cli

%install
# Install ONLY the user-space files.
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
- Final version using the akmods framework for a clean, one-command install.