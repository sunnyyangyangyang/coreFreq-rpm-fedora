# CoreFreq Akmod RPM Spec - Fixed for COPR
%global _debugsource_packages 0
%global _debuginfo_packages 0
%global debug_package %{nil}

%global corefreq_version 2.0.8
%global buildforkernels akmod
%global debug 0

Name:           corefreq
Version:        %{corefreq_version}
Release:        1.alpha17%{?dist}
Summary:        CPU monitoring software with akmod kernel module

License:        GPL-2.0-only
URL:            https://github.com/cyring/CoreFreq
Source0:        %{url}/archive/refs/tags/%{version}.tar.gz#/%{name}-%{version}.tar.gz
Source1:        corefreqd.service
Source2:        Makefile.akmod
Source3:        corefreq-kmod.spec.in

# Akmod BuildRequires
BuildRequires:  kmodtool
BuildRequires:  akmods
BuildRequires:  gcc make
BuildRequires:  systemd-rpm-macros
BuildRequires:  kernel-devel

# Runtime Requirements
Requires:       systemd
Suggests:       mokutil
Requires:       %{name}-kmod >= %{version}

# Generate akmod metadata
%{expand:%(kmodtool --target %{_target_cpu} --kmodname %{name} --pattern ".*" %{?buildforkernels:--%{buildforkernels}} %{?kernels:--for-kernels "%{?kernels}"} 2>/dev/null) }

%description
CoreFreq is a CPU monitoring software designed for 64-bit Processors.
This package provides the user-space tools and the akmod source for the
'corefreqk' kernel module with full automation including Secure Boot support.

%package -n akmod-%{name}
Summary:        Akmod package for %{name} kernel module(s)
Requires:       kmodtool
Requires:       akmods
Provides:       %{name}-kmod = %{?epoch:%{epoch}:}%{version}-%{release}
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
cp %{SOURCE2} Makefile

# Process the kmod spec template - replace variables
sed -e 's|@COREFREQ_VERSION@|%{corefreq_version}|g' \
    -e 's|@VERSION@|%{version}|g' \
    -e 's|@RELEASE@|%{release}|g' \
    %{SOURCE3} > corefreq-kmod.spec

%build
# Build userspace tools only (kernel module built by akmod)
make %{?_smp_mflags} userspace

%install
# Install userspace binaries
install -D -m 0755 build/corefreqd %{buildroot}%{_bindir}/corefreqd
install -D -m 0755 build/corefreq-cli %{buildroot}%{_bindir}/corefreq-cli

# Install systemd service
install -D -m 0644 %{SOURCE1} %{buildroot}%{_unitdir}/corefreqd.service

# Create akmod source package with proper structure
mkdir -p %{buildroot}%{_usrsrc}/akmods/

# Create a temporary directory for packaging
AKMOD_TEMP=$(mktemp -d)
AKMOD_SOURCE="$AKMOD_TEMP/corefreq-kmod-%{version}"

# Copy source tree
cp -r %{_builddir}/CoreFreq-%{version} "$AKMOD_SOURCE"

# Add the processed spec file and Makefile to the source tree
cp corefreq-kmod.spec "$AKMOD_SOURCE/"
cp %{SOURCE2} "$AKMOD_SOURCE/Makefile.akmod"

# Create the tarball with the correct structure
tar -czf %{buildroot}%{_usrsrc}/akmods/%{name}-kmod-%{version}.tar.gz \
    -C "$AKMOD_TEMP" \
    --exclude-vcs \
    --exclude='build/*' \
    --exclude='*.o' \
    --exclude='*.ko' \
    corefreq-kmod-%{version}

# Create the latest symlink
ln -s %{name}-kmod-%{version}.tar.gz %{buildroot}%{_usrsrc}/akmods/%{name}-kmod.latest

# Cleanup
rm -rf "$AKMOD_TEMP"

%check
# Basic validation of built binaries
if ! %{buildroot}%{_bindir}/corefreqd -h >/dev/null 2>&1; then
    echo "WARNING: corefreqd help test failed (may need privileged access)"
fi
if ! %{buildroot}%{_bindir}/corefreq-cli -h >/dev/null 2>&1; then
    echo "WARNING: corefreq-cli help test failed (may need privileged access)"
fi

%post
# === AUTOMATED AKMOD + MOK SETUP ===

# Function to generate secure password
generate_mok_password() {
    if command -v openssl >/dev/null 2>&1; then
        openssl rand -hex 12 2>/dev/null
    else
        printf "%012x" $((RANDOM * RANDOM * RANDOM)) 2>/dev/null
    fi
}

# 1. Auto-enroll MOK key for Secure Boot (only if needed)
if [ -f /etc/pki/akmods/certs/public_key.der ] && command -v mokutil >/dev/null 2>&1; then
    if ! mokutil --list-enrolled 2>/dev/null | grep -q "CN=akmods"; then
        MOK_PASSWORD=$(generate_mok_password)
        if [ -n "$MOK_PASSWORD" ]; then
            echo "--- Queueing akmods MOK key for Secure Boot enrollment ---"
            if echo -e "$MOK_PASSWORD\n$MOK_PASSWORD" | mokutil --import /etc/pki/akmods/certs/public_key.der 2>/dev/null; then
                cat << EOF
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🔐 SECURE BOOT - MOK KEY ENROLLMENT REQUIRED
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
The akmods signing key has been queued for enrollment.
Your MOK password is: $MOK_PASSWORD

To complete setup:
1. REBOOT your computer
2. At the blue 'MOK Manager' screen during boot:
   → Select 'Enroll MOK'
   → Enter password: $MOK_PASSWORD
   → Confirm enrollment

After reboot, CoreFreq will work automatically with all kernel updates.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
EOF
            fi
        fi
    fi
fi

# 2. Enable systemd service
%systemd_post corefreqd.service
systemctl enable corefreqd.service >/dev/null 2>&1 || true

echo ""
echo "✅ CoreFreq installed!"
echo "   The kernel module will be built automatically in the background."
echo "   The service will start once the module is ready."
echo ""
if [ -f /sys/firmware/efi/efivars/SecureBoot-* ] && [ "$(cat /sys/firmware/efi/efivars/SecureBoot-* 2>/dev/null | tail -c 1 | od -An -tu1)" = " 1" ]; then
    echo "🔐 Secure Boot is enabled. If you see MOK enrollment messages,"
    echo "   please reboot and follow the on-screen instructions."
fi
echo ""
echo "   To check status: systemctl status corefreqd.service"
echo "   Once running, use: corefreq-cli -t"
echo ""

%preun
%systemd_preun corefreqd.service
if [ $1 -eq 0 ]; then # Final uninstall only
    systemctl stop corefreqd.service >/dev/null 2>&1 || true
    /sbin/modprobe -r corefreqk >/dev/null 2>&1 || true
fi

%postun
%systemd_postun_with_restart corefreqd.service

%post -n akmod-%{name}
# Trigger akmod build
nohup %{_bindir}/akmods --from-akmod-posttrans --akmod %{name} --kernels "%{?kernel_versions}" &> /dev/null &

%preun -n akmod-%{name}
# Remove all versions of the module
if [ $1 -eq 0 ]; then # Final uninstall only
    for kver in $(find /lib/modules -name "corefreqk.ko" -exec dirname {} \; 2>/dev/null | sed 's|.*/modules/||;s|/.*||' | sort -u); do
        rm -f "/lib/modules/$kver/extra/corefreqk.ko" "/lib/modules/$kver/updates/corefreqk.ko" 2>/dev/null || true
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
%{_usrsrc}/akmods/%{name}-kmod-%{version}.tar.gz
%{_usrsrc}/akmods/%{name}-kmod.latest

%files kmod-common
# Common files for kmod packages (empty for this package)

%changelog
* Sun Sep 08 2025 Package Maintainer <package@example.com> - 2.0.8-1.alpha16
- Fixed akmod source packaging structure
- Process kmod spec template variables during build
- Ensure proper directory structure in akmod tarball
- Fixed source file placement for akmod system

* Sun Sep 01 2025 Package Maintainer <package@example.com> - 2.0.8-1.alpha15
- Fix akmod build trigger by moving it to the akmod subpackage post-install scriptlet
- Remove premature build attempt from main package post-install scriptlet
- Adjust user feedback messages for accuracy during installation
- Add explicit 'Requires: corefreq-kmod' to main package for dependency clarity