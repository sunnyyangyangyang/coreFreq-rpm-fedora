# CoreFreq Akmod RPM Spec - NVIDIA-style approach
%global _debugsource_packages 0
%global _debuginfo_packages 0
%global debug_package %{nil}
%global _dracut_conf_d /usr/lib/dracut/dracut.conf.d
%global corefreq_version 2.0.9

Name:           corefreq
Version:        %{corefreq_version}
Release:        27.beta5%{?dist}
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
Requires:       %{name}-kmod = %{?epoch:%{epoch}:}%{version}-%{release}
Requires:       %{name}-kmod-common = %{?epoch:%{epoch}:}%{version}-%{release}

# Generate akmod metadata
%{expand:%(kmodtool --target %{_target_cpu} --kmodname %{name} --pattern ".*" --akmod 2>/dev/null) }

%description
CoreFreq is a CPU monitoring software designed for 64-bit Processors.
This package provides the user-space tools and the akmod source for the
'corefreqk' kernel module with full automation including Secure Boot support.

IMPORTANT: After installation, a REBOOT is required for the kernel module
to be compiled and loaded automatically.

%package -n akmod-%{name}
Summary:        Akmod package for %{name} kernel module(s)
Requires:       kmodtool
Requires:       akmods
Provides:       %{name}-kmod = %{?epoch:%{epoch}:}%{version}-%{release}
Requires:       %{name}-kmod-common = %{?epoch:%{epoch}:}%{version}-%{release}

%description -n akmod-%{name}
This package provides the akmod package for the %{name} kernel modules.

%package kmod-common
Summary:        Common files for %{name} kernel module
Requires:       %{name} = %{?epoch:%{epoch}:}%{version}-%{release}
Provides:       %{name}-kmod-common = %{?epoch:%{epoch}:}%{version}-%{release}

%description kmod-common
This package provides the common files for the %{name} kernel modules.

%prep
%autosetup -n CoreFreq-%{version} -p1
cp Makefile Makefile.orig
cp %{SOURCE2} Makefile

%build
make %{?_smp_mflags} userspace

%install
# --- Install userspace components ---
install -D -m 0755 build/corefreqd %{buildroot}%{_bindir}/corefreqd
install -D -m 0755 build/corefreq-cli %{buildroot}%{_bindir}/corefreq-cli
install -D -m 0644 %{SOURCE1} %{buildroot}%{_unitdir}/corefreqd.service

# --- Create and install the kmod SRPM for akmods ---
install -d %{buildroot}%{_usrsrc}/akmods/

SRPM_TOPDIR=$(mktemp -d)
mkdir -p "$SRPM_TOPDIR"/{SOURCES,SPECS}

sed -e 's|@COREFREQ_VERSION@|%{corefreq_version}|g' \
    -e 's|@RELEASE@|%{release}|g' \
    %{SOURCE3} > "$SRPM_TOPDIR"/SPECS/corefreq-kmod.spec

tar -czf "$SRPM_TOPDIR"/SOURCES/corefreq-kmod-%{version}.tar.gz \
    --transform "s|^CoreFreq-%{version}|corefreq-kmod-%{version}|" \
    -C %{_builddir} \
    CoreFreq-%{version}

rpmbuild -bs \
  --define "_topdir $SRPM_TOPDIR" \
  "$SRPM_TOPDIR"/SPECS/corefreq-kmod.spec

install -m 0644 "$SRPM_TOPDIR"/SRPMS/*.src.rpm %{buildroot}%{_usrsrc}/akmods/

SRPM_NAME=$(basename "$SRPM_TOPDIR"/SRPMS/*.src.rpm)
ln -s "$SRPM_NAME" %{buildroot}%{_usrsrc}/akmods/%{name}-kmod.latest

rm -rf "$SRPM_TOPDIR"

# --- Dracut configuration ---
install -d -m 0755 %{buildroot}%{_dracut_conf_d}
cat > %{buildroot}%{_dracut_conf_d}/99-corefreq.conf << EOF
# Do not include the corefreqk module in the initramfs.
omit_drivers+=" corefreqk "
EOF

%post
# Generate akmods signing key if it doesn't exist
# This uses the official kmodgenca tool from akmods package
if [ ! -f /etc/pki/akmods/certs/public_key.der ]; then
    echo "Generating akmods signing keys..."
    /usr/sbin/kmodgenca -a 2>/dev/null || true
fi

# === SMART MOK DETECTION ===
smart_mok_check() {
    local akmods_key="/etc/pki/akmods/certs/public_key.der"
    
    # Early exit: Not a UEFI system
    if [ ! -d /sys/firmware/efi/efivars ]; then
        return 0
    fi
    
    # Early exit: mokutil not available
    if ! command -v mokutil >/dev/null 2>&1; then
        return 0
    fi
    
    # Check if Secure Boot is enabled
    local sb_state
    sb_state=$(mokutil --sb-state 2>/dev/null)
    
    if ! echo "$sb_state" | grep -q "SecureBoot enabled"; then
        return 0
    fi
    
    # At this point: UEFI + Secure Boot enabled
    
    # Key should exist now (we just generated it)
    if [ ! -f "$akmods_key" ]; then
        cat << 'EOF'

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚠️  SECURE BOOT WARNING
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Failed to generate akmods key. After reboot, run:
  sudo mokutil --import /etc/pki/akmods/certs/public_key.der
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

EOF
        return 1
    fi
    
    # Check if key is already enrolled
    if mokutil --list-enrolled 2>/dev/null | grep -q "CN=akmods" || \
       mokutil --test-key "$akmods_key" 2>&1 | grep -qi "already.*enrolled"; then
        return 0
    fi
    
    # Key exists but NOT enrolled - show instructions
    cat << 'EOF'

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🔐 SECURE BOOT DETECTED - ACTION REQUIRED
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
To use CoreFreq with Secure Boot, enroll the MOK key NOW (before reboot):

  sudo mokutil --import /etc/pki/akmods/certs/public_key.der

You'll be asked to create a password. Remember it for the next reboot.

After rebooting:
  1. MOK Manager will appear
  2. Select "Enroll MOK"
  3. Enter the password you just created
  4. Reboot again

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

EOF
}

smart_mok_check

# Register service with systemd
%systemd_post corefreqd.service
systemctl enable corefreqd.service >/dev/null 2>&1 || true

cat << 'EOF'

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ CoreFreq Installation Complete
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

⚠️  REBOOT REQUIRED

The kernel module will be compiled during the next boot.
After rebooting, CoreFreq will start automatically.

To use CoreFreq after reboot:
  corefreq-cli

To check service status:
  systemctl status corefreqd.service

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

EOF

%preun
# Stop service before uninstall/upgrade
%systemd_preun corefreqd.service

if [ $1 -eq 0 ]; then
    # Complete uninstall: try to remove the kernel module
    # (May fail if in use - that's OK, reboot will clear it)
    /sbin/modprobe -r corefreqk >/dev/null 2>&1 || true
fi

%postun
%systemd_postun corefreqd.service

if [ $1 -ne 0 ]; then
    # Upgrade scenario: show message
    cat << 'EOF'

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ CoreFreq Upgraded
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

⚠️  REBOOT REQUIRED

The kernel module needs to be recompiled for the new version.
Please reboot your system to complete the upgrade.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

EOF
fi

%files
%license LICENSE
%doc README.md
%{_bindir}/corefreq-cli
%{_bindir}/corefreqd
%{_unitdir}/corefreqd.service
%{_dracut_conf_d}/99-corefreq.conf

%files -n akmod-%{name}
%{_usrsrc}/akmods/corefreq-kmod-%{version}-*.src.rpm
%{_usrsrc}/akmods/corefreq-kmod.latest

%files kmod-common
# Empty dependency anchor package

%changelog
* Fri Dec 06 2025 Package Maintainer <package@example.com> - 2.0.9-29
- Clean up %preun: remove redundant systemctl stop and sleep loop
- Trust systemd's synchronous stop behavior
- Maintain consistent upgrade behavior without service restart

* Wed Nov 12 2025 github-actions[bot] <41898282+github-actions[bot]@users.noreply.github.com> - 2.0.9-1
- Update to upstream version 2.0.9

* Sun Nov 09 2025 Package Maintainer <package@example.com> - 2.0.8-26
- Adopt NVIDIA-style approach: reboot required after installation
- Remove all attempts to start service immediately after install
- Simplified installation flow for better reliability
- Service will start automatically on next boot after module compilation