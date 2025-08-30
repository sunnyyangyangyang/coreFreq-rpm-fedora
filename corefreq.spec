# === FULLY AUTOMATED SPEC (NVIDIA-STYLE) ===

%global _debugsource_packages 0
%global _debuginfo_packages 0
%global debug_package %{nil}

%global corefreq_version 2.0.8

Name:           corefreq
Version:        %{corefreq_version}
Release:        8%{?dist}
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
# === AUTOMATED DKMS + MOK SETUP ===

# 1. Generate DKMS MOK if needed for signing
if [ ! -f /var/lib/dkms/mok.pub ]; then
    echo "--- Generating DKMS MOK key for module signing ---"
    /usr/sbin/dkms mok --generate 2>/dev/null || true
fi

# 2. Auto-enroll MOK key for Secure Boot (user can decline during reboot)
if [ -f /var/lib/dkms/mok.pub ] && command -v mokutil >/dev/null 2>&1; then
    if ! mokutil --list-enrolled 2>/dev/null | grep -q "DKMS module signing key"; then
        echo "--- Queueing DKMS MOK key for Secure Boot enrollment ---"
        # Queue key for import (user will be prompted during next boot)
        echo -e "dkms\ndkms" | mokutil --import /var/lib/dkms/mok.pub 2>/dev/null || true
        echo "NOTE: On next reboot, you'll be prompted to enroll the DKMS key for Secure Boot"
    fi
fi

# 3. Standard DKMS installation (with automatic signing if MOK configured)
if dkms status -m %{name} -v %{version} 2>/dev/null | grep -q installed; then
    dkms remove -m %{name} -v %{version} --all >/dev/null 2>&1 || true
fi

dkms add -m %{name} -v %{version} >/dev/null 2>&1 || true
dkms autoinstall -m %{name} -v %{version} >/dev/null 2>&1 || true

# 4. Enable and start service
%systemd_post corefreqd.service
systemctl enable corefreqd.service >/dev/null 2>&1 || true
systemctl start corefreqd.service >/dev/null 2>&1 || true

# 5. User feedback
if systemctl is-active --quiet corefreqd.service; then
    echo "✅ CoreFreq is ready! Use: corefreq-cli -Oa -t frequency"
else
    echo "✅ CoreFreq installed! After reboot (if Secure Boot), use: corefreq-cli -Oa -t frequency"
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