#!/bin/bash

REGISTRY="${1:-127.0.1.1:5000}"
set -x

export DOCKER_BUILDKIT=1
cd /hdctools_source/hdctools

if [ "$2" == "multi" ]
then
    docker buildx create \
	    --use \
	    --name insecure-builder \
	    --buildkitd-flags '--allow-insecure-entitlement network.host --allow-insecure-entitlement security.insecure' | true
    docker buildx build \
	    --platform=linux/arm64,linux/amd64 \
	    --output type=registry,registry.insecure=true,push=true \
	    --allow security.insecure \
	    --allow network.host \
	    -t ${REGISTRY}/servod:release \
	    -f servo/dockerfiles/Dockerfile .
else
     docker build --build-arg=BUILD_ENV=developer -t ${REGISTRY}/servod:dev -f servo/dockerfiles/Dockerfile . \
     && docker push "${REGISTRY}/servod:dev"
fi

cd -

