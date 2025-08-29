%global corefreq_version 2.0.8

Name:           corefreq
Version:        %{corefreq_version}
Release:        3%{?dist}
Summary:        CPU monitoring software with DKMS kernel module

License:        GPL-2.0-only
URL:            https://github.com/cyring/CoreFreq
Source0:        %{url}/archive/refs/tags/%{version}.tar.gz#/%{name}-%{version}.tar.gz
Source1:        corefreqd.service
Patch0:         dkms.conf.patch

BuildRequires:  gcc make kernel-devel dkms kmod systemd-rpm-macros patch
BuildRequires:  openssl mokutil
Requires:       dkms kernel-devel openssl mokutil

%description
CoreFreq is a CPU monitoring software designed for 64-bit Processors.
This package provides the user-space tools and the DKMS source for the
'corefreqk' kernel module, which will be automatically built, signed, and loaded.

%prep
%autosetup -n CoreFreq-%{version} -p1
%patch 0 -p1
sed -i 's/@RPM_VERSION@/%{version}/' dkms.conf

%build
# The default target 'all' builds the binaries and the .ko stub
%make_build

%install
# --- 最终修正: 手动安装文件，绝不使用 'make install' ---
# 1. 安装用户空间程序 (它们在 'build' 子目录中)
install -D -m 0755 build/corefreqd %{buildroot}%{_bindir}/corefreqd
install -D -m 0755 build/corefreq-cli %{buildroot}%{_bindir}/corefreq-cli

# 2. 安装我们自己提供的健壮的 service 文件
install -D -m 0644 %{SOURCE1} %{buildroot}%{_unitdir}/corefreqd.service

# 3. 设置 DKMS 源码目录
%global dkms_source_dir %{_usrsrc}/%{name}-%{version}
install -d -m 755 %{buildroot}%{dkms_source_dir}
cp -a . %{buildroot}%{dkms_source_dir}/

%post
# --- NVIDIA 级全自动签名脚本 (无需改动) ---
MOK_KEY_DIR="/etc/pki/corefreq"
MOK_PRIV_KEY="${MOK_KEY_DIR}/private_key.priv"
MOK_PUB_KEY="${MOK_KEY_DIR}/public_key.der"
if [ ! -f "${MOK_PRIV_KEY}" ]; then
    echo "--- Secure Boot key not found. Generating a new key for CoreFreq ---"
    mkdir -p "${MOK_KEY_DIR}"
    openssl req -new -x509 -newkey rsa:2048 -keyout "${MOK_PRIV_KEY}" -outform DER -out "${MOK_PUB_KEY}" -nodes -days 36500 -subj "/CN=CoreFreq DKMS Signing Key/" >/dev/null 2>&1
    echo "----------------------------------------------------------------------"
    echo "ATTENTION: SECURE BOOT FIRST-TIME SETUP"
    echo "A new key has been generated. You must now enroll it into your UEFI."
    echo "1. Run:   sudo mokutil --import ${MOK_PUB_KEY}"
    echo "   (You will be asked to create a password for this one-time action.)"
    echo "2. Reboot your computer and follow the prompts at the blue screen."
    echo "----------------------------------------------------------------------"
fi
if dkms status -m %{name} -v %{version} | grep -q installed; then
    dkms remove -m %{name} -v %{version} --all >/dev/null 2>&1 || :
fi
dkms add -m %{name} -v %{version} >/dev/null 2>&1 || :
dkms autoinstall >/dev/null 2>&1 || :
CURRENT_KERNEL=$(ls -t /lib/modules | head -n1)
MODULE_PATH="/lib/modules/${CURRENT_KERNEL}/extra/corefreqk.ko"
if [ -f "${MOK_PRIV_KEY}" ] && [ -f "${MODULE_PATH}" ]; then
    echo "--- Signing the CoreFreq module for kernel ${CURRENT_KERNEL} ---"
    /usr/src/kernels/${CURRENT_KERNEL}/scripts/sign-file sha256 "${MOK_PRIV_KEY}" "${MOK_PUB_KEY}" "${MODULE_PATH}"
fi
%systemd_postun_with_restart corefreqd.service

%preun
%systemd_preun corefreqd.service
if [ $1 -eq 0 ]; then
    /sbin/rmmod corefreqk >/dev/null 2>&1 || :
    dkms remove -m %{name} -v %{version} --all >/dev/null 2>&1 || :
fi

%postun
%systemd_postun_with_restart corefreqd.service

%files
%license LICENSE
%doc README.md
%{_bindir}/corefreq-cli
%{_bindir}/corefreqd
%{_unitdir}/corefreqd.service
%{_usrsrc}/%{name}-%{version}/

%changelog
* Fri Aug 29 2025 Sunny Yang <yxh9956@gmail.com> - 2.0.8-1
- Final release for Copr, validated against upstream Makefile.
- Uses manual install to avoid 'make install' side effects, which is correct for DKMS.
- Implements NVIDIA-style, fully automatic key generation and signing for Secure Boot.
- Uses a patch file for a clean, RPM-friendly dkms.conf.
- Ships a robust, custom systemd service file for reliability.