# syntax=docker/dockerfile:1.4
# Copyright 2025 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

ARG BUILDER_BASE_IMG=us-docker.pkg.dev/chromeos-hw-tools/servod/servod-builder-base:latest
ARG BASE_IMG=us-docker.pkg.dev/chromeos-hw-tools/servod/servod-base:latest

FROM ${BUILDER_BASE_IMG} as hdctools-builder
# For cloud build and for developers copying the local source is correct, if
# you need to build from checked in code vs you local source comment out the
# copy command and uncomment the clone command.
COPY / hdctools/
#RUN git clone https://chromium.googlesource.com/chromiumos/third_party/hdctools

WORKDIR /hdctools
RUN echo 'HOSTOS_CWARN=' >> 'defs/c-Linux.mk'
RUN HDCTOOLS_DIR=/hdctools make -j$(nproc)
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
FROM hdctools-builder as hdctools-measurement-tools-builder
WORKDIR /hdctools/measurement_tools
RUN python3 setup.py bdist_wheel

#####################################################################
FROM hdctools-builder as hdctools-ec3po-builder
WORKDIR /hdctools/ec3po
RUN python3 setup.py bdist_wheel


#####################################################################
FROM python:3.13-slim-trixie as image-downloader-builder
RUN apt-get update \
    && apt-get install -y --no-install-recommends git \
    && pip3 install setuptools wheel --break-system-packages \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /
RUN git clone https://chromium.googlesource.com/chromiumos/platform/labstation
WORKDIR /labstation/image_downloader
RUN python3 setup.py bdist_wheel

######################################################################
FROM ${BASE_IMG}
RUN apt-get update && apt-get install -y --no-install-recommends sudo && rm -rf /var/lib/apt/lists/*


WORKDIR /hdctools/chromeos/
WORKDIR /wheels
COPY --link --from=hdctools-builder /usr/lib/libftdii2c*.so /usr/lib/
COPY --link --from=hdctools-builder /usr/lib/libftdiuart*.so /usr/lib/
COPY --link --from=hdctools-builder /usr/lib/libftdigpio*.so /usr/lib/
COPY --link --from=hdctools-builder /hdctools/servo/dist/* ./
COPY --link --from=hdctools-servo-updater-builder /hdctools/servo_updater/dist/* ./
COPY --link --from=hdctools-measurement-tools-builder /hdctools/measurement_tools/dist/* ./
COPY --link --from=hdctools-ec3po-builder /hdctools/ec3po/dist/* ./
COPY --link --from=hdctools-usbkm232-builder /hdctools/usbkm232/dist/* ./
COPY --link --from=image-downloader-builder /labstation/image_downloader/dist/* ./
RUN pip3  install  *.whl --break-system-packages
WORKDIR /
RUN rm -rf wheels
# ensure that /usr/local/lib is properly known and set up, especially libusb
RUN ldconfig

RUN ln -s /usr/local/share/servo_updater/* /usr/share/servo_updater/

RUN apt-get remove --purge -y \
    python3-pip \
    python3-mypy \
    pylint \
    && apt-get autoclean
