#!/bin/bash

export DOCKER_BUILDKIT=1
cd /hdctools_source
docker build --build-arg=BUILD_ENV=developer -t 127.0.1.1:5000/servod:release -f hdctools/servo/dockerfiles/Dockerfile .
docker push 127.0.1.1:5000/servod:release
cd -
