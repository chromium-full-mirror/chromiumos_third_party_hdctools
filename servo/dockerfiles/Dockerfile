# Copyright 2021 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

ARG BUILD_ENV=production

######################################################################
FROM alpine/git as chromiumos_overlays
WORKDIR /
RUN git clone --filter=blob:none --no-checkout --depth 1 --sparse https://chromium.googlesource.com/chromiumos/overlays/chromiumos-overlay
WORKDIR /chromiumos-overlay
RUN git sparse-checkout init --cone
RUN git sparse-checkout add dev-embedded/libftdi/files/ dev-embedded/libftdi/files/confs/
RUN git checkout

######################################################################
FROM debian:bullseye as clang-builder

RUN apt-get update \
    && apt-get install -y \
        autoconf \
        build-essential \
        clang \
        curl \
        git \
        libssl-dev \
        libtool \
        pkg-config \
        python3 \
        python3-distutils \
        python3-setuptools \
        uuid-dev \
        wget

RUN update-alternatives --auto c++
RUN update-alternatives --auto cc

RUN wget https://bootstrap.pypa.io/get-pip.py
RUN python3 ./get-pip.py
RUN pip3 install --upgrade pip && pip3 install wheel

ENV CC=clang
ENV CXX=clang++
# Required to make the platform/ec makefile not think we are building
# from portage.
ENV BUILDCC_PREFIX=

######################################################################
FROM clang-builder as cbfstool

RUN wget https://coreboot.org/releases/coreboot-4.14.tar.xz && tar xf coreboot-4.14.tar.xz && rm /coreboot-4.14.tar.xz
RUN cd /coreboot-4.14/util/cbfstool && make
RUN strip /coreboot-4.14/util/cbfstool/cbfstool

######################################################################
FROM clang-builder as libusb-builder

RUN git clone https://github.com/libusb/libusb
WORKDIR /libusb

# Disable udev to avoid issues of libusb thinking the device is still attached
# after a software reboot.
RUN ./bootstrap.sh && ./configure --with-pic --disable-udev && make && make install

# Change the package config to have pthread for linking.
RUN sed -i 's/Libs: -L\${libdir} -lusb-1.0/Libs: -L\${libdir} -lusb-1.0 -lpthread /g' /libusb/libusb-1.0.pc

#####################################################################
FROM clang-builder as libftdi

RUN wget https://www.intra2net.com/en/developer/libftdi/download/libftdi1-1.2.tar.bz2 \
    && tar xf libftdi1-1.2.tar.bz2 \
    && rm libftdi1-1.2.tar.bz2

COPY --from=chromiumos_overlays \
    /chromiumos-overlay/dev-embedded/libftdi/files/libftdi-1.2-getopts.patch \
    /libftdi1-1.2/

COPY --from=chromiumos_overlays \
    /chromiumos-overlay/dev-embedded/libftdi/files/confs/*.conf \
    /usr/share/libftdi/

RUN apt-get update --no-install-recommends  \
    && apt-get install -y --no-install-recommends  \
        cmake \
    && rm -rf /var/lib/apt/lists/*


COPY --from=libusb-builder /usr/local/include/libusb-1.0/libusb.h /usr/local/include/libusb-1.0/
COPY --from=libusb-builder /usr/local/lib/libusb-1.0.a /usr/local/lib
COPY --from=libusb-builder /usr/local/lib/libusb-1.0.so.?.?.? /usr/local/lib/
COPY --from=libusb-builder /libusb/*.pc /usr/lib/pkgconfig/

WORKDIR /libftdi1-1.2

RUN git apply libftdi-1.2-getopts.patch

# The examples have a linking issue, not used for anything, disable them.
RUN sed -i s/.*examples.*//g CMakeLists.txt
RUN sed -i s/.*examples.*//g libftdi1.spec.in


RUN mkdir build \
    && cd build \
    && cmake -DCMAKE_INSTALL_PREFIX="/usr" ../ \
    && make \
    && make install

WORKDIR /

######################################################################
FROM libftdi as ec-builder

RUN git clone https://chromium.googlesource.com/chromiumos/platform/ec

WORKDIR /

RUN git clone https://chromium.googlesource.com/chromiumos/third_party/flashmap

WORKDIR /flashmap
RUN make && make install

# Install libusb.
COPY --from=libusb-builder /usr/local/include/libusb-1.0/libusb.h /usr/local/include/libusb-1.0/
COPY --from=libusb-builder /usr/local/lib/libusb-1.0.a /usr/local/lib
COPY --from=libusb-builder /usr/local/lib/libusb-1.0.so.?.?.? /usr/local/lib/
COPY --from=libusb-builder /libusb/libusb-1.0.pc /usr/local/pkg/
ENV PKG_CONFIG_PATH=${PKG_CONFIG_PATH}:/usr/local/pkg/

WORKDIR /ec
RUN make utils-host BOARD=host \
    && make -C extra/usb_updater usb_updater2

COPY servo/dockerfiles/setup_ec.py .
RUN PACKAGE="ec3po" python3 setup_ec.py bdist_wheel
RUN PACKAGE="ecusb" python3 setup_ec.py bdist_wheel
RUN PACKAGE="servo_updater" python3 setup_ec.py bdist_wheel
RUN PACKAGE="powerlog" python3 setup_ec.py bdist_wheel
RUN PACKAGE="console" python3 setup_ec.py bdist_wheel
RUN PACKAGE="unpack_ftb" python3 setup_ec.py bdist_wheel

RUN curl https://raw.githubusercontent.com/kward/shflags/master/shflags --output /usr/share/misc/shflags

RUN strip /ec/extra/usb_updater/usb_updater2 \
          /ec/build/host/util/stm32mon \
          /ec/build/host/util/uartupdatetool \
          /ec/build/host/util/iteflash

RUN strip --strip-unneeded /usr/lib/libfmap.so* /usr/lib/libftdi*

######################################################################
FROM clang-builder as protoc-builder

WORKDIR /
RUN wget  https://github.com/protocolbuffers/protobuf/releases/download/v3.19.3/protobuf-python-3.19.3.tar.gz && tar xf protobuf-python-3.19.3.tar.gz && rm protobuf-python-3.19.3.tar.gz
# Version is set to match version of protoc in the chroot
# When updating package versions, also update protoc to x.y.z in:
# chromium/src/third_party/portage-stable/dev-libs/protobuf/protobuf-x.y.z.ebuild
RUN cd /protobuf-3.19.3/ && ./configure && make && make check && make install && ldconfig

######################################################################
FROM libftdi as hdctools-builder
# For cloud build and for developers copying the local source is correct, if
# you need to build from checked in code vs you local source comment out the
# copy command and uncomment the clone command.
COPY / hdctools/
#RUN git clone https://chromium.googlesource.com/chromiumos/third_party/hdctools

# Install protoc
# Put  protoc in /usr/bin to match chroot's protoc location so that proto/Makefile
# runs without issue
COPY --from=protoc-builder /usr/local/bin/protoc /usr/bin
COPY --from=protoc-builder /usr/local/lib/libproto* /usr/local/lib/
RUN ldconfig

RUN pip3 install pytest

WORKDIR /hdctools
RUN echo 'HOSTOS_CWARN=' >> 'defs/c-Linux.mk'
RUN make
RUN make install

# Setuptools skips nested entry point. Adding custom setup.py to overcome.
COPY /servo/dockerfiles/setup_hdctools.py .
RUN PACKAGE="servo" python3 setup_hdctools.py bdist_wheel
RUN PACKAGE="usbkm232" python3 setup_hdctools.py bdist_wheel
RUN PACKAGE="servo_mfg" python3 setup_hdctools.py bdist_wheel

#####################################################################
FROM clang-builder as uhubctl-builder

RUN git clone https://github.com/mvp/uhubctl
WORKDIR /uhubctl
COPY --from=libusb-builder /usr/local/include/libusb-1.0/libusb.h /usr/local/include/libusb-1.0/
COPY --from=libusb-builder /libusb/*.pc /usr/lib/pkgconfig/
COPY --from=libusb-builder /usr/local/lib/libusb-1.0.so.?.?.? /usr/local/lib/
COPY --from=libusb-builder /usr/local/lib/libusb-1.0.a /usr/local/lib
RUN make
RUN strip  /uhubctl/uhubctl

######################################################################
FROM python:3.10-bullseye as firmware-installer

RUN apt-get update --no-install-recommends  \
    && apt-get install -y --no-install-recommends  \
         apt-transport-https ca-certificates gnupg sudo \
    && rm -rf /var/lib/apt/lists/*

RUN echo "deb [signed-by=/usr/share/keyrings/cloud.google.gpg] https://packages.cloud.google.com/apt cloud-sdk main" | sudo tee -a /etc/apt/sources.list.d/google-cloud-sdk.list
RUN curl https://packages.cloud.google.com/apt/doc/apt-key.gpg | sudo tee /usr/share/keyrings/cloud.google.gpg
RUN sudo apt-get update && sudo apt-get install google-cloud-cli

RUN mkdir -p /usr/share/servo_updater/firmware/
WORKDIR /usr/share/servo_updater/firmware/
COPY /servo/dockerfiles/servo_firmware_provision.py servo_firmware_provision.py
RUN python servo_firmware_provision.py && rm servo_firmware_provision.py

######################################################################
FROM libftdi as flashrom-builder

WORKDIR /
RUN pip3 install meson ninja
RUN git clone https://chromium.googlesource.com/chromiumos/third_party/flashrom

RUN apt-get update \
    && apt-get install -y \
        cmake \
	    libpci-dev

WORKDIR /flashrom
RUN meson builddir && cd builddir && meson install
RUN strip /usr/local/sbin/flashrom

######################################################################
FROM flashrom-builder as futility-builder

# Install vboot.
WORKDIR /
RUN git clone https://chromium.googlesource.com/chromiumos/platform/vboot_reference
WORKDIR /vboot_reference
RUN sed -i 's/%" PRIi64 "/%ld/g' futility/cmd_gbb_utility.c
RUN make && make install

RUN strip /usr/bin/futility

######################################################################
FROM python:3.10-slim-bullseye

# Install libusb.
COPY --from=libusb-builder /usr/local/include/libusb-1.0/libusb.h /usr/local/include/libusb-1.0/
COPY --from=libusb-builder /libusb/*.pc /usr/lib/pkgconfig/
COPY --from=libusb-builder /usr/local/lib/libusb-1.0.so.?.?.? /usr/local/lib/
COPY --from=libusb-builder /usr/local/lib/libusb-1.0.a /usr/local/lib

RUN apt-get update --no-install-recommends \
    && apt-get install -y --no-install-recommends \
        dnsutils \
        fdisk \
        iptables \
        iputils-ping \
        kmod \
        libatomic1 \
        libpci-dev \
        lsof \
        procps \
        sudo \
        usbutils \
        udev \
        xz-utils \
        build-essential \
        make \
        gcc \
    && rm -rf /var/lib/apt/lists/* \
    && update-alternatives --set ip6tables /usr/sbin/ip6tables-nft

# Install python packages.
COPY /servo/dockerfiles/requirements.txt /opt/requirements.txt
RUN pip install --upgrade pip && pip3 --no-cache-dir install -r /opt/requirements.txt

WORKDIR /hdctools/chromeos/
COPY --from=hdctools-builder /hdctools/chromeos/servod_utils.sh .
WORKDIR /wheels
COPY --from=hdctools-builder /hdctools/dist/* ./
COPY --from=ec-builder /ec/dist/*.whl ./
RUN pip install *.whl
WORKDIR /
RUN rm -rf wheels

# Install servo_firmware.
RUN mkdir -p /usr/share/servo_updater/firmware/
COPY --from=firmware-installer /usr/share/servo_updater/firmware/ /usr/share/servo_updater/firmware/
RUN ln -s /usr/local/share/servo_updater/* /usr/share/servo_updater/

COPY --from=chromiumos_overlays \
    /chromiumos-overlay/dev-embedded/libftdi/files/confs/*.conf \
    /usr/share/libftdi/

# Install ec tools
COPY --from=ec-builder \
    /ec/build/host/util/ectool \
    /ec/build/host/util/ec_parse_panicinfo \
    /ec/build/host/util/ec_sb_firmware_update \
    /ec/extra/usb_updater/usb_updater2 \
    /ec/build/host/util/stm32mon \
    /ec/build/host/util/uartupdatetool \
    /ec/build/host/util/iteflash \
    /ec/util/flash_ec \
    /ec/util/uart_stress_tester.py \
    /usr/sbin/
RUN chmod u+x /usr/sbin/* /usr/bin/*

COPY --from=ec-builder \
        /usr/lib/libfmap.so* \
        /usr/lib/libftdi* \
        /usr/lib/

COPY --from=ec-builder /usr/share/misc/shflags /usr/share/misc/shflags
COPY --from=ec-builder /ec/util/openocd/* /usr/share/ec-devutils/

COPY --from=hdctools-builder /hdctools/servo/tests/ /hdctools/servo/tests/

RUN mkdir -p /usr/share/ec-devutils

# Install uhubctl
COPY --from=uhubctl-builder /uhubctl/uhubctl /usr/local/bin/
RUN chmod 755 /usr/local/bin/uhubctl

# Install flashrom
COPY --from=flashrom-builder /usr/local/sbin/flashrom /usr/local/sbin/
RUN chmod 755 /usr/local/sbin/flashrom

#Install futility
COPY --from=futility-builder /usr/bin/futility /usr/bin/
RUN chmod 755 /usr/bin/futility
COPY --from=futility-builder /usr/local/lib/*/libflashrom.so.1.0.0 /usr/lib
RUN ln -s /usr/lib/libflashrom.so.1.0.0 /usr/lib/libflashrom.so.1 && \
   ln -s /usr/lib/libflashrom.so.1.0.0 /usr/lib/libflashrom.so

# Install cbfstool for flashrom and ec.
COPY --from=cbfstool /coreboot-4.14/util/cbfstool/cbfstool /usr/local/bin/
RUN chmod 755 /usr/local/bin/cbfstool

RUN mkdir -p /usr/share/ec-devutils

ENV WARN_ONLY_ON_UNKNOWN_ENV="SERVO_FW_ALL_CHANNEL_OK"

COPY /servo/dockerfiles/update_servo_firmware.py \
     /servo/dockerfiles/start_servod.sh /servo/dockerfiles/stop_servod.sh \
     /

# Running sync in the container with no params will crash the host bare metal as all disks
# are mounted, put a script in the place of sync that checks are lease one argument is passed
# if no arguments are passed an error is thrown.
RUN mv /bin/sync /usr/local/bin/real_sync
COPY /servo/dockerfiles/sync /bin
RUN chmod 755 /bin/sync

# Try to remove as much as possible to make the container smaller
RUN apt-get remove --purge -y \
        xz-utils \
        build-essential \
        make \
        gcc \
    && apt-get autoclean \
    && rm -rf /var/lib/apt/lists/* \
    && rm -rf /usr/local/lib/python3.10/site-packages/numpy/core/tests \
    && python -m pip uninstall -y pip \
    && rm -rf /var/cache/debconf \
    && rm -rf /usr/share/doc \
    && rm -rf /usr/share/zoneinfo/
