%global debug_package %{nil}
%global srcname CoreFreq

Name:           corefreq
Version:        2.0.7
# Small Change: Using %{?dist} to work on all Fedora versions.
Release:        1%{?dist}
# Small Change: Summary reflects its new role.
Summary:        CPU monitoring and tuning software (user-space tools)

License:        GPL-2.0-only
URL:            https://github.com/cyring/CoreFreq

Source0:        %{url}/archive/refs/tags/%{version}.tar.gz

# Small Change: Remove DKMS/kernel build requirements. Add systemd macros.
BuildRequires:  gcc make systemd-rpm-macros

# CRITICAL CHANGE: This is the dependency you requested.
# It makes 'dnf install corefreq' automatically install 'akmod-corefreq'.
Requires:       akmod-corefreq

%description
CoreFreq is a CPU monitoring software with BIOS-like functionalities.
This package provides the user-space tools and depends on the akmod-corefreq
package to provide the required kernel module.

%prep
%autosetup -n %{srcname}-%{version}

%build
mkdir -p build
make %{?_smp_mflags} CFLAGS="%{optflags}" corefreqd corefreq-cli

%install
# This part is the same, installing only the tools and service file.
install -D -m 0755 build/corefreqd %{buildroot}%{_sbindir}/corefreqd
install -D -m 0755 build/corefreq-cli %{buildroot}%{_bindir}/corefreq-cli
install -D -m 0644 corefreqd.service %{buildroot}%{_unitdir}/corefreqd.service

# SMALL CHANGE: All DKMS install logic has been removed as it is now handled by akmods.

# SMALL CHANGE: Using standard systemd macros for clean service management.
%post
%systemd_post corefreqd.service

%preun
%systemd_preun corefreqd.service

%postun
%systemd_postun_with_restart corefreqd.service

%files
# This part is the same, but we remove the lines for DKMS files.
%doc README.md
%license LICENSE
%{_sbindir}/corefreqd
%{_bindir}/corefreq-cli
%{_unitdir}/corefreqd.service

%changelog
* Mon Jul 29 2024 Your Name <youremail@example.com> - 2.0.7-1
- Converted from DKMS to an akmod-dependent package for a seamless install.