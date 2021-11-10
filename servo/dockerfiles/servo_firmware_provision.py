# Copyright 2021 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import os
import subprocess


# TODO (anhdle): Update to track servo-firmware ebuild instead of hardcoding.
C2D2_NAME = "c2d2_v2.4.35-f1113c92b"                # servo-firmware-R81-12768.40.0
SERVO_MICRO_NAME = "servo_micro_v2.4.57-ce329f64f"  # servo-firmware-R81-12768.71.0
SERVO_V4_NAME = "servo_v4_v2.4.58-c37246f9c"       # servo-firmware-R81-12768.74.0
SERVO_V4P1_NAME = "servo_v4p1_v2.0.8584+1a7e7e64c"  # Local builds are temporary b/153464312
SWEETBERRY_NAME = "sweetberry_v2.3.7-096c7ee84"     # servo-firmware-R70-11011.14.0

# Prev channel firmware
SERVO_MICRO_NAME_PREV = "servo_micro_v2.4.35-f1113c92b"  # servo-firmware-R81-12768.40.0
SERVO_V4_NAME_PREV = "servo_v4_v2.4.57-ce329f64f"        # servo-firmware-R81-12768.71.0
SERVO_V4P1_NAME_PREV = "servo_v4p1_v2.0.5159-529612865"  # Local builds are temporary b/153464312

MIRROR_PATH = "gs://chromeos-localmirror/distfiles/"

C2D2_FILE = '{}.tar.gz'.format(C2D2_NAME)
SERVO_MICRO_FILE = '{}.tar.xz'.format(SERVO_MICRO_NAME)
SERVO_MICRO_FILE_PREV = '{}.tar.gz'.format(SERVO_MICRO_NAME_PREV)
SERVO_V4_FILE = '{}.tar.xz'.format(SERVO_V4_NAME)
SERVO_V4_FILE_PREV = '{}.tar.xz'.format(SERVO_V4_NAME_PREV)
SERVO_V4P1_FILE = '{}.tar.xz'.format(SERVO_V4P1_NAME)
SERVO_V4P1_FILE_PREV = '{}.tar.xz'.format(SERVO_V4P1_NAME_PREV)
SWEETBERRY_FILE = '{}.tar.gz'.format(SWEETBERRY_NAME)


def create_sym_link(src, dst):
    os.symlink(src, dst)


def download_unpack(path, filename):
    """Download the tarball from Google Cloud storage, untar, clean up.

    Args:
        path (str): path to the gs bucket.
        filename (str): name of the tarball
        dst (str): local folder to download and extract.
    """
    subprocess.check_call(['gsutil', 'cp', path + filename, filename])
    subprocess.check_call(['tar', 'xf',filename])
    os.remove(filename)


def main():
	download_unpack(MIRROR_PATH, C2D2_FILE)
	os.chmod(C2D2_NAME + '.bin', 420)
	create_sym_link(C2D2_NAME + '.bin', 'c2d2.alpha.bin')
	create_sym_link(C2D2_NAME + '.bin', 'c2d2.stable.bin')
	create_sym_link(C2D2_NAME + '.bin', 'c2d2.dev.bin')
	create_sym_link(C2D2_NAME + '.bin', 'c2d2.prev.bin')

	download_unpack(MIRROR_PATH, SERVO_MICRO_FILE)
	download_unpack(MIRROR_PATH, SERVO_MICRO_FILE_PREV)
	os.chmod(SERVO_MICRO_NAME + '.bin', 420)
	os.chmod(SERVO_MICRO_NAME_PREV + '.bin', 420)
	create_sym_link(SERVO_MICRO_NAME + '.bin', 'servo_micro.alpha.bin')
	create_sym_link(SERVO_MICRO_NAME + '.bin', 'servo_micro.stable.bin')
	create_sym_link(SERVO_MICRO_NAME + '.bin', 'servo_micro.dev.bin')
	create_sym_link(SERVO_MICRO_NAME_PREV + '.bin', 'servo_micro.prev.bin')

	download_unpack(MIRROR_PATH, SERVO_V4_FILE)
	download_unpack(MIRROR_PATH, SERVO_V4_FILE_PREV)
	os.chmod(SERVO_V4_NAME + '.bin', 420)
	os.chmod(SERVO_V4_NAME_PREV + '.bin', 420)
	create_sym_link(SERVO_V4_NAME + '.bin', 'servo_v4.alpha.bin')
	create_sym_link(SERVO_V4_NAME + '.bin', 'servo_v4.stable.bin')
	create_sym_link(SERVO_V4_NAME + '.bin', 'servo_v4.dev.bin')
	create_sym_link(SERVO_V4_NAME_PREV + '.bin', 'servo_v4.prev.bin')

	download_unpack(MIRROR_PATH, SERVO_V4P1_FILE)
	download_unpack(MIRROR_PATH, SERVO_V4P1_FILE_PREV)
	os.chmod(SERVO_V4P1_NAME + '.bin', 420)
	os.chmod(SERVO_V4P1_NAME_PREV + '.bin', 420)
	create_sym_link(SERVO_V4P1_NAME + '.bin', 'servo_v4p1.alpha.bin')
	create_sym_link(SERVO_V4P1_NAME + '.bin', 'servo_v4p1.stable.bin')
	create_sym_link(SERVO_V4P1_NAME + '.bin', 'servo_v4p1.dev.bin')
	create_sym_link(SERVO_V4P1_NAME_PREV + '.bin', 'servo_v4p1.prev.bin')

	download_unpack(MIRROR_PATH, SWEETBERRY_FILE)
	os.chmod(SWEETBERRY_NAME + '.bin', 420)
	create_sym_link(SWEETBERRY_NAME + '.bin', 'sweetberry.alpha.bin')
	create_sym_link(SWEETBERRY_NAME + '.bin', 'sweetberry.stable.bin')
	create_sym_link(SWEETBERRY_NAME + '.bin', 'sweetberry.dev.bin')

main()