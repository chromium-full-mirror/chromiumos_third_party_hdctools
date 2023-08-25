#!/bin/bash
export DOCKER_BUILDKIT=1
IMAGE="servod:dev"
set -x
SOURCE=${BASH_SOURCE[0]}
while [ -L "$SOURCE" ]; do # resolve $SOURCE until the file is no longer a symlink
  DIR=$( cd -P "$( dirname "$SOURCE" )" >/dev/null 2>&1 && pwd )
  SOURCE=$(readlink "$SOURCE")
done
DIR=$( cd -P "$DIR/$( dirname "$SOURCE" )" >/dev/null 2>&1 && pwd )

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
	    -f ${DIR}/../servo/dockerfiles/Dockerfile ${DIR}/..
else
     docker build -t ${IMAGE} -f ${DIR}/../servo/dockerfiles/Dockerfile ${DIR}/..
fi
