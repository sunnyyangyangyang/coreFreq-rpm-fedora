%global cf_major 2
%global cf_minor 0
%global cf_rev 8

Name:           corefreq
Version:        %{cf_major}.%{cf_minor}.%{cf_rev}
Release:        1%{?dist}
Summary:        CoreFreq CPU monitor with DKMS for automatic kernel module builds
License:        GPL-2.0
URL:            https://github.com/cyring/CoreFreq

# The source tarball
Source0:        https://github.com/cyring/CoreFreq/archive/v%{version}.tar.gz#/%{name}-%{version}.tar.gz

# CORRECTED: Use ExclusiveArch instead of BuildArch for Copr compatibility.
# This declares that the source is only compatible with x86_64 without
# making the Source RPM (SRPM) arch-specific.
ExclusiveArch:  x86_64

# Dependencies needed to build the RPM itself
BuildRequires:  make
BuildRequires:  gcc

# Dependencies required on the end-user's system to install and run the RPM
Requires:       dkms
Requires:       kernel-devel
Requires:       systemd
# For Secure Boot MOK management
Requires:       mokutil
Requires:       openssl

%description
CoreFreq is a CPU monitoring software with BIOS like functionalities.
This package uses DKMS to automatically build and install the 'corefreqk'
kernel module for your current and future kernels, ensuring compatibility
across kernel updates.

# --- Prep Section ---
%prep
%autosetup -p1 -n CoreFreq-%{version}

# --- Build Section ---
# Build the user-space tools. The kernel module will be built by DKMS on the user's machine.
%build
make %{?_smp_mflags} corefreqd corefreq-cli

# --- Install Section ---
%install
# 1. Install the user-space binaries
install -d -m 755 %{buildroot}%{_bindir}
install -m 755 build/corefreqd %{buildroot}%{_bindir}/corefreqd
install -m 755 build/corefreq-cli %{buildroot}%{_bindir}/corefreq-cli

# 2. Install the systemd service file
install -d -m 755 %{buildroot}%{_unitdir}
install -m 644 corefreqd.service %{buildroot}%{_unitdir}/corefreqd.service

# 3. Install the kernel module source code for DKMS
install -d -m 755 %{buildroot}%{_usrsrc}/%{name}-%{version}
cp -r ./* %{buildroot}%{_usrsrc}/%{name}-%{version}/

# 4. Create a dkms.conf file on the fly.
cat << EOF > %{buildroot}%{_usrsrc}/%{name}-%{version}/dkms.conf
PACKAGE_NAME="corefreqk"
PACKAGE_VERSION="%{version}"
BUILT_MODULE_NAME[0]="corefreqk"
DEST_MODULE_LOCATION[0]="/extra"
MAKE[0]="make -C . KERNELDIR=/lib/modules/\${kernelver}/build"
CLEAN="make clean"
AUTOINSTALL="yes"
EOF

# --- Scriptlets ---
%post
dkms add -m %{name} -v %{version}
dkms build -m %{name} -v %{version}
dkms install -m %{name} -v %{version}

%systemd_post corefreqd.service
# Use a non-fatal start in case the module needs a MOK enrollment + reboot
systemctl start corefreqd.service >/dev/null 2>&1 || :

if [ -x /usr/bin/mokutil ] && mokutil --sb-state | grep -q "enabled"; then
    echo
    echo "----------------------------------------------------------------------"
    echo "ATTENTION: Secure Boot is enabled on your system."
    echo "For DKMS to automatically sign modules, you must create and enroll"
    echo "a personal Machine Owner Key (MOK)."
    echo
    echo "If you have NOT done this before for DKMS, please see:"
    echo "https://docs.fedoraproject.org/en-US/fedora/latest/system-administrators-guide/kernel-module-driver-configuration/Working_with_Kernel_Modules/#sect-generating-a-signing-key"
    echo "----------------------------------------------------------------------"
    echo
fi

%preun
%systemd_preun corefreqd.service

# Remove from DKMS before the files are deleted
if [ "$1" -eq 0 ] ; then # This condition means "on final uninstallation"
    dkms remove -m %{name} -v %{version} --all >/dev/null 2>&1 || :
fi

%postun
%systemd_postun_with_restart corefreqd.service

# --- Files Section ---
%files
%license LICENSE
%doc README.md
%{_bindir}/corefreqd
%{_bindir}/corefreq-cli
%{_unitdir}/corefreqd.service
%{_usrsrc}/%{name}-%{version}/