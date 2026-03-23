# Copyright 2018 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
# pylint: disable=line-too-long
# pylint: disable=invalid-name

"""Unit tests for SystemConfig."""

import os
import tempfile
import unittest
from unittest import mock

from servo.common.config import system_config
from tests.unit import syscfg_atlas


def _testdata_path(filename):
    """Find a testdata/test_system_config/ file path.

    Args:
      filename: str

    Returns:
      str: absolute path
    """
    return os.path.join(
        os.path.dirname(__file__), "testdata", "test_system_config", filename
    )


class SystemConfig(system_config.SystemConfig):
    """SystemConfig subclass that finds testdata configs."""

    def find_cfg_file(self, filename):
        """Find testdata config files.

        Args:
          filename: str

        Returns:
          None or str: absolute path, or None if the file does not exist in testdata
        """
        filepath = _testdata_path(filename)
        if os.path.isfile(filepath):
            return filepath
        return None


class TestSystemConfig(unittest.TestCase):
    """Unittests for SystemConfig class behavior."""

    # ALLOWABLE_INPUT_TYPES is defined in system_config module

    def setUp(self):
        """Set up a SystemConfig object to use. Cache module values."""
        super().setUp()
        self.syscfg = SystemConfig()
        self.ALLOWABLE_INPUT_TYPES = system_config.ALLOWABLE_INPUT_TYPES

    def tearDown(self):
        """Restore module values."""
        system_config.ALLOWABLE_INPUT_TYPES = self.ALLOWABLE_INPUT_TYPES
        super().tearDown()

    def _AddMap(self, map_name, params):
        """Helper to add a map to the SystemConfig."""
        self.syscfg.syscfg_dict["map"][map_name] = {"map_params": params}

    def _AddNAControl(self, name, extra_params=None):
        """Helper to add an 'N/A' control to the SystemConfig.

        Add control |name| with some default params:
          - drv: na
          - interface: na

        Args:
          name: control name
          extra_params: dict of extra parameters to add
        """
        if extra_params is None:
            extra_params = {}
        base_params = {"drv": "na", "interface": "na"}
        base_params.update(extra_params)
        control_entry = {
            "doc": "",
            "get_params": base_params,
            "set_params": base_params,
        }
        self.syscfg.syscfg_dict[system_config.CONTROL_TAG][name] = control_entry

    def test_ResolveValStandardInt(self):
        """A string containing an int gets returned as an int."""
        input_str = "1"
        # Empty dictionary is passing empty params.
        self.assertEqual(int(input_str), self.syscfg.resolve_val({}, input_str))

    def test_ResolveValStandardFloat(self):
        """A string containing a float gets returned as a float."""
        input_str = "1.1"
        # Empty dictionary is passing empty params.
        self.assertEqual(float(input_str), self.syscfg.resolve_val({}, input_str))

    def test_ResolveValMappedIntNotUsingMap(self):
        """A mapped control allows for raw input when the map is not used."""
        map_key = "mapped_int"
        map_val = "1"
        map_name = "sample_map"
        map_params = {map_key: map_val}
        self._AddMap(map_name, map_params)
        # These are the params from the control using the map. In this case they
        # need to include the map name.
        control_params = {"map": map_name}
        # The control is being set with 7, a raw input that is valid & does not
        # use the map.
        self.assertEqual(7, self.syscfg.resolve_val(control_params, 7))

    def test_ResolveValMappedInt(self):
        """A mapped integer value gets returned as its mapped integer value."""
        map_key = "mapped_int"
        map_val = "1"
        map_name = "sample_map"
        map_params = {map_key: map_val}
        self._AddMap(map_name, map_params)
        # These are the params from the control using the map. In this case they
        # need to include the map name.
        control_params = {"map": map_name}
        self.assertEqual(int(map_val), self.syscfg.resolve_val(control_params, map_key))

    def test_ResolveValMappedFloat(self):
        """A mapped float value gets returned as its mapped float value."""
        map_key = "mapped_float"
        map_val = "1.1"
        map_name = "sample_map"
        map_params = {map_key: map_val}
        self._AddMap(map_name, map_params)
        # These are the params from the control using the map. In this case they
        # need to include the map name.
        control_params = {"map": map_name}
        self.assertEqual(
            float(map_val), self.syscfg.resolve_val(control_params, map_key)
        )

    def test_ResolveValMapNonExistent(self):
        """A non-existent map raises a SystemConfigError."""
        fake_map_name = "fake_map"
        control_params = {"map": fake_map_name}
        with self.assertRaisesRegex(
            system_config.SystemConfigError, "Map %s isn't defined" % (fake_map_name,)
        ):
            # 'random_key' passed as key as the key does not matter for this test.
            self.syscfg.resolve_val(control_params, "random_key")

    def test_ResolveValMapKeyNonExistent(self):
        """A non-existent map key raises a SystemConfigError."""
        map_key = "mapped_float"
        map_val = "1.1"
        map_name = "sample_map"
        map_params = {map_key: map_val}
        self._AddMap(map_name, map_params)
        fake_map_key = "fake_mapped_float"
        # These are the params from the control using the map. In this case they
        # need to include the map name.
        control_params = {"map": map_name}
        with self.assertRaisesRegex(
            system_config.SystemConfigError,
            "Invalid input %r.*valid map key for '%s'" % (fake_map_key, map_name),
        ):
            self.syscfg.resolve_val(control_params, fake_map_key)

    def test_ResolveValInputType(self):
        """Each input type in |ALLOWABLE_INPUT_TYPES| gets returned properly."""
        # The input types are str, float, and int. Sample is int which can be all
        # 3
        raw_input_str = "1"
        # in setUp, ALLOWABLE_INPUT_TYPES get cached in self.
        for input_type, transform in self.ALLOWABLE_INPUT_TYPES.items():
            # These are the params from the control using the map. In this case they
            # need to include the input type.
            control_params = {"input_type": input_type}
            resolved_val = self.syscfg.resolve_val(control_params, raw_input_str)
            expected_resolved_val = transform(raw_input_str)
            # Ensure they have the same value.
            self.assertEqual(expected_resolved_val, resolved_val)
            # Ensure they have the same type.
            self.assertEqual(type(expected_resolved_val), type(resolved_val))

    def test_ResolveValInputTypeInvalid(self):
        """Invalid input_type does not raise an error, does normal conversion."""
        system_config.ALLOWABLE_INPUT_TYPES = {}
        control_params = {"input_type": "int"}
        input_val = expected_resolved_val = 1
        # Casting to string to verify that it does normal flow of converting to int.
        resolved_val = self.syscfg.resolve_val(control_params, str(input_val))
        # Ensure they have the same value.
        self.assertEqual(expected_resolved_val, resolved_val)
        # Ensure they have the same type.
        self.assertEqual(type(expected_resolved_val), type(resolved_val))

    def test_ResolveValMappedInputType(self):
        """A mapped value will also be transformed to the proper input type."""
        map_key = "mapped_int"
        map_val = "1"
        map_name = "sample_map"
        map_params = {map_key: map_val}
        self._AddMap(map_name, map_params)
        # These are the params from the control using the map. In this case they
        # need to include the map name, and the input_type.
        control_params = {"map": map_name, "input_type": "float"}
        expected_resolved_val = float(map_val)
        # First, the |map_key| is converted to |map_val| i.e. '1'.
        # Second, input_type 'float' means resolve returns float('1')
        resolved_val = self.syscfg.resolve_val(control_params, map_key)
        # Ensure they have the same value.
        self.assertEqual(expected_resolved_val, resolved_val)
        # Ensure they have the same type.
        self.assertEqual(type(expected_resolved_val), type(resolved_val))

    def test_TagsForTaggedControl(self):
        """Multiple tagged controls will be found using their tag."""
        tagged_controls = ["test1", "test2", "test3"]
        tag = "testtag"
        for control in tagged_controls:
            # Pass the tag in as extra params
            self._AddNAControl(control, {"tags": tag})
        self.syscfg.finalize()
        found_tagged_controls = self.syscfg.get_controls_for_tag(tag)
        # Assert that the same controls are found that were fed in.
        assert sorted(found_tagged_controls) == sorted(tagged_controls)

    def test_MultipleTagsForTaggedControl(self):
        """Multiple tagged controls will be found using all their tag."""
        tagged_controls = ["test1", "test2", "test3"]
        tags = "testtag, testtag2"
        for control in tagged_controls:
            self._AddNAControl(control, {"tags": tags})
        self.syscfg.finalize()
        # Split tags into individual tags using helper.
        for tag in self.syscfg.tag_string_to_tags(tags):
            found_tagged_controls = self.syscfg.get_controls_for_tag(tag)
            # Assert that the same controls are found that were fed in.
            assert sorted(found_tagged_controls) == sorted(tagged_controls)

    def test_TagUnknown(self):
        """System returns an empty list if the tag is unknown."""
        tagged_controls = ["test1", "test2", "test3"]
        tag = "testtag"
        for control in tagged_controls:
            # Pass the tag in as extra params
            self._AddNAControl(control, {"tags": tag})
        self.syscfg.finalize()
        unknown_tag = "unknown"
        found_tagged_controls = self.syscfg.get_controls_for_tag(unknown_tag)
        # Assert that no controls were found.
        assert not found_tagged_controls

    def _LoadConfigs(self, servo_type, board, model):
        overlay_file, _unused = self.syscfg.get_board_model_config(
            board=board, model=model
        )
        self.assertTrue(servo_type)
        self.assertTrue(overlay_file)
        self.syscfg.add_cfg_file(servo_type, servo_type + ".xml")
        self.syscfg.add_cfg_file(servo_type, overlay_file)
        self.syscfg.finalize()

    def compare_dict(self, d1, d2, key_path):
        """Compare two dicts."""
        for key in d1.keys():
            if key in d2:
                if isinstance(d1[key], dict) and isinstance(d2[key], dict):
                    self.compare_dict(d1[key], d2[key], f"{key_path}.{key}")
                else:
                    assert d1[key] == d2[key], key_path
            else:
                assert False, f"Missing key {key_path}.{key}"
        for key in d2.keys():
            if not key in d1:
                assert False, f"Extra key {key_path}.{key}"

    def test_LoadValidConfigs(self):
        """Tests that a real-world set of configs load successfully."""
        self._LoadConfigs("servo_micro", "atlas", "atlas")
        self.compare_dict(syscfg_atlas.syscfg_dict, self.syscfg.syscfg_dict, "root")

    def test_MissingDrvConfigs(self):
        """Tests that a control with missing drv= is an error."""
        with self.assertRaises(system_config.SystemConfigError):
            self._LoadConfigs("servo_micro", "atlas", "missingdrv")

    def test_ClobberConflict0Configs(self):
        """Tests that a control with conflicting clobber_ok is an error."""
        with self.assertRaises(system_config.SystemConfigError):
            self._LoadConfigs("servo_micro", "atlas", "clobberconflict0")

    def test_ClobberConflict1Configs(self):
        """Tests that a control with conflicting clobber_ok is an error."""
        with self.assertRaises(system_config.SystemConfigError):
            self._LoadConfigs("servo_micro", "atlas", "clobberconflict1")

    def test_DuplicateControl0Configs(self):
        """Tests that duplicate control names in one file is an error."""
        with self.assertRaises(system_config.SystemConfigError):
            self._LoadConfigs("servo_micro", "atlas", "dupctrl0")

    def test_DuplicateControl1Configs(self):
        """Tests that duplicate control names in one file is an error."""
        with self.assertRaises(system_config.SystemConfigError):
            self._LoadConfigs("servo_micro", "atlas", "dupctrl1")

    def test_DuplicateControl2Configs(self):
        """Tests that duplicate control names in one file is an error."""
        with self.assertRaises(system_config.SystemConfigError):
            self._LoadConfigs("servo_micro", "atlas", "dupctrl2")

    def test_reformat_val_no_map_no_fmt(self):
        syscfg = system_config.SystemConfig()
        result = syscfg.reformat_val({"control_name": "test"}, "val")
        self.assertEqual(result, "val")

    def test_reformat_val_with_fmt(self):
        syscfg = system_config.SystemConfig()
        syscfg._Fmt_hex = lambda x: hex(int(x))
        result = syscfg.reformat_val({"control_name": "test", "fmt": "hex"}, "16")
        self.assertEqual(result, "0x10")

    def test_reformat_val_with_invalid_fmt(self):
        syscfg = system_config.SystemConfig()
        with self.assertRaisesRegex(
            system_config.SystemConfigError, "Unrecognized format"
        ):
            syscfg.reformat_val({"control_name": "test", "fmt": "invalid_fmt"}, "16")

    def test_reformat_val_with_fmt_exception(self):
        syscfg = system_config.SystemConfig()
        syscfg._Fmt_fail = mock.Mock(side_effect=ValueError("Test error"))
        with self.assertRaisesRegex(
            system_config.SystemConfigError, "Problem executing format"
        ):
            syscfg.reformat_val({"control_name": "test", "fmt": "fail"}, "16")

    def test_reformat_val_with_map(self):
        syscfg = system_config.SystemConfig()
        syscfg.syscfg_dict[system_config.MAP_TAG]["test_map"] = {
            "map_params": {"on": "1", "off": "0"}
        }
        result = syscfg.reformat_val({"control_name": "test", "map": "test_map"}, "1")
        self.assertEqual(result, "on")

    def test_reformat_val_with_map_regex(self):
        syscfg = system_config.SystemConfig()
        syscfg.syscfg_dict[system_config.MAP_TAG]["test_map_re"] = {
            "map_params": {"active": ".*1.*", "inactive": ".*0.*"}
        }
        result = syscfg.reformat_val(
            {"control_name": "test", "map": "test_map_re"}, "value_1_here"
        )
        self.assertEqual(result, "active")

    def test_reformat_val_with_map_key_match(self):
        syscfg = system_config.SystemConfig()
        syscfg.syscfg_dict[system_config.MAP_TAG]["test_map"] = {
            "map_params": {"on": "1", "off": "0"}
        }
        result = syscfg.reformat_val({"control_name": "test", "map": "test_map"}, "on")
        self.assertEqual(result, "on")

    def test_reformat_val_with_map_not_found(self):
        syscfg = system_config.SystemConfig()
        syscfg.syscfg_dict[system_config.MAP_TAG]["test_map"] = {
            "map_params": {"on": "1", "off": "0"}
        }
        result = syscfg.reformat_val({"control_name": "test", "map": "test_map"}, "2")
        self.assertEqual(result, "2")

    @mock.patch("os.path.isfile")
    def test_find_cfg_file(self, mock_isfile):
        syscfg = system_config.SystemConfig()
        mock_isfile.side_effect = lambda x: x == "direct_file.xml"
        self.assertEqual(syscfg.find_cfg_file("direct_file.xml"), "direct_file.xml")
        mock_isfile.side_effect = lambda x: str(x).endswith("data/default_file.xml")
        self.assertTrue(
            "data/default_file.xml" in syscfg.find_cfg_file("default_file.xml")
        )
        mock_isfile.side_effect = lambda x: False
        self.assertIsNone(syscfg.find_cfg_file("missing_file.xml"))

    def test_tag_string_to_tags(self):
        self.assertEqual(
            system_config.SystemConfig.tag_string_to_tags("tag1,tag2"), ["tag1", "tag2"]
        )

    @mock.patch("glob.glob")
    @mock.patch("os.path.dirname")
    def test_get_all_cfg_names(self, mock_dirname, mock_glob):
        syscfg = system_config.SystemConfig()
        mock_dirname.return_value = "/fake/dir"
        mock_glob.return_value = [
            "/fake/dir/data/servo_v4.xml",
            "/fake/dir/data/servo_v4_overlay.xml",
            "/fake/dir/data/cr50.xml",
        ]
        result = syscfg.get_all_cfg_names()
        self.assertIn("servo_v4.xml", result)
        self.assertIn("cr50.xml", result)
        self.assertNotIn("servo_v4_overlay.xml", result)

    @mock.patch("servo.common.config.system_config.SystemConfig.find_cfg_file")
    def test_add_cfg_file_not_found(self, mock_find):
        syscfg = system_config.SystemConfig()
        mock_find.return_value = None
        with self.assertRaisesRegex(
            system_config.SystemConfigError, "Unable to find system file"
        ):
            syscfg.add_cfg_file("", "missing.xml")

    @mock.patch("servo.common.config.system_config.SystemConfig.find_cfg_file")
    def test_add_cfg_file_already_loaded(self, mock_find):
        syscfg = system_config.SystemConfig()
        mock_find.return_value = "found.xml"
        syscfg._loaded_xml_files.add(("", "found.xml"))
        syscfg.add_cfg_file("", "found.xml")

    def test_add_cfg_file_no_name(self):
        syscfg = system_config.SystemConfig()
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".xml") as f:
            f.write("<root><control></control></root>")
            temp_path = f.name
        try:
            with self.assertRaisesRegex(
                system_config.SystemConfigError, "no name ... see XML"
            ):
                syscfg.add_cfg_file("", temp_path)
        finally:
            os.remove(temp_path)

    def test_add_cfg_file_redundant_entity(self):
        syscfg = system_config.SystemConfig()
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".xml") as f:
            f.write(
                '<root><control><name>test</name><params drv="test"></params></control><control><name>test</name><params drv="test"></params></control></root>'
            )
            temp_path = f.name
        try:
            with self.assertRaisesRegex(
                system_config.SystemConfigError,
                "contains redundant or conflicting definitions",
            ):
                syscfg.add_cfg_file("", temp_path)
        finally:
            os.remove(temp_path)

    def test_add_cfg_file_reserved_param(self):
        syscfg = system_config.SystemConfig()
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".xml") as f:
            f.write(
                '<root><control><name>test</name><params CONTENT="bad" drv="test"></params></control></root>'
            )
            temp_path = f.name
        try:
            with self.assertRaisesRegex(
                system_config.SystemConfigError,
                "specifies reserved params attribute name",
            ):
                syscfg.add_cfg_file("", temp_path)
        finally:
            os.remove(temp_path)

    def test_add_cfg_file_invalid_cmd(self):
        syscfg = system_config.SystemConfig()
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".xml") as f:
            f.write(
                '<root><control><name>test</name><params cmd="bad"></params></control></root>'
            )
            temp_path = f.name
        try:
            with self.assertRaisesRegex(
                system_config.SystemConfigError, "cmd has to be set\\|get"
            ):
                syscfg.add_cfg_file("", temp_path)
        finally:
            os.remove(temp_path)

    def test_add_cfg_file_multiple_params_no_cmd(self):
        syscfg = system_config.SystemConfig()
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".xml") as f:
            f.write(
                "<root><control><name>test</name><params></params><params></params></control></root>"
            )
            temp_path = f.name
        try:
            with self.assertRaisesRegex(
                system_config.SystemConfigError, "multiple params but no cmd"
            ):
                syscfg.add_cfg_file("", temp_path)
        finally:
            os.remove(temp_path)

    def test_add_cfg_file_multiple_get_params(self):
        syscfg = system_config.SystemConfig()
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".xml") as f:
            f.write(
                '<root><control><name>test</name><params cmd="get"></params><params cmd="get"></params></control></root>'
            )
            temp_path = f.name
        try:
            with self.assertRaisesRegex(
                system_config.SystemConfigError, "multiple get params defined"
            ):
                syscfg.add_cfg_file("", temp_path)
        finally:
            os.remove(temp_path)

    def test_add_cfg_file_multiple_set_params(self):
        syscfg = system_config.SystemConfig()
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".xml") as f:
            f.write(
                '<root><control><name>test</name><params cmd="set"></params><params cmd="set"></params></control></root>'
            )
            temp_path = f.name
        try:
            with self.assertRaisesRegex(
                system_config.SystemConfigError, "multiple set params defined"
            ):
                syscfg.add_cfg_file("", temp_path)
        finally:
            os.remove(temp_path)

    def test_add_cfg_file_illegal_number_of_params(self):
        syscfg = system_config.SystemConfig()
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".xml") as f:
            f.write(
                '<root><control><name>test</name><params cmd="set"></params><params cmd="get"></params><params cmd="get"></params></control></root>'
            )
            temp_path = f.name
        try:
            with self.assertRaisesRegex(
                system_config.SystemConfigError, "has illegal number of params 3"
            ):
                syscfg.add_cfg_file("", temp_path)
        finally:
            os.remove(temp_path)

    def test_add_cfg_file_map_alias(self):
        syscfg = system_config.SystemConfig()
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".xml") as f:
            f.write(
                "<root><map><name>test</name><alias>test_alias</alias><params></params></map></root>"
            )
            temp_path = f.name
        try:
            with self.assertRaisesRegex(
                system_config.SystemConfigError, "No aliases for maps allowed"
            ):
                syscfg.add_cfg_file("", temp_path)
        finally:
            os.remove(temp_path)

    def test_add_cfg_file_clobber_never(self):
        syscfg = system_config.SystemConfig()
        syscfg.syscfg_dict[system_config.CONTROL_TAG]["test"] = {
            "get_params": {},
            "set_params": {},
        }
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".xml") as f:
            f.write(
                '<root><control><name>test</name><params clobber_ok="never" drv="test"></params></control></root>'
            )
            temp_path = f.name
        try:
            syscfg.add_cfg_file("", temp_path)
            self.assertNotIn(
                "drv",
                syscfg.syscfg_dict[system_config.CONTROL_TAG]["test"]["get_params"],
            )
        finally:
            os.remove(temp_path)

    def test_add_cfg_file_clobber_patch(self):
        syscfg = system_config.SystemConfig()
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".xml") as f:
            f.write(
                '<root><control><name>test</name><params clobber_ok="patch" drv="test"></params></control></root>'
            )
            temp_path = f.name
        try:
            syscfg.add_cfg_file("", temp_path)
            self.assertNotIn("test", syscfg.syscfg_dict[system_config.CONTROL_TAG])
        finally:
            os.remove(temp_path)

    def test_add_cfg_file_conflicting_clobber(self):
        syscfg = system_config.SystemConfig()
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".xml") as f:
            f.write(
                '<root><control><name>test</name><params cmd="get" clobber_ok="full"></params><params cmd="set" clobber_ok="never"></params></control></root>'
            )
            temp_path = f.name
        try:
            with self.assertRaisesRegex(
                system_config.SystemConfigError, "has conflicting clobber_ok="
            ):
                syscfg.add_cfg_file("", temp_path)
        finally:
            os.remove(temp_path)

    def test_add_cfg_file_hwinit_clobber(self):
        syscfg = system_config.SystemConfig()
        syscfg.syscfg_dict[system_config.CONTROL_TAG]["test"] = {
            "get_params": {},
            "set_params": {},
        }
        syscfg.aliases["alias_name"] = "test"
        syscfg.hwinit.append(("test", "old_init"))
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".xml") as f:
            f.write(
                '<root><control><name>alias_name</name><params init="new_init" drv="test" clobber_ok="full"></params></control></root>'
            )
            temp_path = f.name
        try:
            syscfg.add_cfg_file("", temp_path)
            self.assertIn(("test", "new_init"), syscfg.hwinit)
        finally:
            os.remove(temp_path)

    def test_add_cfg_file_clobber_empty(self):
        syscfg = system_config.SystemConfig()
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".xml") as f:
            f.write(
                '<root><control><name>test</name><params cmd="get" drv="test"></params></control></root>'
            )
            temp_path = f.name
        try:
            syscfg.add_cfg_file("", temp_path)
            self.assertIn("test", syscfg.syscfg_dict[system_config.CONTROL_TAG])
        finally:
            os.remove(temp_path)

    def test_add_cfg_file_clobber_default_full(self):
        syscfg = system_config.SystemConfig()
        syscfg.syscfg_dict[system_config.CONTROL_TAG]["test"] = {
            "get_params": {},
            "set_params": {},
        }
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".xml") as f:
            f.write(
                '<root><control><name>test</name><params cmd="get" drv="test"></params></control></root>'
            )
            temp_path = f.name
        try:
            syscfg.add_cfg_file("", temp_path)
            self.assertIn(
                "drv",
                syscfg.syscfg_dict[system_config.CONTROL_TAG]["test"]["get_params"],
            )
        finally:
            os.remove(temp_path)

    def test_add_cfg_file_no_drv_set(self):
        syscfg = system_config.SystemConfig()
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".xml") as f:
            f.write(
                '<root><control><name>test</name><params cmd="get" drv="test"></params><params cmd="set"></params></control></root>'
            )
            temp_path = f.name
        try:
            with self.assertRaisesRegex(
                system_config.SystemConfigError,
                'control .* cmd="set" has no driver configured',
            ):
                syscfg.add_cfg_file("", temp_path)
        finally:
            os.remove(temp_path)

    def test_add_cfg_file_invalid_alias(self):
        syscfg = system_config.SystemConfig()
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".xml") as f:
            f.write(
                '<root><control><name>test</name><alias>bad alias</alias><params drv="test"></params></control></root>'
            )
            temp_path = f.name
        try:
            with self.assertRaisesRegex(
                system_config.SystemConfigError, "invalid alias"
            ):
                syscfg.add_cfg_file("", temp_path)
        finally:
            os.remove(temp_path)

    def test_lookup_map_params_not_found(self):
        syscfg = system_config.SystemConfig()
        syscfg.syscfg_dict[system_config.MAP_TAG] = {"map1": {}, "map2": {}}
        with self.assertRaisesRegex(
            NameError, "No map named missing_map. All maps:\nmap1,map2"
        ):
            syscfg.lookup_map_params("missing_map")

    def test_lookup_control_params_not_found(self):
        syscfg = system_config.SystemConfig()
        syscfg.syscfg_dict[system_config.CONTROL_TAG] = {"ctrl1": {}, "ctrl2": {}}
        with self.assertRaisesRegex(
            NameError, "No control named missing_control. All controls:\nctrl1,ctrl2"
        ):
            syscfg.lookup_control_params("missing_control")

    def test_board_cfg(self):
        syscfg = system_config.SystemConfig()
        syscfg.set_board_cfg("test_board.xml")
        self.assertEqual(syscfg.get_board_cfg(), "test_board.xml")

    def test_check_controls_for_drv(self):
        syscfg = system_config.SystemConfig()
        syscfg.syscfg_dict[system_config.CONTROL_TAG]["test1"] = {
            "get_params": {},
            "set_params": {"drv": "test"},
        }
        with self.assertRaisesRegex(
            system_config.SystemConfigError, 'cmd="get" has no driver configured'
        ):
            syscfg._check_controls_for_drv()

        syscfg.syscfg_dict[system_config.CONTROL_TAG]["test2"] = {
            "get_params": {"drv": "test"},
            "set_params": {},
        }
        # Need to clean up test1 or it will fail on test1 again!
        del syscfg.syscfg_dict[system_config.CONTROL_TAG]["test1"]
        with self.assertRaisesRegex(
            system_config.SystemConfigError, 'cmd="set" has no driver configured'
        ):
            syscfg._check_controls_for_drv()

    def test_get_all_controls(self):
        syscfg = system_config.SystemConfig()
        syscfg.syscfg_dict[system_config.CONTROL_TAG] = {"control1": {}, "control2": {}}
        self.assertEqual(set(["control1", "control2"]), syscfg.get_all_controls())

    def test_is_control(self):
        syscfg = system_config.SystemConfig()
        syscfg.syscfg_dict[system_config.CONTROL_TAG] = {"control1": {}}
        self.assertTrue(syscfg.is_control("control1"))
        self.assertFalse(syscfg.is_control("missing"))

    def test_get_control_str(self):
        syscfg = system_config.SystemConfig()
        syscfg.syscfg_dict[system_config.CONTROL_TAG] = {
            "test": {
                "doc": "Test doc",
                "get_params": {"cmd": "get"},
                "set_params": {"cmd": "set"},
            }
        }
        result = syscfg.get_control_str("test")
        self.assertIn("DOC: Test doc", result)
        self.assertIn("GET: {'cmd': 'get'}", result)
        self.assertIn("SET: {'cmd': 'set'}", result)

    def test_is_map(self):
        syscfg = system_config.SystemConfig()
        syscfg.syscfg_dict[system_config.MAP_TAG] = {"map1": {}}
        self.assertTrue(syscfg.is_map("map1"))
        self.assertFalse(syscfg.is_map("missing"))

    def test_get_control_docstring(self):
        syscfg = system_config.SystemConfig()
        syscfg.syscfg_dict[system_config.CONTROL_TAG] = {"test": {"doc": "Test doc"}}
        self.assertEqual(syscfg.get_control_docstring("test"), "Test doc")

    def test_display_config(self):
        syscfg = system_config.SystemConfig()
        syscfg.syscfg_dict[system_config.MAP_TAG]["test_map"] = {
            "doc": "Test Map",
            "map_params": {"on": "1", "off": "0"},
        }
        syscfg.syscfg_dict[system_config.CONTROL_TAG]["test_control"] = {
            "doc": "Test Control",
            "get_params": {"cmd": "get"},
            "set_params": {"cmd": "set"},
        }
        result = syscfg.display_config()
        self.assertIn("Test Map", result)
        self.assertIn("Test Control", result)
        result_with_args = syscfg.display_config(
            tag_param=system_config.CONTROL_TAG, prefix="prefix"
        )
        self.assertIn("prefix.test_control", result_with_args)
        self.assertNotIn("Test Map", result_with_args)

    def test_resolve_val_input_type_value_error(self):
        syscfg = system_config.SystemConfig()
        with self.assertRaisesRegex(
            system_config.SystemConfigError, "must be of type 'int'"
        ):
            syscfg.resolve_val({"input_type": "int"}, "not_an_int")

    def test_resolve_val_input_type_unrecognized(self):
        syscfg = system_config.SystemConfig()
        with self.assertRaisesRegex(
            system_config.SystemConfigError,
            "cannot be cast to default input type 'int' or fallback input type 'float'",
        ):
            syscfg.resolve_val({"input_type": "some_random_type"}, "test")

    def test_fmt_hex(self):
        syscfg = system_config.SystemConfig()
        self.assertEqual(syscfg._Fmt_hex(16), "0x10")

    def test_fmt_lowercase(self):
        syscfg = system_config.SystemConfig()
        self.assertEqual(syscfg._Fmt_lowercase("TEsT"), "test")

    def test_lookup(self):
        syscfg = system_config.SystemConfig()
        syscfg.syscfg_dict[system_config.CONTROL_TAG] = {"test": {"doc": "Test doc"}}
        self.assertEqual(
            syscfg._lookup(system_config.CONTROL_TAG, "test"), {"doc": "Test doc"}
        )
        self.assertIsNone(syscfg._lookup(system_config.CONTROL_TAG, "missing"))


if __name__ == "__main__":
    unittest.main()
