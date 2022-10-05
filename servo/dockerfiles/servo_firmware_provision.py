# Copyright 2021 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import os
import subprocess


# TODO (anhdle): Update to track servo-firmware ebuild instead of hardcoding.
# stable channel firmware
C2D2_NAME="c2d2_v2.4.73-d771c18ba9"                # servo-firmware-R81-12768.40.0
SERVO_MICRO_NAME="servo_micro_v2.4.73-d771c18ba9"  # servo-firmware-R81-12768.71.0
SERVO_V4_NAME="servo_v4_v2.4.58-c37246f9c"         # servo-firmware-R81-12768.74.0
SERVO_V4P1_NAME="servo_v4p1_v2.0.8584+1a7e7e64c"   # Local builds are temporary b/153464312
SWEETBERRY_NAME="sweetberry_v2.3.7-096c7ee84"      # servo-firmware-R70-11011.14.0

# Prev channel firmware
C2D2_NAME_PREV="c2d2_v2.4.35-f1113c92b"                # servo-firmware-R81-12768.40.0
SERVO_MICRO_NAME_PREV="servo_micro_v2.4.57-ce329f64f"  # servo-firmware-R81-12768.40.0
SERVO_V4_NAME_PREV="servo_v4_v2.4.57-ce329f64f"        # servo-firmware-R81-12768.71.0
SERVO_V4P1_NAME_PREV="servo_v4p1_v2.0.7721-8af602eee"  # Local builds are temporary b/153464312

# Dev channel firmware
SERVO_V4P1_NAME_DEV="servo_v4p1_v2.0.18563-55348847f"  # EC ToT from 09/07/2022
C2D2_NAME_DEV="c2d2_v2.4.73-d771c18ba9"                # servo-firmware-R81-12768.151.0
SERVO_MICRO_NAME_DEV="servo_micro_v2.4.73-d771c18ba9"  # servo-firmware-R81-12768.151.0

# Alpha channel firmware
C2D2_NAME_ALPHA="c2d2_v2.0.18040-0fa6cb3063"                # R106-15042.0.0 build
SERVO_MICRO_NAME_ALPHA="servo_micro_v2.0.18040-0fa6cb3063"  # R106-15042.0.0 build
SERVO_V4P1_NAME_ALPHA="servo_v4p1_v2.0.13477-1c6bb5adb"     # R103-14703.0.0 build

MIRROR_PATH = "gs://chromeos-localmirror/distfiles/"

# Temporary solution to the different file extensions
GZ_FILES = [C2D2_NAME_PREV, SWEETBERRY_NAME]

# Sets the paths for the shared binaries.
SERVO_V4_NAME_ALPHA = SERVO_V4_NAME
SERVO_V4_NAME_DEV = SERVO_V4_NAME
SWEETBERRY_NAME_ALPHA = SWEETBERRY_NAME
SWEETBERRY_NAME_DEV = SWEETBERRY_NAME
SWEETBERRY_NAME_PREV = SWEETBERRY_NAME

ALL_IMAGES = [
    ('c2d2.alpha', C2D2_NAME_ALPHA),
    ('c2d2.dev', C2D2_NAME_DEV),
    ('c2d2.prev', C2D2_NAME_PREV),
    ('c2d2.stable', C2D2_NAME),
    ('servo_micro.alpha', SERVO_MICRO_NAME_ALPHA),
    ('servo_micro.dev', SERVO_MICRO_NAME_DEV),
    ('servo_micro.prev', SERVO_MICRO_NAME_PREV),
    ('servo_micro.stable', SERVO_MICRO_NAME),
    ('servo_v4.alpha', SERVO_V4_NAME_ALPHA),
    ('servo_v4.dev', SERVO_V4_NAME_DEV),
    ('servo_v4.prev', SERVO_V4_NAME_PREV),
    ('servo_v4.stable', SERVO_V4_NAME),
    ('servo_v4p1.alpha', SERVO_V4P1_NAME_ALPHA),
    ('servo_v4p1.dev', SERVO_V4P1_NAME_DEV),
    ('servo_v4p1.prev', SERVO_V4P1_NAME_PREV),
    ('servo_v4p1.stable', SERVO_V4P1_NAME),
    ('sweetberry.alpha', SWEETBERRY_NAME_ALPHA),
    ('sweetberry.dev', SWEETBERRY_NAME_DEV),
    ('sweetberry.prev', SWEETBERRY_NAME_PREV),
    ('sweetberry.stable', SWEETBERRY_NAME),
]

def create_sym_link(src, dst):
    """ Creates the symbolic link. """
    os.symlink(src, dst)


def download_unpack(path, base_name):
    """Download the tarball from Google Cloud storage, untar, clean up.

    Args:
        path (str): path to the gs bucket.
        base_name (str): Base name of the tarball and binary
        dst (str): local folder to download and extract.
    """
    tar_name = '{}.tar.xz'.format(base_name)
    bin_name = '{}.bin'.format(base_name)
    # All files have a 'xz' extension except for a few legacy ones which
    # have yet to be migrated or obsoleted.
    if base_name in GZ_FILES:
        tar_name = '{}.tar.gz'.format(base_name)
    subprocess.check_call(['gsutil', 'cp', path + tar_name, tar_name])
    subprocess.check_call(['tar', '--no-same-owner', '-xf', tar_name])
    os.remove(tar_name)
    os.chmod(bin_name, 420)

def main():
    """ Downloads the images and creates the required links. """
    # Find each unique file
    tar_files = set([x[1] for x in ALL_IMAGES])
    for tar in tar_files:
        download_unpack(MIRROR_PATH, tar)
    # Create the Symlinks.
    for image in ALL_IMAGES:
        sym_name = '{}.bin'.format(image[0])
        bin_name = '{}.bin'.format(image[1])
        create_sym_link(bin_name, sym_name)

main()
