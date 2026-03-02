#!/usr/bin/env python3
# Copyright 2026 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
import sys


def main():
    if len(sys.argv) < 2:
        print("Usage: commit_msg_length.py <commit-msg-file>")
        sys.exit(1)

    msg_file = sys.argv[1]
    try:
        with open(msg_file, "r", encoding="utf-8") as f:
            lines = f.read().splitlines()
    except Exception as e:
        print(f"Error reading commit message: {e}")
        sys.exit(1)

    if not lines:
        sys.exit(0)

    # Strip comments
    lines = [line for line in lines if not line.startswith("#")]
    if not lines:
        sys.exit(0)

    subject = lines[0]
    if len(subject) > 72:
        print(
            f"ERROR: Commit subject line exceeds 72 characters ({len(subject)} chars)."
        )
        print(f"Subject: {subject}")
        print("Please wrap your commit message properly.")
        sys.exit(1)

    if len(lines) > 1 and lines[1].strip() != "":
        print("ERROR: Second line of commit message must be blank.")
        sys.exit(1)

    for i, line in enumerate(lines[2:], start=3):
        # Allow long lines if they are URLs, BUG=, TEST=, Change-Id=
        if len(line) > 72:
            if not any(
                prefix in line
                for prefix in (
                    "http://",
                    "https://",
                    "BUG=",
                    "TEST=",
                    "Change-Id:",
                    "Signed-off-by:",
                    "Reviewed-by:",
                )
            ):
                print(f"ERROR: Commit message line {i} exceeds 72 characters.")
                print(f"Line {i}: {line}")
                sys.exit(1)

    sys.exit(0)


if __name__ == "__main__":
    main()
