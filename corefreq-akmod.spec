# CoreFreq Akmod RPM Spec - Fixed for COPR
%global _debugsource_packages 0
%global _debuginfo_packages 0
%global debug_package %{nil}

%global corefreq_version 2.0.8

Name:           corefreq
Version:        %{corefreq_version}
Release:        1.beta6%{?dist}
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
# === SMART MOK DETECTION AND SETUP ===
smart_mok_check() {
    local akmods_key="/etc/pki/akmods/certs/public_key.der"
    local pending_keys="/var/lib/mokutil/request"
    local secure_boot_enabled=false
    
    # Check if Secure Boot is enabled
    if [ -d /sys/firmware/efi/efivars ]; then
        if mokutil --sb-state 2>/dev/null | grep -q "SecureBoot enabled"; then
            secure_boot_enabled=true
        fi
    fi
    
    # Only proceed if Secure Boot is enabled
    if [ "$secure_boot_enabled" = "false" ]; then
        return 0
    fi
    
    # Check if akmods key exists
    if [ ! -f "$akmods_key" ]; then
        echo "Warning: akmods signing key not found. Module signing may fail."
        return 1
    fi
    
    # Check if key is already enrolled (multiple ways to detect this)
    if mokutil --list-enrolled 2>/dev/null | grep -q "CN=akmods" || \
       mokutil --test-key "$akmods_key" 2>&1 | grep -q "already enrolled\|SKIP.*already enrolled"; then
        echo "akmods MOK key already enrolled."
        return 0
    fi
    
    # Check if there are pending MOK requests
    if [ -d "$pending_keys" ] && [ -n "$(ls -A "$pending_keys" 2>/dev/null)" ]; then
        cat << 'EOF'
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🔐 MOK KEY ENROLLMENT PENDING
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
You have pending MOK (Machine Owner Key) enrollments.

To complete enrollment:
1. REBOOT your computer
2. At the blue 'MOK Manager' screen during boot:
   → Select 'Enroll MOK'
   → Enter the password you provided
   → Confirm enrollment

If you need to enroll the akmods key manually:
  sudo mokutil --import /etc/pki/akmods/certs/public_key.der
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
EOF
        return 0
    fi
    
    # If no pending requests and key not enrolled, show manual enrollment
    cat << 'EOF'
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🔐 SECURE BOOT DETECTED - MOK ENROLLMENT REQUIRED
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
To use CoreFreq with Secure Boot, enroll the akmods signing key:

  sudo mokutil --import /etc/pki/akmods/certs/public_key.der

Then REBOOT and follow the on-screen MOK Manager instructions.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
EOF
}

# Run smart MOK check
smart_mok_check

%systemd_post corefreqd.service
systemctl enable corefreqd.service >/dev/null 2>&1 || true
echo ""
echo "CoreFreq installed successfully!"
echo "The kernel module has been compiled."
echo "Attempting to start the CoreFreq service..."

# Since the akmod build is now synchronous, the module exists. Start the service.
# 'try-restart' is safe and will not fail the entire installation if the service fails to start.
systemctl try-restart corefreqd.service >/dev/null 2>&1 || :

echo ""
echo "To check status: systemctl status corefreqd.service"
echo "Once running, use: corefreq-cli"
echo ""

%preun
%systemd_preun corefreqd.service
if [ $1 -eq 0 ]; then # Final uninstall only
    systemctl stop corefreqd.service >/dev/null 2>&1 || true
    for i in {1..5}; do
        if /sbin/modprobe -r corefreqk >/dev/null 2>&1; then
            break 
        fi
        sleep 1
    done
fi

%postun
%systemd_postun_with_restart corefreqd.service

# === KERNEL UPDATE TRIGGERS FOR AUTOMATIC REBUILDS ===
%triggerin -- kernel kernel-core kernel-devel kernel-modules kernel-modules-core
echo "Kernel update detected, rebuilding CoreFreq module..."
if [ -x /usr/bin/akmods ]; then
    # Run in background to avoid blocking the transaction
    nohup sh -c 'sleep 5; /usr/bin/akmods --akmod %{name} --force' >/dev/null 2>&1 &
fi

%triggerpostun -- kernel kernel-core kernel-devel kernel-modules kernel-modules-core
echo "Kernel removal detected, cleaning up CoreFreq modules..."
if [ -x /usr/bin/akmods ]; then
    # Clean up modules for removed kernels
    /usr/bin/akmods --remove %{name} >/dev/null 2>&1 || true
fi

%post -n akmod-%{name}
# Synchronously build the kernel module to ensure it's ready immediately.
# This will make the DNF/RPM transaction wait for the build to complete.
echo "Compiling the CoreFreq kernel module for the current kernel..."
echo "This may take a few minutes, please be patient."
if ! %{_bindir}/akmods --from-akmod-posttrans --akmod %{name} --kernels "$(uname -r)"; then
    echo "ERROR: akmods build failed! The service will not be started."
    echo "Please check the build logs in /var/cache/akmods/ for details."
    exit 1
fi
echo "Kernel module compilation complete."

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
* Sat Sep 07 2025 Package Maintainer <package@example.com> - 2.0.8-1.alpha28
- Added kernel update triggers for automatic module rebuilds
- Improved MOK detection logic - checks actual enrollment status and pending requests
- Removed automatic password generation and MOK enrollment
- Now provides clear manual instructions for MOK enrollment when needed
- Added triggers for kernel-modules and kernel-modules-core packages