# === AKMOD SPEC FILE ===

%global _debugsource_packages 0
%global _debuginfo_packages 0
%global debug_package %{nil}

%global corefreq_version 2.0.8
%global buildforkernels akmod
%global debug 0

Name:           corefreq
Version:        %{corefreq_version}
Release:        1.alpha2%{?dist}
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
BuildRequires:  kernel-devel
Requires:    %{name}%{?_isa} = %{version}-%{release}

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

# Replace original complex Makefile with akmod-compatible version
cp %{SOURCE2} Makefile

# Copy sources to akmod builddir
for kernel_version in %{?kernel_versions}; do
    mkdir -p _kmod_build_${kernel_version%%___*}
    cp -a . _kmod_build_${kernel_version%%___*}/
    pushd _kmod_build_${kernel_version%%___*}
    # Ensure akmod-compatible Makefile is used
    cp %{SOURCE2} Makefile
    popd
done

%build
# Build userspace tools
make %{?_smp_mflags} userspace

# Build kernel modules for akmod
for kernel_version in %{?kernel_versions}; do
    pushd _kmod_build_${kernel_version%%___*}
    make %{?_smp_mflags} KERNELDIR=${kernel_version##*___} all
    popd
done

%install
# Install userspace tools
install -D -m 0755 build/corefreqd %{buildroot}%{_bindir}/corefreqd
install -D -m 0755 build/corefreq-cli %{buildroot}%{_bindir}/corefreq-cli
install -D -m 0644 %{SOURCE1} %{buildroot}%{_unitdir}/corefreqd.service

# Install kernel modules
for kernel_version in %{?kernel_versions}; do
    pushd _kmod_build_${kernel_version%%___*}
    install -D -m 0755 build/corefreqk.ko %{buildroot}%{kmodinstdir_prefix}${kernel_version%%___*}%{kmodinstdir_postfix}/corefreqk.ko
    popd
done

# Install akmod sources
install -d %{buildroot}%{_usrsrc}/akmods/
cp -a . %{buildroot}%{_usrsrc}/akmods/%{name}-%{version}
rm -rf %{buildroot}%{_usrsrc}/akmods/%{name}-%{version}/_kmod_build_*
rm -rf %{buildroot}%{_usrsrc}/akmods/%{name}-%{version}/build

%post
# === AUTOMATED DKMS + MOK SETUP (adapted for akmod) ===

# 1. Auto-enroll MOK key for Secure Boot (user can decline during reboot)
if [ -f /etc/pki/akmods/certs/public_key.der ] && command -v mokutil >/dev/null 2>&1; then
    if ! mokutil --list-enrolled 2>/dev/null | grep -q "akmods"; then
        # Generate random password and auto-queue the key
        MOK_PASSWORD=$(printf "%08d" $((RANDOM * RANDOM % 100000000)))
        echo "--- Queueing akmods MOK key for Secure Boot enrollment ---"
        echo -e "$MOK_PASSWORD\n$MOK_PASSWORD" | mokutil --import /etc/pki/akmods/certs/public_key.der 2>/dev/null || true

        echo "------------------------------------------------------------------"
        echo "ATTENTION: SECURE BOOT - MOK KEY ENROLLMENT REQUIRED"
        echo "The akmods signing key has been queued for enrollment."
        echo "Your temporary MOK password is: $MOK_PASSWORD"
        echo
        echo "To complete the setup:"
        echo "1. Reboot your computer."
        echo "2. At the blue 'MOK Manager' screen that appears on boot,"
        echo "   select 'Enroll MOK' and follow the prompts."
        echo "3. Enter the password shown above: $MOK_PASSWORD"
        echo
        echo "After the reboot, the module will load automatically for all"
        echo "future kernel updates."
        echo "------------------------------------------------------------------"
    fi
fi

# 2. Try to load the kernel module if it exists for current kernel
if [ -f "/lib/modules/$(uname -r)/extra/corefreqk.ko" ] || [ -f "/lib/modules/$(uname -r)/updates/corefreqk.ko" ]; then
    /sbin/modprobe corefreqk >/dev/null 2>&1 || true
fi

# 3. Enable and start service
%systemd_post corefreqd.service
systemctl enable corefreqd.service >/dev/null 2>&1 || true
systemctl start corefreqd.service >/dev/null 2>&1 || true

# 4. User feedback
if systemctl is-active --quiet corefreqd.service; then
    echo "✅ CoreFreq is ready! Use: corefreq-cli -Oa -t frequency"
elif lsmod | grep -q corefreqk; then
    echo "✅ CoreFreq module loaded! Service will start automatically."
    echo "   Use: corefreq-cli -Oa -t frequency"
else
    echo "✅ CoreFreq installed! After reboot (if Secure Boot), use: corefreq-cli -Oa -t frequency"
    echo "   Or manually load with: sudo modprobe corefreqk && sudo systemctl start corefreqd"
fi

%preun
%systemd_preun corefreqd.service
if [ $1 -eq 0 ]; then # Final uninstall only
    # Stop service and unload module
    systemctl stop corefreqd.service >/dev/null 2>&1 || true
    modprobe -r corefreqk >/dev/null 2>&1 || true
fi

%postun
%systemd_postun_with_restart corefreqd.service

%post -n akmod-%{name}
nohup %{_bindir}/akmods --from-akmod-posttrans --akmod %{name} --kernels %{kernel_versions} &> /dev/null &

%preun -n akmod-%{name}
# Remove all versions of the module
for kver in $(rpm -q --qf '%%{version}-%%{release}.%%{arch}\n' kernel kernel-devel 2>/dev/null | sort -u); do
    if [ -d "/lib/modules/$kver/extra" ]; then
        rm -f "/lib/modules/$kver/extra/corefreqk.ko" 2>/dev/null || true
        /sbin/depmod -a "$kver" 2>/dev/null || true
    fi
done

%files
%license LICENSE
%doc README.md
%{_bindir}/corefreq-cli
%{_bindir}/corefreqd
%{_unitdir}/corefreqd.service

%files -n akmod-%{name}
%{_usrsrc}/akmods/%{name}-%{version}

%files kmod-common
# This is for files shared between kmod packages
# Usually empty for simple kernel modules

%changelog
* Sat Aug 30 2025 - Release 8
- Converted from DKMS to akmod format for COPR
- NVIDIA-style full automation with akmod integration
- Auto-enrolls akmods MOK key with predictable password
- Enhanced service with akmod integration and retry logic
- Optimized for COPR build environment