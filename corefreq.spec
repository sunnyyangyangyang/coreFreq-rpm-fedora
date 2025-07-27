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

# We build for a specific architecture because we are including compiled user-space tools.
BuildArch:      x86_64

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
# Unpack the source code.
%prep
%autosetup -p1 -n CoreFreq-%{version}

# --- Build Section ---
# Here we only build the user-space tools. The kernel module will be built by DKMS
# on the user's machine.
%build
make %{?_smp_mflags} corefreqd corefreq-cli

# --- Install Section ---
# This section places all necessary files into the buildroot.
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
# Copy the entire source tree
cp -r ./* %{buildroot}%{_usrsrc}/%{name}-%{version}/

# 4. Create a dkms.conf file on the fly. This is cleaner than patching the original.
#    This tells DKMS how to build the module.
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
# These scripts run on the user's machine during installation/uninstallation.

%post
# This script runs after the package is installed.

# 1. Add the module to DKMS, which will trigger the first build and install.
echo "Adding CoreFreq to DKMS..."
dkms add -m %{name} -v %{version}
echo "Building CoreFreq module for kernel $(uname -r)..."
dkms build -m %{name} -v %{version}
echo "Installing CoreFreq module..."
dkms install -m %{name} -v %{version}

# 2. Enable and start the systemd service.
echo "Reloading systemd and starting service..."
%systemd_post corefreqd.service
systemctl start corefreqd.service >/dev/null 2>&1 || :

# 3. Handle Secure Boot. This is the standard, secure way for DKMS.
#    We instruct the user to create their own key for DKMS to use.
if [ -x /usr/bin/mokutil ] && mokutil --sb-state | grep -q "enabled"; then
    echo
    echo "----------------------------------------------------------------------"
    echo "ATTENTION: Secure Boot is enabled on your system."
    echo
    echo "For DKMS to automatically sign the CoreFreq module, you must create"
    echo "a personal Machine Owner Key (MOK) and enroll it."
    echo
    echo "If you have NOT done this before, please perform the following steps:"
    echo "1. Create a key for DKMS to use:"
    echo "   sudo /usr/sbin/dkms-mok-key"
    echo
    echo "2. Enroll the new key. You will be asked to create a password:"
    echo "   sudo mokutil --import /var/lib/dkms/mok.pub"
    echo
    echo "3. Reboot your system. The MOK Manager will launch."
    echo "   Select 'Enroll MOK', 'Continue', and enter the password you just"
    echo "   created to complete the enrollment."
    echo
    echo "Once this is done, DKMS will automatically sign the CoreFreq module"
    echo "now and for all future kernel updates."
    echo "----------------------------------------------------------------------"
    echo
fi

%preun
# This script runs before the package is uninstalled.

# 1. Stop and disable the service.
%systemd_preun corefreqd.service

# 2. Remove the module from DKMS. This is the most critical step for clean removal.
#    It removes the source, all built modules, and cleans up links.
if [ -f /usr/sbin/dkms ]; then
    echo "Removing CoreFreq from DKMS..."
    dkms remove -m %{name} -v %{version} --all >/dev/null 2>&1 || :
fi

%postun
# Final systemd cleanup after uninstallation.
%systemd_postun_with_restart corefreqd.service


# --- Files Section ---
# This section lists every single file and directory that belongs to the package.

%files
%license LICENSE
%doc README.md
%{_bindir}/corefreqd
%{_bindir}/corefreq-cli
%{_unitdir}/corefreqd.service
# This is the directory containing the kernel module source code for DKMS
%{_usrsrc}/%{name}-%{version}/