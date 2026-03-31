# Copyright 2021 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import os
import subprocess


# TODO (anhdle): Update to track servo-firmware ebuild instead of hardcoding.
# stable channel firmware
C2D2_NAME = "c2d2_v2.4.82-dbed085877"  # servo branch builder 05/30/2024
SERVO_MICRO_NAME = "servo_micro_v2.4.85-0480cc7379"  # servo branch builder 03/04/2026
SERVO_V4_NAME = "servo_v4_v2.4.83-5e9611ca0c"  # servo branch builder 08/28/24
SERVO_V4P1_NAME = "servo_v4p1_v2.0.29298-4d4a4e980"  # EC ToT from 23/09/2025
SWEETBERRY_NAME = "sweetberry_v2.4.76-01f828e3a6"  # servo-firmware-R81-12768.204.0

# Prev channel firmware
C2D2_NAME_PREV = "c2d2_v2.4.73-d771c18ba9"  # servo-firmware-R81-12768.40.0
SERVO_MICRO_NAME_PREV = (
    "servo_micro_v2.4.82-dbed085877"  # servo branch builder 05/30/2024
)
SERVO_V4_NAME_PREV = "servo_v4_v2.4.58-c37246f9c"  # servo-firmware-R81-12768.74.0
SERVO_V4P1_NAME_PREV = "servo_v4p1_v2.0.27354-3eeb06336"  # EC ToT from 01/27/2025
SWEETBERRY_NAME_PREV = "sweetberry_v2.3.7-096c7ee84"  # servo-firmware-R70-11011.14.0

# Dev channel firmware
SERVO_MICRO_NAME_DEV = (
    "servo_micro_v2.4.85-0480cc7379"  # servo branch builder 03/04/2026
)

# Alpha channel firmware
SERVO_V4P1_NAME_ALPHA = "servo_v4p1_v2.0.29601-4fd1021ab"  # EC Legacy from 12/12/2025

MIRROR_PATH = "gs://chromeos-localmirror/distfiles/"

# Temporary solution to the different file extensions
GZ_FILES = [SWEETBERRY_NAME_PREV]

# Sets the paths for the shared binaries.
SERVO_V4_NAME_ALPHA = SERVO_V4_NAME
SERVO_V4_NAME_DEV = SERVO_V4_NAME
SERVO_V4P1_NAME_DEV = SERVO_V4P1_NAME
SWEETBERRY_NAME_ALPHA = SWEETBERRY_NAME
SWEETBERRY_NAME_DEV = SWEETBERRY_NAME

ALL_IMAGES = [
    ("c2d2.alpha", C2D2_NAME),
    ("c2d2.dev", C2D2_NAME),
    ("c2d2.prev", C2D2_NAME_PREV),
    ("c2d2.stable", C2D2_NAME),
    ("servo_micro.alpha", SERVO_MICRO_NAME),
    ("servo_micro.dev", SERVO_MICRO_NAME_DEV),
    ("servo_micro.prev", SERVO_MICRO_NAME_PREV),
    ("servo_micro.stable", SERVO_MICRO_NAME),
    ("servo_v4.alpha", SERVO_V4_NAME_ALPHA),
    ("servo_v4.dev", SERVO_V4_NAME_DEV),
    ("servo_v4.prev", SERVO_V4_NAME_PREV),
    ("servo_v4.stable", SERVO_V4_NAME),
    ("servo_v4p1.alpha", SERVO_V4P1_NAME_ALPHA),
    ("servo_v4p1.dev", SERVO_V4P1_NAME_DEV),
    ("servo_v4p1.prev", SERVO_V4P1_NAME_PREV),
    ("servo_v4p1.stable", SERVO_V4P1_NAME),
    ("sweetberry.alpha", SWEETBERRY_NAME_ALPHA),
    ("sweetberry.dev", SWEETBERRY_NAME_DEV),
    ("sweetberry.prev", SWEETBERRY_NAME_PREV),
    ("sweetberry.stable", SWEETBERRY_NAME),
]


def create_sym_link(src, dst):
    """Creates the symbolic link."""
    try:
        os.symlink(src, dst)
    except FileExistsError:
        print(dst, "symlink already exists. Update it to ", src)
        os.unlink(dst)
        os.symlink(src, dst)


def download_unpack(path, tar_files):
    """Download the tarball from Google Cloud storage, untar, clean up.

    Args:
        path (str): path to the gs bucket.
        tar_files (list): List of base names of the ""tarball"" and binary
    """
    tar_bin_mapping = {}
    for base_name in tar_files:
        tar_name = "{}.tar.xz".format(base_name)
        bin_name = "{}.bin".format(base_name)
        # All files have a 'xz' extension except for a few legacy ones which
        # have yet to be migrated or obsoleted.
        if base_name in GZ_FILES:
            tar_name = "{}.tar.gz".format(base_name)

        tar_bin_mapping[tar_name] = bin_name

    files_to_copy = [path + tar_name for tar_name in list(tar_bin_mapping.keys())]

    subprocess.check_call(["gsutil", "-m", "cp"] + files_to_copy + ["."])
    for tar_name, bin_name in tar_bin_mapping.items():
        subprocess.check_call(["tar", "--no-same-owner", "-xf", tar_name])
        os.remove(tar_name)
        os.chmod(bin_name, 420)


def main():
    """Downloads the images and creates the required links."""
    # Find each unique file
    tar_files = set([x[1] for x in ALL_IMAGES])
    download_unpack(MIRROR_PATH, tar_files)
    # Create the Symlinks.
    for image in ALL_IMAGES:
        sym_name = "{}.bin".format(image[0])
        bin_name = "{}.bin".format(image[1])
        create_sym_link(bin_name, sym_name)


main()
