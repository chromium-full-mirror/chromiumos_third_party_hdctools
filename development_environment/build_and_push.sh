#!/bin/bash
# Copyright 2026 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
# Builds the servod Docker image, tags it, and pushes it to the Artifact Registry.

set -e

FULL_IMAGE_NAME="us-docker.pkg.dev/chromeos-hw-tools-dev/servod-scratch/servod:haddowk"
LOCAL_TAG="servod:dev"

cd "$(dirname "$0")/.." || exit 1

echo "Building local image: $LOCAL_TAG"
./scripts/build-servod

echo "Tagging image as: $FULL_IMAGE_NAME"
docker tag "$LOCAL_TAG" "$FULL_IMAGE_NAME"

echo "Pushing image: $FULL_IMAGE_NAME"
docker push "$FULL_IMAGE_NAME"

echo "Build and push complete."
