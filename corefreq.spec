
%global debug_package %{nil}
%global srcname CoreFreq

Name:           corefreq
Version:        2.0.8
Release:        1%{?dist}
Summary:        CPU monitoring and tuning software with DKMS kernel module

License:        GPL-2.0-only
URL:            https://github.com/cyring/CoreFreq

Source0:        %{url}/archive/refs/tags/%{version}.tar.gz

BuildRequires:  gcc make kernel-devel dkms kmod systemd
Requires:       dkms kernel-devel

%description
CoreFreq is a CPU monitoring software with BIOS-like functionalities.
This package provides the user-space tools and the DKMS source for the
'corefreqk' kernel module, which will be automatically built, loaded, and started.

%prep
%autosetup -n %{srcname}-%{version}

%build
mkdir -p build
make %{?_smp_mflags} CFLAGS="%{optflags}" corefreqd corefreq-cli

%install
install -D -m 0755 build/corefreqd %{buildroot}%{_sbindir}/corefreqd
install -D -m 0755 build/corefreq-cli %{buildroot}%{_bindir}/corefreq-cli
install -D -m 0644 corefreqd.service %{buildroot}%{_unitdir}/corefreqd.service
%global dkms_source_dir %{_usrsrc}/%{name}-%{version}
install -d -m 755 %{buildroot}%{dkms_source_dir}
cp -a . %{buildroot}%{dkms_source_dir}/
cat > %{buildroot}%{dkms_source_dir}/dkms.conf << 'DKMS_EOF'
PACKAGE_NAME="%{name}"
PACKAGE_VERSION="%{version}"
MAKE[0]="make -C . all"
BUILT_MODULE_NAME[0]="corefreqk"
BUILT_MODULE_LOCATION[0]="build/"
DEST_MODULE_LOCATION[0]="/extra"
AUTOINSTALL="yes"
DKMS_EOF
install -d -m 755 %{buildroot}%{_sysconfdir}/modules-load.d
echo corefreqk > %{buildroot}%{_sysconfdir}/modules-load.d/%{name}.conf


%post
# Step 1: Build the kernel module.
dkms add -m %{name} -v %{version} >/dev/null 2>&1 || :
dkms autoinstall >/dev/null 2>&1 || :

# Step 2: Try to load the module and check for Secure Boot errors.
if ! /sbin/modprobe corefreqk >/dev/null 2>&1; then
    # The modprobe failed. Check dmesg to see if it was a key rejection.
    if dmesg | grep -q "Key was rejected by service"; then
        # It was! Print a helpful message for the user.
        echo "------------------------------------------------------------------"
        echo "ATTENTION: SECURE BOOT"
        echo "The CoreFreq kernel module was built and signed successfully, but"
        echo "your system's Secure Boot prevented it from loading."
        echo
        echo "This is normal for the first installation of a custom module."
        echo
        echo "To approve the key, please follow these steps:"
        echo "1. Run this command: sudo mokutil --import /var/lib/dkms/mok.pub"
        echo "   (You will be asked to create a temporary password.)"
        echo "2. Reboot your computer."
        echo "3. At the blue 'MOK Manager' screen that appears on boot,"
        echo "   select 'Enroll MOK' and follow the prompts, entering the"
        echo "   password you created."
        echo
        echo "After the reboot, the module will be trusted and will load automatically."
        echo "------------------------------------------------------------------"
    fi
fi

# Step 3: Enable and start the daemon.
# It will only succeed if the module is loaded.
systemctl daemon-reload >/dev/null 2>&1 || :
systemctl enable --now corefreqd.service >/dev/null 2>&1 || :


%preun
systemctl disable --now corefreqd.service >/dev/null 2>&1 || :
/sbin/rmmod corefreqk >/dev/null 2>&1 || :
if [ $1 -eq 0 ]; then
  dkms remove -m %{name} -v %{version} --all >/dev/null 2>&1 || :
fi


%files
%doc README.md
%license LICENSE
%{_sbindir}/corefreqd
%{_bindir}/corefreq-cli
%{_unitdir}/corefreqd.service
%{_usrsrc}/%{name}-%{version}/
%config(noreplace) %{_sysconfdir}/modules-load.d/%{name}.conf

%changelog
* Fri Jul 26 2024 Your Name <youremail@example.com> - 2.0.7-15
- Added user-friendly prompt for MOK enrollment on Secure Boot systems.
- Final polished version.
