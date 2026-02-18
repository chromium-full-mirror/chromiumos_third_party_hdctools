# Copyright 2022 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

FROM debian:trixie AS base

ARG USER
ARG USERID

RUN apt-get -yq update && apt-get install --no-install-recommends -yq \
    apt-transport-https \
    ca-certificates \
    wget \
    gnupg \
    curl \
    gnupg-agent \
    sudo

# Install vscode
RUN wget -qO- https://packages.microsoft.com/keys/microsoft.asc | gpg --dearmor > packages.microsoft.gpg
RUN install -o root -g root -m 644 packages.microsoft.gpg /etc/apt/trusted.gpg.d/
RUN sh -c 'echo "deb [arch=amd64,arm64,armhf signed-by=/etc/apt/trusted.gpg.d/packages.microsoft.gpg] https://packages.microsoft.com/repos/code stable main" > /etc/apt/sources.list.d/vscode.list'
RUN rm -f packages.microsoft.gpg

# Install gcloud
RUN echo "deb [signed-by=/usr/share/keyrings/cloud.google.gpg] \
    https://packages.cloud.google.com/apt cloud-sdk main" | \
    tee -a /etc/apt/sources.list.d/google-cloud-sdk.list
RUN curl https://packages.cloud.google.com/apt/doc/apt-key.gpg | \
    gpg --dearmor | sudo tee /usr/share/keyrings/cloud.google.gpg > /dev/null

RUN curl -fsSL https://download.docker.com/linux/debian/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
RUN chmod a+r /etc/apt/keyrings/docker.gpg

RUN echo \
  "deb [arch="$(dpkg --print-architecture)" signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/debian \
  "$(. /etc/os-release && echo "$VERSION_CODENAME")" stable" | \
  tee /etc/apt/sources.list.d/docker.list > /dev/null

RUN apt-get -yq update && apt-get install --no-install-recommends -yq \
    black \
    code \
    containerd.io \
    docker-buildx-plugin \
    docker-ce \
    docker-ce-cli \
    docker-compose-plugin \
    flake8 \
    git-core \
    google-cloud-sdk \
    isort \
    libasound2 \
    libusb-dev \
    libxshmfence-dev \
    meld \
    pre-commit \
    pylint \
    python3 \
    python3-docker \
    python3-flake8-docstrings \
    python3-pip \
    python3-pytest \
    python3-setuptools \
    python3-usb \
    usbutils \
    vim

# Install chrome
RUN wget https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb
RUN apt install -y ./google-chrome-stable_current_amd64.deb

WORKDIR /hdctools_source

COPY development_environment/entry.sh development_environment/bashrc development_environment/get-source.sh /usr/local/bin/
RUN chmod uog+rx /usr/local/bin/get-source.sh /usr/local/bin/entry.sh

ENV DISPLAY=:0

CMD ["entry.sh"]
