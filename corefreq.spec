%global gh_owner cyring
%global gh_repo CoreFreq
%global dkms_name corefreq
# This is the key to fixing the final build error
%global debug_package %{nil}

Name:           corefreq
Version:        2.0.8
Release:        12%{?dist}
Summary:        CPU monitoring software with BIOS-like functionalities

License:        GPL-2.0-or-later
URL:            https://github.com/%{gh_owner}/%{gh_repo}
Source0:        %{url}/archive/refs/tags/%{version}.tar.gz
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

# A pure metapackage should have an empty %files section
%files

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
%setup -q -n %{gh_repo}-%{version}

# Use sed to modify the Makefile directly.
sed -i 's/WARNING ?= -Wall -Wfatal-errors/WARNING ?=/' Makefile

# Copy secondary sources into the build directory
cp %{SOURCE1} .
cp %{SOURCE2} .

%build
# Build the userspace binaries
%make_build corefreqd corefreq-cli

%install
# Step 1: Install the compiled userspace binaries to their final destination
install -Dm755 build/corefreqd %{buildroot}%{_bindir}/corefreqd
install -Dm755 build/corefreq-cli %{buildroot}%{_bindir}/corefreq-cli
install -Dm644 corefreqd.service %{buildroot}%{_unitdir}/corefreqd.service

# Step 2: Manually remove the compiled artifacts from the source tree.
rm -f build/corefreqd build/corefreq-cli build/*.o

# Step 3: Now copy the *clean* source tree for the DKMS package
install -d %{buildroot}%{_usrsrc}/%{dkms_name}-%{version}/
cp -a . %{buildroot}%{_usrsrc}/%{dkms_name}-%{version}/

# Step 4: Finalize DKMS configuration
sed -i 's/@VERSION@/%{version}/' %{buildroot}%{_usrsrc}/%{dkms_name}-%{version}/dkms.conf

%post dkms
dkms add -m %{dkms_name} -v %{version} --rpm_safe_upgrade
dkms build -m %{dkms_name} -v %{version}
dkms install -m %{dkms_name} -v %{version} --rpm_safe_upgrade

%preun dkms
if [ $1 -eq 0 ]; then
  dkms remove -m %{dkms_name} -v %{version} --all
fi

%posttrans dkms
if command -v mokutil >/dev/null 2>&1 && mokutil --sb-state | grep -q enabled; then
  MOK_KEY="/var/lib/dkms/mok.pub"
  if [ -f "$MOK_KEY" ] && ! mokutil --test-key "$MOK_KEY" >/dev/null 2>&1; then
    echo "--------------------------------------------------------------------------------"
    echo "ATTENTION: Secure Boot is enabled and the DKMS signing key is not yet enrolled."
    echo
    echo "The system may now ask you to create a password for the MOK enrollment."
    echo
    echo "1. On reboot, the blue 'MOK management' screen will appear."
    echo "2. Select 'Enroll MOK' -> 'Continue'."
    echo "3. When asked to 'Enroll the key(s)?', select 'Yes'."
    echo "4. Enter the password you just created."
    echo "--------------------------------------------------------------------------------"
    mokutil --import-key "$MOK_KEY" --root-pw || true
  fi
fi

%post server
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
# This now owns the clean source tree
%{_usrsrc}/%{dkms_name}-%{version}/

%changelog
* Thu Aug 07 2025 Fedora Packager - 2.0.8-12
- Disabled debug packages to fix final 'Empty %files' error.

* Thu Aug 07 2025 Fedora Packager - 2.0.8-11
- Replaced 'make clean' with a manual 'rm' of build artifacts to fix build environment errors.
- Cleaned up main package %files section to be a proper metapackage.