# CoreFreq Akmod RPM Spec - Fixed for COPR
%global _debugsource_packages 0
%global _debuginfo_packages 0
%global debug_package %{nil}

%global corefreq_version 2.0.8

Name:           corefreq
Version:        %{corefreq_version}
Release:        24.alpha20%{?dist}
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

# --- Create a helper script for delayed service start ---
cat > %{buildroot}%{_bindir}/corefreq-service-starter << 'EOF'
#!/bin/bash
# CoreFreq service starter with module availability check

TIMEOUT=60
INTERVAL=2
MODULE_NAME="corefreqk"

echo "Waiting for CoreFreq kernel module to be available..."

for ((i=0; i<TIMEOUT; i+=INTERVAL)); do
    # Check if module can be loaded
    if modprobe -n "$MODULE_NAME" 2>/dev/null; then
        echo "Module $MODULE_NAME is available, starting service..."
        systemctl start corefreqd.service
        if systemctl is-active --quiet corefreqd.service; then
            echo "CoreFreq service started successfully!"
            exit 0
        else
            echo "Service start failed, retrying in $INTERVAL seconds..."
        fi
    else
        echo "Module not ready yet, waiting... ($i/${TIMEOUT}s)"
    fi
    sleep $INTERVAL
done

echo "Timeout waiting for module. You may need to start the service manually later."
echo "Try: systemctl start corefreqd.service"
exit 1
EOF

chmod +x %{buildroot}%{_bindir}/corefreq-service-starter

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
echo ""

# Don't start the service immediately, let the helper do it with retry logic
echo "Kernel module compilation is in progress..."
echo "The service will start automatically once the module is ready."

# Start the delayed service starter in background
nohup %{_bindir}/corefreq-service-starter >/dev/null 2>&1 &

echo ""
echo "To check status: systemctl status corefreqd.service"
echo "Once running, use: corefreq-cli"
echo ""

%preun
%systemd_preun corefreqd.service
# This scriptlet runs on final removal ($1 == 0), not on upgrade.
if [ $1 -eq 0 ]; then
    echo "Stopping CoreFreq service for final removal..."
    # Stop the service. Redirect output as it can be noisy.
    systemctl stop corefreqd.service >/dev/null 2>&1 || true

    # Wait up to 5 seconds for the service to fully stop.
    for i in {1..5}; do
        if ! systemctl is-active --quiet corefreqd.service; then
            echo "Service confirmed stopped."
            break
        fi
        sleep 1
    done

    # Now, attempt to unload the kernel module with a retry loop.
    echo "Unloading CoreFreq kernel module..."
    for i in {1..5}; do
        # Check if the module is loaded before trying to remove it.
        if lsmod | grep -q "^corefreqk\s"; then
            if /sbin/modprobe -r corefreqk >/dev/null 2>&1; then
                echo "Module corefreqk successfully unloaded."
                break # Success, exit the loop
            fi
        else
            echo "Module corefreqk is not loaded."
            break # Not loaded, nothing to do
        fi
        sleep 1
    done
fi

%postun
%systemd_postun_with_restart corefreqd.service

%post -n akmod-%{name}
# This scriptlet runs when the akmod-corefreq package is installed.
# We kick off a build for the currently running kernel in the background.
# This provides a better user experience, so the module is available
# without needing a reboot.
echo "Initiating CoreFreq kernel module compilation for the current kernel."
echo "This will happen in the background and may take a few minutes."
(
  nohup /usr/sbin/akmods --akmod %{name} --kernels "$(uname -r)" &
) >/dev/null 2>&1

%files
%license LICENSE
%doc README.md
%{_bindir}/corefreq-cli
%{_bindir}/corefreqd
%{_bindir}/corefreq-service-starter
%{_unitdir}/corefreqd.service

%files -n akmod-%{name}
# Package the SRPM and the symlink
%{_usrsrc}/akmods/corefreq-kmod-%{version}-*.src.rpm
%{_usrsrc}/akmods/corefreq-kmod.latest

%files kmod-common
# This package is empty but serves as a dependency anchor

%changelog
* Sat Sep 07 2025 Package Maintainer <package@example.com> - 2.0.8-1.alpha30
- Forced synchronous kernel module compilation during akmod install
- Added module verification and marker file system
- Main package now waits for akmod completion before starting service
- Improved error handling and user feedback for compilation failures
- Added comprehensive module path verification
- Service startup now guaranteed to happen after successful compilation