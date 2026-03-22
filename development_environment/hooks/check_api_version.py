#!/usr/bin/env python3
# Copyright 2026 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Pre-commit hook to ensure CORE_API_VERSION is incremented on core changes."""

import re
import subprocess
import sys


def run_cmd(cmd):
    try:
        return subprocess.check_output(
            cmd, shell=True, text=True, stderr=subprocess.DEVNULL
        )
    except subprocess.CalledProcessError:
        return ""


def get_base_branch():
    if len(sys.argv) > 1:
        branch = sys.argv[1]
        if run_cmd(f"git rev-parse --verify {branch}"):
            return branch

    # Try to find the upstream tracking branch of the current branch
    upstream = run_cmd("git rev-parse --abbrev-ref --symbolic-full-name @{u}").strip()
    if upstream and run_cmd(f"git rev-parse --verify {upstream}"):
        return upstream

    # Fallbacks
    remote_branch = (
        run_cmd("git symbolic-ref refs/remotes/origin/HEAD")
        .strip()
        .replace("refs/remotes/", "")
    )
    if remote_branch and run_cmd(f"git rev-parse --verify {remote_branch}"):
        return remote_branch

    for branch in ["cros/main", "origin/main", "m/main"]:
        if run_cmd(f"git rev-parse --verify {branch}"):
            return branch
    return ""


def main():
    base = get_base_branch()
    if not base:
        # If we can't find a base branch, skip the check
        return 0

    merge_base = run_cmd(f"git merge-base {base} HEAD").strip()
    if not merge_base:
        return 0

    # Get files changed relative to base
    changed_files = run_cmd(f"git diff {merge_base} --name-only").splitlines()

    core_changed = any(
        f.startswith("servo/core/") or f.startswith("servo/common/proto/")
        for f in changed_files
    )

    if not core_changed:
        return 0

    # Core files changed. Check versions.
    base_content = run_cmd(f"git show {merge_base}:servo/common/api_version.py")
    match = re.search(r"CORE_API_VERSION\s*=\s*(\d+)", base_content)
    base_version = int(match.group(1)) if match else 0

    try:
        with open("servo/common/api_version.py", "r", encoding="utf-8") as f:
            local_content = f.read()
        match = re.search(r"CORE_API_VERSION\s*=\s*(\d+)", local_content)
        local_version = int(match.group(1)) if match else 0
    except FileNotFoundError:
        local_version = 0

    if local_version <= base_version:
        print(
            "ERROR: You have modified core servod files "
            "(servo/core/ or servo/common/proto/)."
        )
        print("You MUST increment CORE_API_VERSION in servo/common/api_version.py.")
        print(f"Base version: {base_version}, Local version: {local_version}")
        sys.exit(1)

    return 0


if __name__ == "__main__":
    sys.exit(main())
