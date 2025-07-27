# File: corefreq-dkms.spec
%global debug_package %{nil}
%global kmod_name corefreq
%global srcname CoreFreq

Name:           %{kmod_name}-dkms
Version:        2.0.7
Release:        1%{?dist}
Summary:        DKMS source for the CoreFreq kernel module

License:        GPL-2.0-only
URL:            https://github.com/cyring/CoreFreq
Source0:        https://github.com/cyring/%{srcname}/archive/refs/tags/%{version}.tar.gz

BuildArch:      noarch

BuildRequires:  dkms
Requires:       dkms

%description
This package provides the source code for the CoreFreq kernel module
and registers it with the DKMS service. When a new kernel is installed,
DKMS will automatically rebuild the corefreqk module for it.

This package is a dependency of the main 'corefreq' package.

%prep
%autosetup -n %{srcname}-%{version}

%install
%global dkms_src_dir %{_usrsrc}/%{kmod_name}-%{version}
install -d -m 0755 %{buildroot}%{dkms_src_dir}
cp -a ./* %{buildroot}%{dkms_src_dir}/

# Add modules-load.d file to auto-load the 'corefreqk' module on boot.
install -d -m 755 %{buildroot}%{_sysconfdir}/modules-load.d/
echo corefreqk > %{buildroot}%{_sysconfdir}/modules-load.d/%{kmod_name}.conf

%post
# Register the module with DKMS.
dkms add -m %{kmod_name} -v %{version}

# Build and install the module for the currently running kernel.
# The 'dkms install' command implies 'build' first.
dkms install -m %{kmod_name} -v %{version}

# --- PORTED SECURE BOOT CHECK FROM YOUR KMOD TEMPLATE ---
# After the DKMS install, try to load the module to check for Secure Boot issues.
if ! /sbin/modprobe corefreqk >/dev/null 2>&1; then
    # Check dmesg for the specific error messages related to key rejection.
    if dmesg | grep -q -e "Key was rejected by service" -e "Required key not available"; then
        echo "------------------------------------------------------------------"
        echo "ATTENTION: SECURE BOOT"
        echo "The CoreFreq kernel module was built, but Secure Boot prevented it from loading."
        echo
        echo "To use this module, you must enroll the DKMS signing key (MOK)."
        echo "Please follow these steps:"
        echo "1. Run this command: sudo mokutil --import /etc/pki/akmods/certs/public_key.der"
        echo "   (Note: DKMS on Fedora uses the 'akmods' key. You will be asked to create a password.)"
        echo "2. Reboot your computer."
        echo "3. At the blue 'MOK Manager' screen that appears after the vendor logo,"
        echo "   select 'Enroll MOK', continue, and enter the password you created."
        echo "------------------------------------------------------------------"
    fi
fi

%preun
# Before uninstallation, cleanly remove the module from all kernels.
dkms remove -m %{kmod_name} -v %{version} --all

%files
%doc README.md
%license LICENSE
%{_usrsrc}/%{kmod_name}-%{version}/
%config(noreplace) %{_sysconfdir}/modules-load.d/%{kmod_name}.conf

%changelog
* Tue Jul 30 2024 Your Name <youremail@example.com> - 2.0.7-1
- Initial DKMS package. Includes Secure Boot MOK prompt for user convenience.