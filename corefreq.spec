%global debug_package %{nil}
%global srcname CoreFreq

Name:           corefreq
Version:        2.0.7
Release:        1%{?dist}
Summary:        CPU monitoring and tuning software (user-space tools)

License:        GPL-2.0-only
URL:            https://github.com/cyring/CoreFreq
Source0:        %{url}/archive/refs/tags/%{version}.tar.gz

BuildRequires:  gcc make systemd-rpm-macros

Requires:       akmod-corefreq = %{version}-%{release}

%description
CoreFreq is a CPU monitoring software with BIOS-like functionalities.
This package provides the user-space tools and depends on the akmod-corefreq
package to provide the required kernel module.

%prep
%autosetup -n %{srcname}-%{version}

%build
make %{?_smp_mflags} CFLAGS="%{optflags}" corefreqd corefreq-cli

%install
install -D -m 0755 build/corefreqd %{buildroot}%{_sbindir}/corefreqd
install -D -m 0755 build/corefreq-cli %{buildroot}%{_bindir}/corefreq-cli
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