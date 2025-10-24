# syntax=docker/dockerfile:1.4
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
FROM debian:trixie as clang-builder

RUN apt-get update \
    && apt-get install -y \
    autoconf \
    build-essential \
    equivs \
    clang \
    curl \
    git \
    libssl-dev \
    libtool \
    pkg-config \
    python3 \
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

# Override the libraries we build ourselves, and do it early: no need to mess
# up the library builds by building against distro packages that we don't
# intend to use.
COPY servo/dockerfiles/equivs-control .
RUN equivs-build equivs-control
RUN apt-get install -y ./hdctools-docker-fake_9999-1_all.deb

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

RUN wget https://www.intra2net.com/en/developer/libftdi/download/libftdi1-1.5.tar.bz2 \
    && tar xf libftdi1-1.5.tar.bz2 \
    && rm libftdi1-1.5.tar.bz2


COPY --from=chromiumos_overlays \
    /chromiumos-overlay/dev-embedded/libftdi/files/confs/*.conf \
    /usr/share/libftdi/

RUN apt-get update --no-install-recommends  \
    && apt-get install -y --no-install-recommends  \
    cmake \
    libconfuse-dev \
    && rm -rf /var/lib/apt/lists/*


COPY --from=libusb-builder /usr/local/include/libusb-1.0/libusb.h /usr/local/include/libusb-1.0/
COPY --from=libusb-builder /usr/local/lib/libusb-1.0.a /usr/local/lib
COPY --from=libusb-builder /usr/local/lib/libusb-1.0.so.?.?.? /usr/local/lib/
COPY --from=libusb-builder /libusb/*.pc /usr/lib/pkgconfig/

WORKDIR /libftdi1-1.5

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
RUN PACKAGE="powerlog" python3 setup_ec.py bdist_wheel
RUN PACKAGE="console" python3 setup_ec.py bdist_wheel
RUN PACKAGE="unpack_ftb" python3 setup_ec.py bdist_wheel

RUN strip /ec/extra/usb_updater/usb_updater2 \
    /ec/build/host/util/stm32mon \
    /ec/build/host/util/uartupdatetool \
    /ec/build/host/util/iteflash

RUN strip --strip-unneeded /usr/lib/libfmap.so* /usr/lib/libftdi*

WORKDIR /
RUN tar cvf libs.tar /usr/lib/libfmap.so* /usr/lib/libftdi*

######################################################################
FROM libftdi as pigweed-builder

RUN git clone https://chromium.googlesource.com/chromiumos/third_party/pigweed/pigweed

WORKDIR /pigweed
# TODO(b/371018012): Once pigweed downstreaming is enabled follow
# upstream pigweed
RUN git checkout upstream/main
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
FROM libftdi as hdctools-builder-base

RUN apt-get update \
    && apt-get install -y \
    protobuf-compiler \
    python3-grpc-tools \
    python3-pytest

######################################################################
FROM hdctools-builder-base as hdctools-builder
# For cloud build and for developers copying the local source is correct, if
# you need to build from checked in code vs you local source comment out the
# copy command and uncomment the clone command.
COPY / hdctools/
#RUN git clone https://chromium.googlesource.com/chromiumos/third_party/hdctools

WORKDIR /hdctools
RUN echo 'HOSTOS_CWARN=' >> 'defs/c-Linux.mk'
RUN make -j $(nproc)
RUN make install

WORKDIR /hdctools/servo
RUN python3 setup.py bdist_wheel

#####################################################################
FROM hdctools-builder as hdctools-servo-updater-builder
WORKDIR /hdctools/servo_updater
RUN python3 setup.py bdist_wheel

#####################################################################
FROM hdctools-builder as hdctools-usbkm232-builder

WORKDIR /hdctools/usbkm232
RUN python3 setup.py bdist_wheel

#####################################################################
FROM hdctools-builder as hdctools-ec3po-builder

WORKDIR /hdctools/ec3po
RUN python3 setup.py bdist_wheel

#####################################################################

######################################################################
FROM alpine/git as shflags-builder

WORKDIR /
RUN git clone https://github.com/kward/shflags.git
WORKDIR /shflags
RUN git checkout "$(git tag -l | egrep '^v[0-9]+\.[0-9]+.[0-9]+$' | sort -V | tail -1)"

######################################################################
FROM debian:trixie-slim as firmware-installer

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

COPY --link --from=clang-builder hdctools-docker-fake_9999-1_all.deb /
RUN apt-get install -y /hdctools-docker-fake_9999-1_all.deb

RUN echo "deb [signed-by=/usr/share/keyrings/cloud.google.gpg] https://packages.cloud.google.com/apt cloud-sdk main" | sudo tee -a /etc/apt/sources.list.d/google-cloud-sdk.list
RUN curl https://packages.cloud.google.com/apt/doc/apt-key.gpg | gpg --dearmor | sudo tee /usr/share/keyrings/cloud.google.gpg
RUN sudo apt-get update && sudo apt-get install -y google-cloud-cli

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

RUN apt-get update \
    && apt-get install -y \
    libnss3-dev

# Install vboot.
WORKDIR /
RUN git clone https://chromium.googlesource.com/chromiumos/platform/vboot_reference
WORKDIR /vboot_reference
RUN sed -i 's/%" PRIi64 "/%ld/g' futility/cmd_gbb_utility.c
RUN make && make install

RUN strip /usr/bin/futility

######################################################################
FROM futility-builder as coreboot

WORKDIR /
RUN git clone --depth 1 https://chromium.googlesource.com/chromiumos/third_party/coreboot
RUN cd /coreboot/util/cbfstool && make VBOOT_SOURCE=/vboot_reference
RUN strip /coreboot/util/cbfstool/cbfstool
RUN cd /coreboot/util/ifdtool && make
RUN strip /coreboot/util/ifdtool/ifdtool

######################################################################
FROM debian:trixie-slim as base

COPY --from=clang-builder hdctools-docker-fake_9999-1_all.deb /

RUN apt-get update --no-install-recommends \
    && apt-get install -y --no-install-recommends \
    build-essential \
    dnsutils \
    fwupd \
    gcc \
    iptables \
    iputils-ping \
    kmod \
    libatomic1 \
    libpci-dev \
    lsof \
    make \
    procps \
    python3 \
    python3-backoff \
    python3-mock \
    python3-numpy \
    python3-packaging \
    python3-pexpect \
    python3-pip \
    python3-protobuf \
    python3-pytest \
    python3-pytest-cov \
    python3-pytest-forked \
    python3-pytest-mock \
    python3-pytest-xdist \
    python3-requests \
    python3-serial \
    python3-usb \
    sudo \
    udev \
    usbutils \
    xz-utils \
    wget \
    && rm -rf /var/lib/apt/lists/* \
    && update-alternatives --set ip6tables /usr/sbin/ip6tables-nft \
    && apt-get install -y /hdctools-docker-fake_9999-1_all.deb \
    && rm -f /hdctools-docker-fake_9999-1_all.deb

# Install libusb.
COPY --link --from=libusb-builder /usr/local/include/libusb-1.0/libusb.h /usr/local/include/libusb-1.0/
COPY --link --from=libusb-builder /libusb/*.pc /usr/lib/pkgconfig/
COPY --link --from=libusb-builder /usr/local/lib/libusb-1.0.so.?.?.? /usr/local/lib/
COPY --from=libusb-builder /usr/local/lib/libusb-1.0.a /usr/local/lib

WORKDIR /wheels
COPY --link --from=ec-builder /ec/dist/*.whl ./
COPY --link --from=pigweed-builder /pigweed/dist/*.whl ./
RUN pip3  install  *.whl --break-system-packages
WORKDIR /
RUN rm -rf wheels

# Install servo_firmware.
RUN mkdir -p /usr/share/servo_updater/firmware/
COPY --link --from=firmware-installer /usr/share/servo_updater/firmware/ /usr/share/servo_updater/firmware/

COPY --link --from=chromiumos_overlays \
    /chromiumos-overlay/dev-embedded/libftdi/files/confs/*.conf \
    /usr/share/libftdi/

# Install genesys hub firmware
RUN mkdir -p /usr/local/genesys
RUN wget https://storage.googleapis.com/fwupd-cache/be2c9146ff4cfac5d647376c39ce0b78151e9f1a785a287e93ac3968aff2ed50-GenesysLogic_GL3590_64.17.cab \
    -O /usr/local/genesys/GenesysLogic_GL3590_64.17.cab

# Install ec tools
COPY --link --from=ec-builder \
    /ec/extra/usb_updater/usb_updater2 \
    /ec/build/host/util/stm32mon \
    /ec/build/host/util/uartupdatetool \
    /ec/build/host/util/iteflash \
    /ec/util/flash_ec \
    /ec/util/uart_stress_tester.py \
    /usr/sbin/

COPY --link --from=gcstool-builder \
    /ec/extra/usb_updater/gsctool \
    /usr/sbin/

RUN chmod u+x /usr/sbin/* /usr/bin/*

COPY --link --from=ec-builder libs.tar .
RUN tar xvf libs.tar
RUN rm libs.tar

RUN mkdir -p /usr/share/ec-devutils

COPY --link --from=ec-builder /ec/util/openocd/* /usr/share/ec-devutils/

# Fetch NPCX monitor from GCS
RUN wget https://storage.googleapis.com/chromeos-localmirror/distfiles/cros_ec/npcx_monitor/npcx_monitor-2025.02.11.bin \
    -O /usr/share/ec-devutils/npcx_monitor.bin

RUN mkdir -p /usr/share/cros_ec/tokens
# Fetch EC Token Database from GCS
RUN wget https://storage.googleapis.com/chromeos-localmirror/distfiles/chromeos-ec-token-historical.bin \
    -O /usr/share/cros_ec/tokens/historical.bin



# Install flashrom
COPY --link --from=flashrom-builder /usr/local/sbin/flashrom /usr/local/sbin/
RUN chmod 755 /usr/local/sbin/flashrom

#Install futility
COPY --link --from=futility-builder /usr/bin/futility /usr/bin/
RUN chmod 755 /usr/bin/futility
COPY --from=futility-builder /usr/local/lib/*/libflashrom.so.1.0.0 /usr/lib
RUN ln -s /usr/lib/libflashrom.so.1.0.0 /usr/lib/libflashrom.so.1 && \
    ln -s /usr/lib/libflashrom.so.1.0.0 /usr/lib/libflashrom.so

RUN ln -s /usr/bin/futility /usr/bin/dump_fmap; \
    ln -s /usr/bin/futility /usr/bin/dump_kernel_config; \
    ln -s /usr/bin/futility /usr/bin/gbb_utility; \
    ln -s /usr/bin/futility /usr/bin/vbutil_kernel; \
    ln -s /usr/bin/futility /usr/bin/vbutil_key; \
    ln -s /usr/bin/futility /usr/bin/vbutil_keyblock

# Install cbfstool for flashrom and ec.
COPY --link --from=coreboot /coreboot/util/cbfstool/cbfstool /usr/local/bin/
RUN chmod 755 /usr/local/bin/cbfstool
COPY --link --from=coreboot /coreboot/util/ifdtool/ifdtool /usr/local/bin/
RUN chmod 755 /usr/local/bin/ifdtool

# Install shflags
COPY --link --from=shflags-builder shflags/shflags /usr/share/misc/shflags

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
    make \
    gcc \
    wget \
    && apt-get autoclean \
    && rm -rf /var/lib/apt/lists/* \
    && rm -rf /usr/local/lib/python*/site-packages/numpy/core/tests \
    && rm -rf /var/cache/debconf \
    && rm -rf /usr/share/doc \
    && rm -rf /usr/share/zoneinfo/

######################################################################
FROM base

WORKDIR /hdctools/chromeos/
WORKDIR /wheels
COPY --link --from=hdctools-builder /usr/lib/libftdii2c*.so /usr/lib/
COPY --link --from=hdctools-builder /usr/lib/libftdiuart*.so /usr/lib/
COPY --link --from=hdctools-builder /usr/lib/libftdigpio*.so /usr/lib/
COPY --link --from=hdctools-builder /hdctools/servo/dist/* ./
COPY --link --from=hdctools-servo-updater-builder /hdctools/servo_updater/dist/* ./
COPY --link --from=hdctools-usbkm232-builder /hdctools/usbkm232/dist/* ./
COPY --link --from=hdctools-ec3po-builder /hdctools/ec3po/dist/* ./
RUN pip3  install  *.whl --break-system-packages
WORKDIR /
RUN rm -rf wheels
# ensure that /usr/local/lib is properly known and set up, especially libusb
RUN ldconfig

COPY --link --from=hdctools-builder /hdctools/servo/tests/ /hdctools/servo/tests/
COPY --link --from=hdctools-builder /hdctools/ec3po/tests/ /hdctools/ec3po/tests/
RUN ln -s /usr/local/share/servo_updater/* /usr/share/servo_updater/
