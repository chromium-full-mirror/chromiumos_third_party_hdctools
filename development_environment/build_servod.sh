#!/bin/bash

export DOCKER_BUILDKIT=1
docker build --build-arg=BUILD_ENV=developer -t 127.0.1.1:5000/servod:release -f hdctools/servo/dockerfiles/Dockerfile /hdctools_source
docker push 127.0.1.1:5000/servod:release
