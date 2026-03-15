#!/usr/bin/env python3
# Copyright 2026 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Standalone validator for servo XML configs."""

import argparse
import logging
import sys

from servo.common.config.system_config import SystemConfig


def main():
    parser = argparse.ArgumentParser(description="Lint servo XML files.")
    parser.add_argument("files", nargs="+", help="XML files to lint")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger("servo_config_lint")

    has_errors = False
    for f in args.files:
        scfg = SystemConfig()
        try:
            scfg.add_cfg_file("", f)

            for control in scfg.get_all_controls():
                scfg.lookup_control_params(control)
            logger.info("PASS: %s", f)
        except Exception as e:
            logger.error("FAIL: %s - %s", f, e)
            has_errors = True

    if has_errors:
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()
