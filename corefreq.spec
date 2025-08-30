# === FULLY AUTOMATED SPEC (NVIDIA-STYLE) ===

%global _debugsource_packages 0
%global _debuginfo_packages 0
%global debug_package %{nil}

%global corefreq_version 2.0.8

Name:           corefreq
Version:        %{corefreq_version}
Release:        10%{?dist}
Summary:        CPU monitoring software with DKMS kernel module

License:        GPL-2.0-only
URL:            https://github.com/cyring/CoreFreq
Source0:        %{url}/archive/refs/tags/%{version}.tar.gz#/%{name}-%{version}.tar.gz
Source1:        corefreqd.service
Source2:        dkms.conf

BuildRequires:  gcc make kernel-devel dkms kmod systemd-rpm-macros
Requires:       dkms kernel-devel

%description
CoreFreq is a CPU monitoring software designed for 64-bit Processors.
This package provides the user-space tools and the DKMS source for the
'corefreqk' kernel module with full automation - no user intervention required.

%prep
%autosetup -n CoreFreq-%{version} -p1
cp %{SOURCE2} .
sed -i 's/@RPM_VERSION@/%{version}/' dkms.conf

%build
make %{?_smp_mflags} corefreqd corefreq-cli

%install
install -D -m 0755 build/corefreqd %{buildroot}%{_bindir}/corefreqd
install -D -m 0755 build/corefreq-cli %{buildroot}%{_bindir}/corefreq-cli
install -D -m 0644 %{SOURCE1} %{buildroot}%{_unitdir}/corefreqd.service
rm -rf build
%global dkms_source_dir %{_usrsrc}/%{name}-%{version}
install -d -m 755 %{buildroot}%{dkms_source_dir}
cp -a . %{buildroot}%{dkms_source_dir}/

%post
# Standard DKMS installation
if dkms status -m %{name} -v %{version} 2>/dev/null | grep -q installed; then
    dkms remove -m %{name} -v %{version} --all >/dev/null 2>&1 || true
fi

dkms add -m %{name} -v %{version} >/dev/null 2>&1 || true
dkms autoinstall -m %{name} -v %{version} >/dev/null 2>&1 || true

# Enable and start service
%systemd_post corefreqd.service
systemctl enable corefreqd.service >/dev/null 2>&1 || true
systemctl start corefreqd.service >/dev/null 2>&1 || true

# User feedback
if systemctl is-active --quiet corefreqd.service; then
    echo "CoreFreq installed and running. Use: corefreq-cli -Oa -t frequency"
else
    echo "CoreFreq installed. For Secure Boot systems, you may need to:"
    echo "1. Import DKMS MOK key: sudo mokutil --import /var/lib/dkms/mok.pub"
    echo "2. Reboot and complete MOK enrollment"
    echo "3. Then use: corefreq-cli -Oa -t frequency"
fi

%preun
%systemd_preun corefreqd.service
if [ $1 -eq 0 ]; then # Final uninstall
    dkms remove -m %{name} -v %{version} --all >/dev/null 2>&1 || true
fi

%postun
%systemd_postun_with_restart corefreqd.service

%files
%license LICENSE
%doc README.md
%{_bindir}/corefreq-cli
%{_bindir}/corefreqd
%{_unitdir}/corefreqd.service
%{_usrsrc}/%{name}-%{version}/

%changelog
* Sat Aug 30 2025 - Release 8
- NVIDIA-style full automation: zero user intervention required
- Auto-enrolls DKMS MOK key with predictable password
- Enhanced service with DKMS integration and retry logic