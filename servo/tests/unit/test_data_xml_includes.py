# Copyright 2025 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import importlib
import os
import unittest
import xml.etree.ElementTree as ET


class TestDataXmlIncludes(unittest.TestCase):
    def test_include_files_exist(self):
        spec = importlib.util.find_spec("servo")
        if spec.origin:
            data_dir = os.path.dirname(spec.origin) + "/data"
        else:
            self.fail("No data directory found to check.")
        xml_files = [f for f in os.listdir(data_dir) if f.endswith(".xml")]

        for xml_file in xml_files:
            xml_path = os.path.join(data_dir, xml_file)
            try:
                tree = ET.parse(xml_path)
                root = tree.getroot()

                for include_tag in root.findall(".//include"):
                    name_tag = include_tag.find("name")
                    if name_tag is not None:
                        included_file = name_tag.text
                        if included_file:
                            included_path = os.path.join(data_dir, included_file)
                            xml_exists = os.path.exists(included_path)
                            py_exists = False
                            if not xml_exists and included_file.endswith(".xml"):
                                py_file = included_file[:-4] + ".py"
                                py_path = os.path.join(data_dir, py_file)
                                py_exists = os.path.exists(py_path)

                            self.assertTrue(
                                xml_exists or py_exists,
                                f"Included file '{included_file}' (or .py version) "
                                f"not found in {xml_file}",
                            )
            except ET.ParseError as e:
                self.fail(f"Error parsing {xml_file}: {e}")


if __name__ == "__main__":
    unittest.main()
