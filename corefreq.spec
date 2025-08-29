%global _debugsource_packages 0
%global _debuginfo_packages 0
%global debug_package %{nil}

%global corefreq_version 2.0.8

Name:           corefreq
Version:        %{corefreq_version}
Release:        5%{?dist}
Summary:        CPU monitoring software with DKMS kernel module

License:        GPL-2.0-only
URL:            https://github.com/cyring/CoreFreq
Source0:        %{url}/archive/refs/tags/%{version}.tar.gz#/%{name}-%{version}.tar.gz
Source1:        corefreqd.service
Source2:        dkms.conf

BuildRequires:  gcc make kernel-devel dkms kmod systemd-rpm-macros
BuildRequires:  openssl mokutil
Requires:       dkms kernel-devel openssl mokutil

%description
CoreFreq is a CPU monitoring software designed for 64-bit Processors.
This package provides the user-space tools and the DKMS source for the
'corefreqk' kernel module, which will be automatically built, signed, and loaded.

%prep
%autosetup -n CoreFreq-%{version} -p1
cp %{SOURCE2} .
sed -i 's/@RPM_VERSION@/%{version}/' dkms.conf

%build
make %{?_smp_mflags} corefreqd corefreq-cli

%install
install -D -m 0755 build/corefreqd %{buildroot}%{_bindir}/corefreqd
install -D -m 0755 build/corefreq-cli %{buildroot}%{_bindir}/corefreq-cli
install -D -m 0644 %{SOURCE1} %{buildroot}%{_unitdir}/corefreqd.service
rm -rf build
%global dkms_source_dir %{_usrsrc}/%{name}-%{version}
install -d -m 755 %{buildroot}%{dkms_source_dir}
cp -a . %{buildroot}%{dkms_source_dir}/

%post
MOK_KEY_DIR="/etc/pki/corefreq"
MOK_PRIV_KEY="${MOK_KEY_DIR}/private_key.priv"
MOK_PUB_KEY="${MOK_KEY_DIR}/public_key.der"

# Generate key if needed
if [ ! -f "${MOK_PRIV_KEY}" ]; then
    echo "--- Generating Secure Boot signing key ---"
    mkdir -p "${MOK_KEY_DIR}"
    
    openssl req -new -x509 -newkey rsa:2048 \
        -keyout "${MOK_PRIV_KEY}" \
        -outform DER -out "${MOK_PUB_KEY}" \
        -nodes -days 36500 \
        -subj "/CN=CoreFreq DKMS Signing Key/" >/dev/null 2>&1
    
    chmod 600 "${MOK_PRIV_KEY}"
    chmod 644 "${MOK_PUB_KEY}"
    
    echo "----------------------------------------------------------------------"
    echo "SECURE BOOT SETUP: Run 'sudo mokutil --import ${MOK_PUB_KEY}' then reboot"
    echo "----------------------------------------------------------------------"
fi

# Standard DKMS installation (signing happens via dkms.conf POST_BUILD)
if dkms status -m %{name} -v %{version} | grep -q installed; then
    dkms remove -m %{name} -v %{version} --all >/dev/null 2>&1 || :
fi

dkms add -m %{name} -v %{version} >/dev/null 2>&1 || :
dkms autoinstall -m %{name} -v %{version} >/dev/null 2>&1 || :

/sbin/modprobe corefreqk >/dev/null 2>&1 || :
%systemd_post corefreqd.service

%postun
%systemd_postun_with_restart corefreqd.service

%files
%license LICENSE
%doc README.md
%{_bindir}/corefreq-cli
%{_bindir}/corefreqd
%{_unitdir}/corefreqd.service
%{_usrsrc}/%{name}-%{version}/
# --- We don't list the conf hook in %files ---
# It is created and removed by scripts, not owned by the package. This is safer.

%changelog
# ...