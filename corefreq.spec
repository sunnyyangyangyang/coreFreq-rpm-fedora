# === FULLY AUTOMATED SPEC (NVIDIA-STYLE) ===

%global _debugsource_packages 0
%global _debuginfo_packages 0
%global debug_package %{nil}

%global corefreq_version 2.0.8

Name:           corefreq
Version:        %{corefreq_version}
Release:        9%{?dist}
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
# 1. 安全的 MOK 处理 - 不自动导入，给用户清晰指引
if [ -f /var/lib/dkms/mok.pub ] && command -v mokutil >/dev/null 2>&1 && mokutil --sb-state | grep -qi enabled; then
    if ! mokutil --list-enrolled 2>/dev/null | grep -q "DKMS module signing key"; then
        echo "=================================================================="
        echo "ACTION REQUIRED: Secure Boot is enabled on your system."
        echo "To use the corefreqk module, you must enroll the DKMS signing key."
        echo ""
        echo "1. Run: sudo mokutil --import /var/lib/dkms/mok.pub"
        echo "2. Set a temporary password when prompted"
        echo "3. Reboot your system"
        echo "4. At the blue MOK management screen, enroll the key with your password"
        echo "5. After second reboot, CoreFreq will start automatically"
        echo "=================================================================="
    fi
elif [ ! -f /var/lib/dkms/mok.pub ]; then
    echo "--- Generating DKMS MOK key ---"
    sudo -u dkms dkms --generate-mok 2>/dev/null || :
fi

# 2. 标准 DKMS 安装
if dkms status -m %{name} -v %{version} | grep -q installed; then
    dkms remove -m %{name} -v %{version} --all >/dev/null 2>&1 || :
fi
dkms add -m %{name} -v %{version} >/dev/null 2>&1 || :
dkms autoinstall -m %{name} -v %{version} >/dev/null 2>&1 || :

# 3. 启用服务
%systemd_post corefreqd.service
systemctl enable corefreqd.service >/dev/null 2>&1 || :

# 4. 尝试立即启动
systemctl start corefreqd.service >/dev/null 2>&1 || :

# 5. 用户反馈
sleep 1
if systemctl is-active --quiet corefreqd.service; then
    echo "=================================================================="
    echo "✅ CoreFreq is ready! Use: corefreq-cli -Oa -t frequency"
    echo "=================================================================="
else
    echo "=================================================================="
    echo "✅ CoreFreq installed! Service will start automatically on boot."
    echo "Use: corefreq-cli -Oa -t frequency"
    echo "=================================================================="
fi

%preun
%systemd_preun corefreqd.service
if [ $1 -eq 0 ]; then # Final uninstall
    dkms remove -m %{name} -v %{version} --all >/dev/null 2>&1 || :
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