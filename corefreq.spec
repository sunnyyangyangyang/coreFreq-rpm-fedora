%global gh_owner cyring
%global gh_repo CoreFreq
%global dkms_name corefreq

Name:           corefreq
Version:        2.0.8
Release:        6%{?dist}
Summary:        CPU monitoring software with BIOS-like functionalities

License:        GPL-2.0-or-later
URL:            https://github.com/%{gh_owner}/%{gh_repo}
# Correct Source URL
Source0:        %{url}/archive/refs/tags/%{version}.tar.gz
# Declare the patch using the standard Patch0 tag
Patch0:         corefreq-honor-compiler-flags.patch
# Declare other sources
Source1:        dkms.conf
Source2:        corefreqd.service

ExclusiveArch:  x86_64 aarch64

BuildRequires:  gcc
BuildRequires:  make
BuildRequires:  sed
BuildRequires:  kernel-devel
BuildRequires:  dkms
BuildRequires:  systemd-rpm-macros

# Metapackage for convenience
Requires:       %{name}-client%{?_isa} = %{version}-%{release}
Requires:       %{name}-server%{?_isa} = %{version}-%{release}

%description
CoreFreq is a CPU monitoring software with BIOS-like functionalities.
This is a metapackage that installs all CoreFreq components.

%package dkms
Summary:        DKMS driver sources for CoreFreq
Requires:       dkms
Requires:       kernel-devel
Requires:       mokutil
Requires:       openssl
Provides:       %{name}-kmod = %{version}-%{release}

%description dkms
This package contains the source for the corefreqk kernel module and configures
DKMS to build and install it. It supports signing for Secure Boot.

%package server
Summary:        CoreFreq server daemon
Requires:       %{name}-dkms = %{version}-%{release}
Requires:       systemd
%{?systemd_requires}

%description server
Contains the corefreqd daemon and systemd service.

%package client
Summary:        CoreFreq command-line client
Requires:       %{name}-server = %{version}-%{release}

%description client
Contains corefreq-cli, a command-line interface for the daemon.

%prep
# Corrected %prep: Use the robust %autosetup macro.
# -p1 applies all Patch files (like Patch0) correctly.
# -n specifies the non-standard directory name inside the tarball (CoreFreq-v2.0.8).
%autosetup -p1 -n %{gh_repo}-v%{version}

# Manually copy the extra source files into the build directory.
# This must be done after %autosetup has created the directory.
cp %{SOURCE1} .
cp %{SOURCE2} .

%build
# %make_build passes standard Fedora CFLAGS and LDFLAGS
%make_build corefreqd corefreq-cli

%install
# Install userspace binaries
install -Dm755 build/corefreqd %{buildroot}%{_bindir}/corefreqd
install -Dm755 build/corefreq-cli %{buildroot}%{_bindir}/corefreq-cli

# Install systemd service file (using the one we copied into the build dir)
install -Dm644 corefreqd.service %{buildroot}%{_unitdir}/corefreqd.service

# Install sources for DKMS
install -d %{buildroot}%{_usrsrc}/%{dkms_name}-%{version}/
cp -a . %{buildroot}%{_usrsrc}/%{dkms_name}-%{version}/

# Substitute the package version in dkms.conf and install it
sed -i 's/@VERSION@/%{version}/' dkms.conf
install -Dm644 dkms.conf %{buildroot}%{_usrsrc}/%{dkms_name}-%{version}/dkms.conf

%post dkms
dkms add -m %{dkms_name} -v %{version} --rpm_safe_upgrade
dkms build -m %{dkms_name} -v %{version}
dkms install -m %{dkms_name} -v %{version} --rpm_safe_upgrade

%preun dkms
if [ $1 -eq 0 ]; then
  dkms remove -m %{dkms_name} -v %{version} --all
fi

%posttrans dkms
# Instruct user to enroll the DKMS signing key (MOK) if Secure Boot is enabled.
if command -v mokutil >/dev/null 2>&1 && mokutil --sb-state | grep -q enabled; then
  MOK_KEY="/var/lib/dkms/mok.pub"
  if [ -f "$MOK_KEY" ] && ! mokutil --test-key "$MOK_KEY" >/dev/null 2>&1; then
    echo "--------------------------------------------------------------------------------"
    echo "ATTENTION: Secure Boot is enabled and the DKMS signing key is not yet enrolled."
    echo
    echo "The system may now ask you to create a password for the MOK enrollment."
    echo "Please enter a temporary password you can remember for the reboot."
    echo
    echo "1. On reboot, the blue 'MOK management' screen will appear."
    echo "2. Select 'Enroll MOK' -> 'Continue'."
    echo "3. When asked to 'Enroll the key(s)?', select 'Yes'."
    echo "4. Enter the password you just created."
    echo
    echo "The CoreFreq kernel module will not load until this key is enrolled."
    echo "--------------------------------------------------------------------------------"
    mokutil --import-key "$MOK_KEY" --root-pw || true
  fi
fi

%post server
# Use modern macro to handle service enable/start on install and restart on upgrade.
%systemd_post_with_restart corefreqd.service

%preun server
%systemd_preun corefreqd.service

%files client
%license LICENSE
%doc README.md
%{_bindir}/corefreq-cli

%files server
%{_bindir}/corefreqd
%{_unitdir}/corefreqd.service

%files dkms
%{_usrsrc}/%{dkms_name}-%{version}/
%exclude %{_usrsrc}/%{dkms_name}-%{version}/build/corefreqd
%exclude %{_usrsrc}/%{dkms_name}-%{version}/build/corefreq-cli
%exclude %{_usrsrc}/%{dkms_name}-%{version}/corefreqd.service
%exclude %{_usrsrc}/%{dkms_name}-%{version}/dkms.conf

%changelog
* Thu Aug 08 2025 Fedora Packager - 2.0.8-6
- Corrected patch application by using standard Patch0 tag and robust %autosetup macro.
- This fixes the 'No patch number 1' error in the COPR build environment.

* Thu Aug 08 2025 Fedora Packager - 2.0.8-5
- Corrected Source0 URL and %prep section to be compatible with COPR build system.
- Changed %autosetup to manual %setup and %patch to handle non-standard tarball names.

* Thu Aug 07 2025 Fedora Packager - 2.0.8-3
- Hardened spec against build errors and improved Fedora version flexibility.
- Modified compiler flags patch to use system defaults instead of suppressing warnings.
- Refined systemd and Secure Boot MOK enrollment logic for better user experience.

* Thu Aug 07 2025 Fedora Packager - 2.0.8-2
- Enhanced spec with fully automated systemd, DKMS, and Secure Boot MOK enrollment logic.
- Added user prompts for MOK enrollment and ensured clean uninstallation.

* Thu Aug 07 2025 Fedora Packager - 2.0.8-1
- Initial Fedora package combining openSUSE spec and Arch PKGBUILD with DKMS.