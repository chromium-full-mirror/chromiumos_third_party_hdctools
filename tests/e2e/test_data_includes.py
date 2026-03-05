# Copyright 2025 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""End-to-end tests for data file include directives."""

import glob
import os
import unittest
import xml.etree.ElementTree as ET

from servo.core import servod


SERVO_DATA_DIR = "data"


class TestDataIncludes(unittest.TestCase):
    """Test that all include directives in servo/data files are valid."""

    def test_include_directives(self):
        """Verify that all <include> href values point to existing files."""

        install_dir = os.path.dirname(servod.__file__)

        data_files = glob.glob(os.path.join(install_dir, SERVO_DATA_DIR, "*.xml"))

        for data_file in data_files:
            try:
                tree = ET.parse(data_file)
                root = tree.getroot()
            except ET.ParseError as e:
                self.fail(f"Error parsing XML file {data_file}: {e}")
                continue

            for include_tag in root.findall(".//include"):
                include_name_tag = include_tag.find("name")
                if include_name_tag is None:
                    self.fail(
                        (
                            "Found <include> tag with no name attribute in "
                            f"{os.path.basename(data_file)}"
                        )
                    )
                include_name = include_name_tag.text
                if include_name:
                    file_name = os.path.join(install_dir, SERVO_DATA_DIR, include_name)
                    self.assertIn(
                        file_name,
                        data_files,
                        f"Include file '{include_name}' not found in {SERVO_DATA_DIR} "
                        f"(referenced in {os.path.basename(data_file)})",
                    )
                else:
                    self.fail(
                        (
                            "Found <include> tag with no text in the name attribute in "
                            f"{os.path.basename(data_file)}"
                        )
                    )


if __name__ == "__main__":
    unittest.main()
