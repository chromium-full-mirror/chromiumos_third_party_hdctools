# Copyright 2025 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

FROM debian:trixie AS keyboard_build

WORKDIR /build

RUN apt-get update \
    && apt-get install -y \
    avr-libc \
    avrdude \
    binutils-avr \
    dfu-programmer \
    gcc-avr \
    gdb-avr \
    make \
    unzip \
    wget

RUN wget http://www.github.com/abcminiuser/lufa/archive/LUFA-140928.zip
RUN unzip *.zip
RUN ln -s lufa-*/LUFA .
COPY KeyboardSerial ./KeyboardSerial/

WORKDIR /build/KeyboardSerial

RUN make

#######################################################################
FROM scratch AS copytohost

COPY --link --from=keyboard_build /build/KeyboardSerial/Keyboard.hex /
