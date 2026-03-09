# Copyright 2023 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from setuptools import setup


setup(
    name="pw_tokenizer",
    version="1.0",
    author="Pigweed Authors",
    url="https://pigweed.dev/",
    package_dir={"": "pw_tokenizer/py"},
    packages=["pw_tokenizer"],
    description="Pigweed tokenizer",
)
