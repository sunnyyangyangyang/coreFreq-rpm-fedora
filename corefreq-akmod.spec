# CoreFreq Akmod RPM Spec - Fixed for COPR
%global _debugsource_packages 0
%global _debuginfo_packages 0
%global debug_package %{nil}

%global corefreq_version 2.0.8

Name:           corefreq
Version:        %{corefreq_version}
Release:        1.alpha24%{?dist}
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
BuildRequires:  gcc make rpm-build
BuildRequires:  systemd-rpm-macros
BuildRequires:  kernel-devel

# Runtime Requirements
Requires:       systemd
Suggests:       mokutil
Requires:       %{name}-kmod >= %{version}

# Generate akmod metadata
%{expand:%(kmodtool --target %{_target_cpu} --kmodname %{name} --pattern ".*" --akmod 2>/dev/null) }

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
# Keep a copy of the original Makefile
cp Makefile Makefile.orig
# Use our akmod-compatible Makefile
cp %{SOURCE2} Makefile

%build
# Build userspace tools only (kernel module is built later by akmod)
make %{?_smp_mflags} userspace

%install
# --- Install userspace components ---
install -D -m 0755 build/corefreqd %{buildroot}%{_bindir}/corefreqd
install -D -m 0755 build/corefreq-cli %{buildroot}%{_bindir}/corefreq-cli
install -D -m 0644 %{SOURCE1} %{buildroot}%{_unitdir}/corefreqd.service

# --- Create and install the kmod SRPM for akmods ---
install -d %{buildroot}%{_usrsrc}/akmods/

# 1. Create a temporary build environment for the SRPM
SRPM_TOPDIR=$(mktemp -d)
mkdir -p "$SRPM_TOPDIR"/{SOURCES,SPECS}

# 2. Prepare the inner spec file by substituting variables
sed -e 's|@COREFREQ_VERSION@|%{corefreq_version}|g' \
    -e 's|@RELEASE@|1%{?dist}|g' \
    %{SOURCE3} > "$SRPM_TOPDIR"/SPECS/corefreq-kmod.spec

# 3. Create the source tarball that the inner spec expects
#    The inner spec's Source0 will be 'corefreq-kmod-%{version}.tar.gz'
#    It must contain the full source tree.
tar -czf "$SRPM_TOPDIR"/SOURCES/corefreq-kmod-%{version}.tar.gz \
    --transform "s|^CoreFreq-%{version}|corefreq-kmod-%{version}|" \
    -C %{_builddir} \
    CoreFreq-%{version}

# 4. Build the Source RPM (.src.rpm)
rpmbuild -bs \
  --define "_topdir $SRPM_TOPDIR" \
  "$SRPM_TOPDIR"/SPECS/corefreq-kmod.spec

# 5. Install the SRPM where akmods expects to find it
install -m 0644 "$SRPM_TOPDIR"/SRPMS/*.src.rpm %{buildroot}%{_usrsrc}/akmods/

# 6. Create the 'latest' symlink pointing to the new SRPM
#    Find the actual SRPM filename to create the symlink
SRPM_NAME=$(basename "$SRPM_TOPDIR"/SRPMS/*.src.rpm)
ln -s "$SRPM_NAME" %{buildroot}%{_usrsrc}/akmods/%{name}-kmod.latest

# 7. Clean up the temporary directory
rm -rf "$SRPM_TOPDIR"


%post
# === AUTOMATED AKMOD + MOK SETUP ===
# (scriptlets remain unchanged)
# Function to generate secure password
generate_mok_password() {
    if command -v openssl >/dev/null 2>&1; then
        openssl rand -hex 12 2>/dev/null
    else
        printf "%012x" $((RANDOM * RANDOM * RANDOM)) 2>/dev/null
    fi
}
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
echo "   Once running, use: corefreq-cli"
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
        rm -rf "/lib/modules/$kver/extra/corefreq" "/lib/modules/$kver/updates/corefreqk.ko" 2>/dev/null || true
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
# Package the SRPM and the symlink
%{_usrsrc}/akmods/corefreq-kmod-%{version}-*.src.rpm
%{_usrsrc}/akmods/corefreq-kmod.latest

%files kmod-common
# This package is empty but serves as a dependency anchor

%changelog
* Sun Sep 08 2025 Package Maintainer <package@example.com> - 2.0.8-1.alpha20
- Switched to building an SRPM for akmods instead of a tarball
- Corrected akmodsbuild usage which expects a .src.rpm file
- Reworked %install section to use rpmbuild -bs for kmod source
- Updated %files section for akmod subpackage to include the SRPM
- This should resolve the "cannot be installed" error

* Sun Sep 08 2025 Package Maintainer <package@example.com> - 2.0.8-1.alpha19
- Fixed akmod inner spec file with working build and install sections
- Added proper %files section to prevent unpackaged files error
- Corrected directory structure handling for rpmbuild
- Successfully tested kernel module build process