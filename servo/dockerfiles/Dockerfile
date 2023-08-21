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
FROM debian:bookworm as clang-builder

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
        python3-wheel \
        uuid-dev \
        wget
RUN update-alternatives --auto c++
RUN update-alternatives --auto cc

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
RUN git checkout "$(git tag -l | egrep '^v[0-9]+\.[0-9]+.[0-9]+$' | sort -V | tail -1)"

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
#RUN find . -type f -name "Makefile*" -exec sed -i 's#-Werror # #'  {} \;
RUN make build/host/util/iteflash BOARD=host && \
    make build/host/util/uartupdatetool BOARD=host&& \
    make build/host/util/stm32mon BOARD=host && \
    make -C extra/usb_updater usb_updater2

COPY servo/dockerfiles/setup_ec.py .
RUN PACKAGE="ecusb" python3 setup_ec.py bdist_wheel
RUN PACKAGE="servo_updater" python3 setup_ec.py bdist_wheel
RUN PACKAGE="powerlog" python3 setup_ec.py bdist_wheel
RUN PACKAGE="console" python3 setup_ec.py bdist_wheel
RUN PACKAGE="unpack_ftb" python3 setup_ec.py bdist_wheel

RUN strip /ec/extra/usb_updater/usb_updater2 \
          /ec/build/host/util/stm32mon \
          /ec/build/host/util/uartupdatetool \
          /ec/build/host/util/iteflash

RUN strip --strip-unneeded /usr/lib/libfmap.so* /usr/lib/libftdi*

######################################################################
FROM libftdi as pigweed-builder

RUN git clone https://chromium.googlesource.com/external/pigweed/pigweed/pigweed

WORKDIR /pigweed
COPY servo/dockerfiles/setup_pigweed.py .
RUN python3 setup_pigweed.py bdist_wheel

######################################################################
FROM libftdi as gcstool-builder

RUN git clone https://chromium.googlesource.com/chromiumos/platform/ec

WORKDIR /ec

RUN git checkout gsc_utils && git pull
RUN find . -type f -name "Makefile*" -exec sed -i 's#-Werror # #'  {} \;
RUN make -C extra/usb_updater gsctool

RUN strip  /ec/extra/usb_updater/gsctool

######################################################################
FROM libftdi as hdctools-builder
# For cloud build and for developers copying the local source is correct, if
# you need to build from checked in code vs you local source comment out the
# copy command and uncomment the clone command.
COPY / hdctools/
#RUN git clone https://chromium.googlesource.com/chromiumos/third_party/hdctools

RUN apt-get update \
    && apt-get install -y \
        protobuf-compiler \
        python3-pytest

WORKDIR /hdctools
RUN echo 'HOSTOS_CWARN=' >> 'defs/c-Linux.mk'
RUN make -j $(grep -c   "^processor" /proc/cpuinfo)
RUN make install

# Setuptools skips nested entry point. Adding custom setup.py to overcome.
COPY /servo/dockerfiles/setup_hdctools.py .
RUN PACKAGE="servo" python3 setup_hdctools.py bdist_wheel
RUN PACKAGE="usbkm232" python3 setup_hdctools.py bdist_wheel
RUN PACKAGE="servo_mfg" python3 setup_hdctools.py bdist_wheel
RUN PACKAGE="ec3po" python3 setup_hdctools.py bdist_wheel

#####################################################################
FROM clang-builder as uhubctl-builder

RUN git clone https://github.com/mvp/uhubctl
WORKDIR /uhubctl
RUN git checkout "$(git tag -l | egrep '^v[0-9]+\.[0-9]+.[0-9]+$' | sort -V | tail -1)"

COPY --from=libusb-builder /usr/local/include/libusb-1.0/libusb.h /usr/local/include/libusb-1.0/
COPY --from=libusb-builder /libusb/*.pc /usr/lib/pkgconfig/
COPY --from=libusb-builder /usr/local/lib/libusb-1.0.so.?.?.? /usr/local/lib/
COPY --from=libusb-builder /usr/local/lib/libusb-1.0.a /usr/local/lib
RUN make
RUN strip  /uhubctl/uhubctl

######################################################################
FROM debian:bookworm-slim as firmware-installer

RUN apt-get update --no-install-recommends  \
    && apt-get install -y --no-install-recommends  \
         apt-transport-https \
         ca-certificates \
         curl \
         gnupg \
         python3 \
         sudo \
         xz-utils \
    && rm -rf /var/lib/apt/lists/*

RUN echo "deb [signed-by=/usr/share/keyrings/cloud.google.gpg] https://packages.cloud.google.com/apt cloud-sdk main" | sudo tee -a /etc/apt/sources.list.d/google-cloud-sdk.list
RUN curl https://packages.cloud.google.com/apt/doc/apt-key.gpg | gpg --dearmor | sudo tee /usr/share/keyrings/cloud.google.gpg
RUN sudo apt-get update && sudo apt-get install google-cloud-cli

RUN mkdir -p /usr/share/servo_updater/firmware/
WORKDIR /usr/share/servo_updater/firmware/
COPY /servo/dockerfiles/servo_firmware_provision.py servo_firmware_provision.py
RUN python3 servo_firmware_provision.py && rm servo_firmware_provision.py

######################################################################
FROM libftdi as flashrom-builder

WORKDIR /

RUN apt-get update \
    && apt-get install -y \
        meson \
        ninja-build \
        cmake \
        libcmocka-dev \
        libpci-dev

RUN git clone https://chromium.googlesource.com/chromiumos/third_party/flashrom

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
FROM debian:bookworm-slim

# Install libusb.
COPY --from=libusb-builder /usr/local/include/libusb-1.0/libusb.h /usr/local/include/libusb-1.0/
COPY --from=libusb-builder /libusb/*.pc /usr/lib/pkgconfig/
COPY --from=libusb-builder /usr/local/lib/libusb-1.0.so.?.?.? /usr/local/lib/
COPY --from=libusb-builder /usr/local/lib/libusb-1.0.a /usr/local/lib

RUN apt-get update --no-install-recommends \
    && apt-get install -y --no-install-recommends \
        dnsutils \
        fwupd \
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
        python3 \
        python3-mock \
        python3-numpy \
        python3-pexpect \
        python3-protobuf \
        python3-serial \
        python3-pytest \
        python3-pytest-cov \
        python3-pytest-forked \
        python3-pytest-mock \
        python3-pytest-xdist \
        python3-usb \
        python3-requests \
        python3-pip \
        wget \
    && rm -rf /var/lib/apt/lists/* \
    && update-alternatives --set ip6tables /usr/sbin/ip6tables-nft


WORKDIR /hdctools/chromeos/
COPY --from=hdctools-builder /hdctools/chromeos/servod_utils.sh .
WORKDIR /wheels
COPY --from=hdctools-builder /hdctools/dist/* ./
COPY --from=ec-builder /ec/dist/*.whl ./
COPY --from=pigweed-builder /pigweed/dist/*.whl ./
RUN pip3  install  *.whl --break-system-packages
WORKDIR /
RUN rm -rf wheels

# Install servo_firmware.
RUN mkdir -p /usr/share/servo_updater/firmware/
COPY --from=firmware-installer /usr/share/servo_updater/firmware/ /usr/share/servo_updater/firmware/
RUN ln -s /usr/local/share/servo_updater/* /usr/share/servo_updater/

COPY --from=chromiumos_overlays \
    /chromiumos-overlay/dev-embedded/libftdi/files/confs/*.conf \
    /usr/share/libftdi/

# Install genesys hub firmware
RUN mkdir -p /usr/local/genesys
RUN wget https://fwupd.org/downloads/be2c9146ff4cfac5d647376c39ce0b78151e9f1a785a287e93ac3968aff2ed50-GenesysLogic_GL3590_64.17.cab \
    -O /usr/local/genesys/GenesysLogic_GL3590_64.17.cab

# Install ec tools
COPY --from=ec-builder \
    /ec/extra/usb_updater/usb_updater2 \
    /ec/build/host/util/stm32mon \
    /ec/build/host/util/uartupdatetool \
    /ec/build/host/util/iteflash \
    /ec/util/flash_ec \
    /ec/util/uart_stress_tester.py \
    /usr/sbin/

COPY --from=gcstool-builder \
    /ec/extra/usb_updater/gsctool \
    /usr/sbin/

RUN chmod u+x /usr/sbin/* /usr/bin/*

COPY --from=ec-builder \
        /usr/lib/libfmap.so* \
        /usr/lib/libftdi* \
        /usr/lib/

RUN wget https://raw.githubusercontent.com/kward/shflags/master/shflags --output-document /usr/share/misc/shflags
COPY --from=ec-builder /ec/util/openocd/* /usr/share/ec-devutils/
#TODO(b/287265152): Fetch token database from GCS
#COPY --from=ec-builder /ec/tokens.bin /tmp/tokens.bin

COPY --from=hdctools-builder /hdctools/servo/tests/ /hdctools/servo/tests/

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
     /servo/dockerfiles/start_servod.sh \
     /servo/dockerfiles/start_servod_dev.sh \
     /servo/dockerfiles/stop_servod.sh /

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
        python3-pip \
        wget \
    && apt-get autoclean \
    && rm -rf /var/lib/apt/lists/* \
    && rm -rf /usr/local/lib/python*/site-packages/numpy/core/tests \
    && rm -rf /var/cache/debconf \
    && rm -rf /usr/share/doc \
    && rm -rf /usr/share/zoneinfo/

# Required for the name paramter for using .servorc.
ENV SUDO_USER=docker
# Required for the ftdi libraries to be found. ENV does not allow the
# use of command to populate the results, to be less brittle it would
# be nice if the path could be discovered with a command like:
# find / -name libftdii2c.so -exec dirname {} \;
ENV LD_LIBRARY_PATH=/usr/local/lib/python3.11/dist-packages
