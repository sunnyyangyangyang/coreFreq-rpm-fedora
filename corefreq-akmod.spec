# === AKMOD SPEC FILE ===

%global _debugsource_packages 0
%global _debuginfo_packages 0
%global debug_package %{nil}

%global corefreq_version 2.0.8
%global buildforkernels akmod
%global debug 0

Name:           corefreq
Version:        %{corefreq_version}
Release:        1.alpha3%{?dist}
Summary:        CPU monitoring software with akmod kernel module

License:        GPL-2.0-only
URL:            https://github.com/cyring/CoreFreq
Source0:        %{url}/archive/refs/tags/%{version}.tar.gz#/%{name}-%{version}.tar.gz
Source1:        corefreqd.service
Source2:        Makefile.akmod

# Akmod BuildRequires
BuildRequires:  kmodtool
BuildRequires:  gcc make
BuildRequires:  systemd-rpm-macros
%{!?kernels:BuildRequires: buildsys-build-rpmfusion-kerneldevpkgs-%{?buildforkernels:%{buildforkernels}}%{!?buildforkernels:current}-%{_target_cpu}}

# Generate akmod metadata
%{expand:%(kmodtool --target %{_target_cpu} --kmodname %{name} --pattern ".*" %{?buildforkernels:--%{buildforkernels}} %{?kernels:--for-kernels "%{?kernels}"} 2>/dev/null) }

%description
CoreFreq is a CPU monitoring software designed for 64-bit Processors.
This package provides the user-space tools and the akmod source for the
'corefreqk' kernel module with full automation.

%package -n akmod-%{name}
Summary:        Akmod package for %{name} kernel module(s)
Requires:       kmodtool
Requires:       akmods
Provides:       %{name}-kmod = %{?epoch:%{epoch}:}%{version}
Requires:       %{name}-kmod-common >= %{?epoch:%{epoch}:}%{version}

%description -n akmod-%{name}
This package provides the akmod package for the %{name} kernel modules.

%package kmod-common
Summary:        Common files for %{name} kernel module
Requires:       %{name} = %{?epoch:%{epoch}:}%{version}-%{release}
Provides:       %{name}-kmod-common = %{?epoch:%{epoch}:}%{version}

%description kmod-common
This package provides the common files for the %{name} kernel modules.

%prep
%autosetup -n CoreFreq-%{version} -p1

# Replace original Makefile with akmod-compatible version
cp %{SOURCE2} Makefile

%build
# Build userspace tools only
make %{?_smp_mflags} userspace

%install
# Install userspace binaries
install -D -m 0755 build/corefreqd %{buildroot}%{_bindir}/corefreqd
install -D -m 0755 build/corefreq-cli %{buildroot}%{_bindir}/corefreq-cli
install -D -m 0644 %{SOURCE1} %{buildroot}%{_unitdir}/corefreqd.service

# Create akmod source package
mkdir -p %{buildroot}%{_usrsrc}/akmods/
tar -czf %{buildroot}%{_usrsrc}/akmods/%{name}-%{version}-%{release}.tar.gz \
    --exclude-vcs \
    --exclude='build/*' \
    --exclude='*.o' \
    --exclude='*.ko' \
    --exclude='*.mod.*' \
    --exclude='.tmp_versions' \
    --exclude='Module.symvers' \
    --exclude='modules.order' \
    -C %{_builddir} CoreFreq-%{version}/

%post
# === AUTOMATED AKMOD + MOK SETUP ===

# 1. Auto-enroll MOK key for Secure Boot
if [ -f /etc/pki/akmods/certs/public_key.der ] && command -v mokutil >/dev/null 2>&1; then
    if ! mokutil --list-enrolled 2>/dev/null | grep -q "akmods"; then
        MOK_PASSWORD=$(openssl rand -hex 8 2>/dev/null || printf "%08x" $((RANDOM * RANDOM)))
        echo "--- Queueing akmods MOK key for Secure Boot enrollment ---"
        echo -e "$MOK_PASSWORD\n$MOK_PASSWORD" | mokutil --import /etc/pki/akmods/certs/public_key.der 2>/dev/null || true

        cat << EOF
------------------------------------------------------------------
ATTENTION: SECURE BOOT - MOK KEY ENROLLMENT REQUIRED
The akmods signing key has been queued for enrollment.
Your temporary MOK password is: $MOK_PASSWORD

To complete the setup:
1. Reboot your computer.
2. At the blue 'MOK Manager' screen that appears on boot,
   select 'Enroll MOK' and follow the prompts.
3. Enter the password shown above: $MOK_PASSWORD

After the reboot, the module will load automatically for all
future kernel updates.
------------------------------------------------------------------
EOF
    fi
fi

# 2. Enable and start service
%systemd_post corefreqd.service
systemctl enable corefreqd.service >/dev/null 2>&1 || true

# 3. Trigger akmod build for current kernel
if [ -x %{_bindir}/akmods ]; then
    echo "Building kernel module for current kernel..."
    %{_bindir}/akmods --kernels "$(uname -r)" --akmod %{name} || true
fi

# 4. Try to load the kernel module if it was built successfully
if [ -f "/lib/modules/$(uname -r)/extra/corefreqk.ko" ]; then
    /sbin/depmod -a "$(uname -r)" 2>/dev/null || true
    /sbin/modprobe corefreqk >/dev/null 2>&1 || true
fi

# 5. Start service if module is loaded
if lsmod | grep -q corefreqk; then
    systemctl start corefreqd.service >/dev/null 2>&1 || true
fi

# 6. User feedback
if systemctl is-active --quiet corefreqd.service; then
    echo "✅ CoreFreq is ready! Use: corefreq-cli -Oa -t frequency"
elif lsmod | grep -q corefreqk; then
    echo "✅ CoreFreq module loaded! Starting service..."
    echo "   Use: corefreq-cli -Oa -t frequency"
else
    echo "✅ CoreFreq installed! Module will build on next kernel update or reboot."
    echo "   Manual build: sudo akmods --akmod corefreq"
    echo "   Then use: corefreq-cli -Oa -t frequency"
fi

%preun
%systemd_preun corefreqd.service
if [ $1 -eq 0 ]; then # Final uninstall only
    systemctl stop corefreqd.service >/dev/null 2>&1 || true
    modprobe -r corefreqk >/dev/null 2>&1 || true
fi

%postun
%systemd_postun_with_restart corefreqd.service

%post -n akmod-%{name}
# Trigger akmod build
nohup %{_bindir}/akmods --from-akmod-posttrans --akmod %{name} --kernels "%{?kernel_versions}" &> /dev/null &

%preun -n akmod-%{name}
# Remove all versions of the module
if [ $1 -eq 0 ]; then # Final uninstall only
    for kver in $(find /lib/modules -name "corefreqk.ko" -exec dirname {} \; | sed 's|.*/modules/||;s|/.*||' | sort -u); do
        rm -f "/lib/modules/$kver/extra/corefreqk.ko" 2>/dev/null || true
        /sbin/depmod -a "$kver" 2>/dev/null || true
    done
fi

%files
%license LICENSE
%doc README.md
%{_bindir}/corefreq-cli
%{_bindir}/corefreqd
%{_unitdir}/corefreqd.service

%files -n akmod-%{name}
%{_usrsrc}/akmods/%{name}-%{version}-%{release}.tar.gz

%files kmod-common
# Common files for kmod packages (empty for this package)

%changelog
* Mon Sep 06 2025 - Release 8.1
- Fixed akmod source packaging path
- Improved MOK password generation
- Enhanced module loading logic
- Better error handling in post scripts
* Sat Aug 30 2025 - Release 8
- Converted from DKMS to akmod format for COPR
- NVIDIA-style full automation with akmod integration
- Auto-enrolls akmods MOK key with predictable password
- Enhanced service with akmod integration and retry logic
- Optimized for COPR build environment