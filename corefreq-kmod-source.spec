%global debug_package %{nil}
%global kmod_name corefreq
%global srcname CoreFreq

Name:           corefreq-kmod-source
Version:        2.0.7
Release:        1%{?dist}
Summary:        Source files for building the CoreFreq kmod via akmods

License:        GPL-2.0-only
URL:            https://github.com/cyring/CoreFreq
Source0:        %{url}/archive/refs/tags/%{version}.tar.gz

%description
This package contains the source tarball and the template spec file
needed by the akmods service to build the CoreFreq kernel module.
It is normally installed as a dependency of the akmod-corefreq package.

%install
install -d -m 0755 %{buildroot}%{_usrsrc}/akmods/SOURCES/
install -d -m 0755 %{buildroot}%{_usrsrc}/akmods/
install -p -m 0644 %{SOURCE0} %{buildroot}%{_usrsrc}/akmods/SOURCES/

cat > %{buildroot}%{_usrsrc}/akmods/kmod-%{kmod_name}.spec << 'EOF'
%global debug_package %{nil}
%global kmod_name corefreq

Name:           kmod-%{kmod_name}
Version:        %{version}
Release:        1%{?dist}
Summary:        CoreFreq kernel module
License:        GPL-2.0-only
URL:            https://github.com/cyring/CoreFreq
BuildRequires:  kernel-devel = %{kver}
BuildRequires:  gcc
BuildRequires:  make

%description
This package provides the %{kmod_name} kernel module for kernel %{kver}.

%prep
%setup -q -n CoreFreq-%{version}

%build
make %{?_smp_mflags} -C %{_builddir}/CoreFreq-%{version} KERNELDIR=%{_usrsrc}/kernels/%{kver} corefreqk.ko

%install
install -D -m 0755 build/corefreqk.ko %{buildroot}%{kmodinstdir}/%{kmod_name}k.ko
install -d -m 755 %{buildroot}%{_sysconfdir}/modules-load.d
echo %{kmod_name}k > %{buildroot}%{_sysconfdir}/modules-load.d/%{kmod_name}.conf

%post
/sbin/depmod -a %{kver}
if ! /sbin/modprobe %{kmod_name}k >/dev/null 2>&1; then
    if dmesg | grep -q "Key was rejected by service"; then
        echo "------------------------------------------------------------------"
        echo "ATTENTION: SECURE BOOT"
        echo "The CoreFreq kernel module was built, but Secure Boot prevented it from loading."
        echo "You may need to enroll the akmods signing key. See Fedora documentation."
        echo "------------------------------------------------------------------"
    fi
fi
systemctl try-restart corefreqd.service >/dev/null 2>&1 || :

%preun
if [ $1 -eq 0 ]; then
    systemctl stop corefreqd.service >/dev/null 2>&1 || :
fi

%postun
/sbin/depmod -a %{kver}

%files
%kmod_files
%config(noreplace) %{_sysconfdir}/modules-load.d/%{kmod_name}.conf
EOF

%preun
if [ $1 -eq 0 ]; then
    rpm -e $(rpm -qa 'kmod-%{kmod_name}-*') &>/dev/null || :
fi

%files
%dir %{_usrsrc}/akmods
%dir %{_usrsrc}/akmods/SOURCES
%{_usrsrc}/akmods/SOURCES/CoreFreq-%{version}.tar.gz
%{_usrsrc}/akmods/kmod-%{kmod_name}.spec