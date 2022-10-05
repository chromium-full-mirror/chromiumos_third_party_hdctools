# Copyright 2022 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

FROM debian:bullseye as base

ARG USER
ARG USERID

RUN apt-get -yq update && apt-get install --no-install-recommends -yq \
    apt-transport-https \
    ca-certificates \
    wget \
    gnupg \
    curl \
    gnupg-agent

# Install vscode
RUN wget -qO- https://packages.microsoft.com/keys/microsoft.asc | gpg --dearmor > packages.microsoft.gpg
RUN install -o root -g root -m 644 packages.microsoft.gpg /etc/apt/trusted.gpg.d/
RUN sh -c 'echo "deb [arch=amd64,arm64,armhf signed-by=/etc/apt/trusted.gpg.d/packages.microsoft.gpg] https://packages.microsoft.com/repos/code stable main" > /etc/apt/sources.list.d/vscode.list'
RUN rm -f packages.microsoft.gpg

# Install gcloud
RUN echo "deb [signed-by=/usr/share/keyrings/cloud.google.gpg] \
    https://packages.cloud.google.com/apt cloud-sdk main" | \
    tee -a /etc/apt/sources.list.d/google-cloud-sdk.list
RUN curl https://packages.cloud.google.com/apt/doc/apt-key.gpg |\
    apt-key --keyring /usr/share/keyrings/cloud.google.gpg add -



RUN apt-get -yq update && apt-get install --no-install-recommends -yq \
    git-core \
    google-cloud-sdk \
    python3 \
    python3-pip \
    python3-setuptools \
    software-properties-common \
    sudo \
    vim \
    code \
    libasound2 \
    libusb-dev \
    libxshmfence-dev

# Install chrome
RUN wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub |\
    apt-key add -
RUN sh -c 'echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ \
    stable main" >> /etc/apt/sources.list.d/google.list'
RUN apt-get -yq update && apt-get install -yq google-chrome-stable

RUN update-alternatives --install /usr/bin/python python /usr/bin/python3 1

# Install docker
RUN curl -fsSL https://get.docker.com -o get-docker.sh
RUN bash ./get-docker.sh

COPY requirements.txt ./
RUN python3 -m pip install -U pip && python3 -m pip install --no-cache-dir -r \
    requirements.txt

WORKDIR /hdctools_source

COPY entry.sh get_source.sh build_servod.sh start_servod.py /usr/local/bin/
RUN chmod uog+rx /usr/local/bin/get_source.sh /usr/local/bin/entry.sh /usr/local/bin/build_servod.sh \
  /usr/local/bin/start_servod.py

RUN adduser --gecos "" --disabled-password --uid ${USERID} ${USER}

RUN echo "$USER ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers

RUN chown -R $USER /hdctools_source
RUN chmod u+rwx /hdctools_source

ENV DISPLAY=:0
USER $USER

CMD ["entry.sh"]
