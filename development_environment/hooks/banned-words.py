#!/usr/bin/env python3
# Copyright 2023 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import base64
import os
import re
import sys
from urllib import request


UNBLOCKED_TERMS_FILE = "unblocked_terms.txt"


def _read_terms_file(terms_file: str):
    """Read list of words from file, skipping comments and blank lines."""
    file_terms = set()
    with open(terms_file, "r", encoding="utf-8") as fh:
        for line in fh.readlines():
            # Allow comment and blank lines.
            line = line.split("#", 1)[0]
            if not line:
                continue
            file_terms.add(line)
    return file_terms


def _read_terms_from_gitiles(url: str):
    """Read list of words from gitiles."""
    response = request.urlopen(url)
    if response.getcode() != 200:
        print("Unable to get bad words list")
        sys.exit(1)
    encoded = response.read()
    lines = base64.b64decode(encoded).split(b"\n")
    keywords = set()
    for line in lines:
        line = line.split(b"#", 1)[0]
        if not line:
            continue
        keywords.add(line.decode("utf-8"))
    return keywords


def _check_keywords_in_file(file_to_check, keywords):
    """Checks there are no blocked keywords in a file being changed."""

    def _check_line(line):
        # Store information about each span matching blocking regex.
        # to match unblocked regex with blocked reg ex match.
        # [{'span':re.span,    - overlap of matching regex in line
        #   'group':re.group,  - matching term
        #   'blocked':bool,    - whether matching is blocked
        #   'keyword':regex,   - block regex
        #  }, ...]
        blocked_span = []
        # Store information about each span matching unblocking regex.
        # [re.span, ...]
        unblocked_span = []

        # Ignore lines that end with nocheck, typically in a comment.
        # This enables devs to bypass this check line by line.
        if line.endswith(" nocheck") or line.endswith(" nocheck */"):
            return False

        for word in keywords:
            for match in re.finditer(word, line, flags=re.I):
                blocked_span.append(
                    {
                        "span": match.span(),
                        "group": match.group(0),
                        "blocked": True,
                        "keyword": word,
                    }
                )

        # Unblock terms that are superset of blocked terms:
        #   blocked := "this.?word"
        #   unblocked := "\.this.?word"
        # "this line is blocked because of this1word"
        # "this line is unblocked because of thenew.this1word"
        #
        for b in blocked_span:
            for ub in unblocked_span:
                if ub[0] <= b["span"][0] and ub[1] >= b["span"][1]:
                    b["blocked"] = False
            if b["blocked"]:
                return f'Matched "{b["group"]}" with regex of "{b["keyword"]}"'
        return False

    matches = []
    if file_to_check:
        try:
            with open(file_to_check, "r", encoding="utf-8") as fh:
                for line in fh.readlines():
                    result = _check_line(line.strip())
                    if result:
                        matches.append((file_to_check, result))
        except UnicodeDecodeError:
            pass

    if matches:
        for error_file, error in matches:
            print("File: %s Error: %s" % (error_file, error))
        raise sys.exit(1)


def main():
    keywords = _read_terms_from_gitiles(
        (
            "https://chromium.googlesource.com/chromiumos/"
            "repohooks/+/refs/heads/main/blocked_terms.txt?format=TEXT"
        )
    )
    for filename in sys.argv:
        if os.path.isfile(filename):
            _check_keywords_in_file(filename, keywords=keywords)


if __name__ == "__main__":
    main()
