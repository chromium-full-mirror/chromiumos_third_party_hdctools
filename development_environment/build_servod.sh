#!/bin/bash

export DOCKER_BUILDKIT=1
IMAGE="servod:dev"
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
	    -t ${IMAGE} \
	    -f servo/dockerfiles/Dockerfile .
else
     docker build -t ${IMAGE} -f servo/dockerfiles/Dockerfile .
fi

cd -

