# Copyright 2021 The Chromium OS Authors. All rights reserved.
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
FROM debian:bullseye-slim as clang-builder

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

# This is setup for the most normal case, developers and cloud builds
# to pull the code from the checked in ec repo.
# If you wish to build/test changes to the ec repo as a developer
# uncomment the copy line and comment out the git clone line.
# COPY /ec /ec
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
RUN make utils-host \
    && make -C extra/usb_updater usb_updater2

COPY hdctools/servo/dockerfiles/setup_ec.py .
RUN PACKAGE="ec3po" python3 setup_ec.py bdist_wheel
RUN PACKAGE="ecusb" python3 setup_ec.py bdist_wheel
RUN PACKAGE="servo_updater" python3 setup_ec.py bdist_wheel
RUN PACKAGE="powerlog" python3 setup_ec.py bdist_wheel
RUN PACKAGE="console" python3 setup_ec.py bdist_wheel
RUN PACKAGE="unpack_ftb" python3 setup_ec.py bdist_wheel

RUN curl https://raw.githubusercontent.com/kward/shflags/master/shflags --output /usr/share/misc/shflags

RUN strip /ec/extra/usb_updater/usb_updater2 \
          /ec/build/elm/util/stm32mon \
          /ec/build/elm/util/uartupdatetool \
          /ec/build/elm/util/iteflash

RUN strip --strip-unneeded /usr/lib/libfmap.so* /usr/lib/libftdi*

######################################################################
FROM libftdi as hdctools-developer
COPY hdctools/ hdctools/
FROM libftdi as hdctools-builder

# For cloud build and for developers copying the local source is correct, if
# you need to build from checked in code vs you local source comment out the
# copy command and uncomment the clone command.
COPY hdctools/ hdctools/
#RUN git clone https://chromium.googlesource.com/chromiumos/third_party/hdctools

RUN pip3 install pytest

WORKDIR /hdctools
RUN echo 'HOSTOS_CWARN=' >> 'defs/c-Linux.mk'
RUN make -d
RUN make install

# Setuptools skips nested entry point. Adding custom setup.py to overcome.
COPY /hdctools/servo/dockerfiles/setup_hdctools.py .
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

RUN pip install --upgrade pip && pip3 install gsutil

RUN mkdir -p /usr/share/servo_updater/firmware/
WORKDIR /usr/share/servo_updater/firmware/
COPY /hdctools/servo/dockerfiles/servo_firmware_provision.py servo_firmware_provision.py
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
        bzip2 \
        curl \
        dnsutils \
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
    && rm -rf /var/lib/apt/lists/* \
    && update-alternatives --set ip6tables /usr/sbin/ip6tables-nft

# Install python packages.
COPY /hdctools/servo/dockerfiles/requirements.txt /opt/requirements.txt
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
    /ec/build/elm/util/ectool \
    /ec/build/elm/util/ec_parse_panicinfo \
    /ec/build/elm/util/ec_sb_firmware_update \
    /ec/extra/usb_updater/usb_updater2 \
    /ec/build/elm/util/stm32mon \
    /ec/build/elm/util/uartupdatetool \
    /ec/build/elm/util/iteflash \
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

# Install futility
COPY --from=futility-builder /usr/bin/futility /usr/bin/
RUN chmod 755 /usr/bin/futility
COPY --from=futility-builder /usr/local/lib/x86_64-linux-gnu/libflashrom.so.1.0.0 /usr/lib
RUN ln -s /usr/lib/libflashrom.so.1.0.0 /usr/lib/libflashrom.so.1 && \
    ln -s /usr/lib/libflashrom.so.1.0.0 /usr/lib/libflashrom.so

# Install cbfstool for flashrom and ec.
COPY --from=cbfstool /coreboot-4.14/util/cbfstool/cbfstool /usr/local/bin/
RUN chmod 755 /usr/local/bin/cbfstool

RUN mkdir -p /usr/share/ec-devutils
# Avoid watchtower updating servod, it gets pulled before every start of the
# container, we should not stop/start it in the case a new version is pushed.
LABEL com.centurylinklabs.watchtower.enable="false"

ENV WARN_ONLY_ON_UNKNOWN_ENV="SERVO_FW_ALL_CHANNEL_OK"

COPY /hdctools/servo/dockerfiles/update_servo_firmware.py \
     /hdctools/servo/dockerfiles/start_servod.sh /hdctools/servo/dockerfiles/stop_servod.sh \
     /

# Running sync in the container with no params will crash the host bare metal as all disks
# are mounted, put a script in the place of sync that checks are lease one argument is passed
# if no arguments are passed an error is thrown.
RUN mv /bin/sync /usr/local/bin/real_sync
COPY /hdctools/servo/dockerfiles/sync /bin
RUN chmod 755 /bin/sync

# Try to remove as much as possible to make the container smaller
RUN apt-get remove --purge -y \
        xz-utils \
    && apt-get autoclean \
    && rm -rf /var/lib/apt/lists/* \
    && rm -rf /usr/local/lib/python3.10/site-packages/numpy/core/tests \
    && python -m pip uninstall -y pip \
    && rm -rf /var/cache/debconf \
    && rm -rf /usr/share/doc \
    && rm -rf /usr/share/zoneinfo/
