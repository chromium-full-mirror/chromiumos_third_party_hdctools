#!/bin/bash
# Copyright 2024 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

# Check if path argument is provided
if [ -z "$1" ]; then
  echo "Error: Please provide the path to the working directory as an argument."
  exit 1
fi

SERVO_BUILD_PATH="$1"

# Extract version from ec_version.h
VERSION=$(grep '#define VERSION' "${SERVO_BUILD_PATH}/ec_version.h" | \
  sed -E 's/#define VERSION "(.*)"/\1/')

# Check if version was extracted successfully
if [ -z "${VERSION}" ]; then
  if [ -z "$2" ]; then
    echo "Can not find ec_version.h file please provide version manually."
    exit 1
  fi
    VERSION="$2"
fi

# Rename ec.bin and cp to working directory
NEW_FILENAME="${VERSION}.bin"
cp "${SERVO_BUILD_PATH}/ec.bin" "${NEW_FILENAME}"

# Compress into tar.xz
ARCHIVE_FILENAME="${VERSION}.tar.xz"
tar cfJ "${ARCHIVE_FILENAME}" "${NEW_FILENAME}"

# Copy archive to cloud bucket and edit access
# NOTE: please run "gcloud auth login" earlier
CLOUD_ARCHIVE_PATH="gs://chromeos-localmirror/distfiles/${ARCHIVE_FILENAME}"
if gsutil cp "${ARCHIVE_FILENAME}" "${CLOUD_ARCHIVE_PATH}" &&
   gsutil acl ch -u allUsers:R "${CLOUD_ARCHIVE_PATH}"; then
    echo "Done! Created ${VERSION}.tar.xz and uploaded to https://pantheon.corp.google.com/storage/browser/chromeos-localmirror/distfiles/${ARCHIVE_FILENAME}"
    echo "Removing local copies!"
    rm "${ARCHIVE_FILENAME}" "${NEW_FILENAME}"
else
    echo "Some issues encountered trying to update file to cloud bucket."
    echo "Generated  ${VERSION}.tar.xz - please try to update it manually to https://pantheon.corp.google.com/storage/browser/chromeos-localmirror/distfiles"
    echo "Then change the access to public via GUI"
fi
