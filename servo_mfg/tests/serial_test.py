# Copyright 2021 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import unittest

from servo_mfg import micro_manager
from servo_mfg import v4p1_manager


# Note: This file repeatedly refers to 'standardized' serialnames. This is an
# effort to standardize all serials across servo models as
# 'MODEL'-[MFG]-[DATE][UNIT-NUMBER]


class TestMicroSerial(unittest.TestCase):
    """Test servo micro serial name conventions.

    Note: if the format of the serialname changes in the future, please
    add a test with the new format here.
    """

    def setUp(self):
        """Setup by getting the regex from the manager."""
        super(TestMicroSerial, self).setUp()
        self.re = micro_manager.MicroManager.SERIALNO_RE

    def test_Standardized(self):
        """Test a standardized serialname."""
        serial = "MICRO-S-2009020002"
        assert self.re.match(serial)

    def test_StandardizedTypeWrong(self):
        """Test a standardized serialname with the wrong servo type fails."""
        # No MACRO device type.
        serial = "MACRO-S-2009020002"
        assert not self.re.match(serial)

    def test_StandardizedInvalidDate(self):
        """Test a standardized serialname with an invalid date fails."""
        # No 31st month.
        serial = "MICRO-S-2031020002"
        assert not self.re.match(serial)

    def test_StandardizedInvalidSuffix(self):
        """Test a standardized serialname with an invalid suffix fails."""
        # Suffix at most 4 digits.
        serial = "MICRO-S-200902000222"
        assert not self.re.match(serial)
        # Suffix at most 4 digits.
        serial = "MICRO-S-200902000A"
        assert not self.re.match(serial)

    def test_LegacyStandardized(self):
        """Test a prior standardized format."""
        # The legacy standardized serial had no '-' or a type string up front.
        serial = "S2009020002"
        assert self.re.match(serial)

    def test_LegacyOne(self):
        """Test another prior format used."""
        # A previously used legacy format.
        serial = "SNNP00001"
        assert self.re.match(serial)
        serial = "SMCQ00203"
        assert self.re.match(serial)

    def test_LegacyTwo(self):
        """Test another prior format used."""
        # A previously used legacy format.
        serial = "CMO653-00166-04A928ABUL"
        assert self.re.match(serial)


class TestV4P1Serial(unittest.TestCase):
    """Test servo v4p1 serial name conventions.

    Note: if the format of the serialname changes in the future, please
    add a test with the new format here.
    """

    def setUp(self):
        """Setup by getting the regex from the manager."""
        super(TestV4P1Serial, self).setUp()
        self.re = v4p1_manager.V4P1Manager.SERIALNO_RE

    def test_Standardized(self):
        """Test a standardized serialname."""
        serial = "SERVOV4P1-S-2009020002"
        assert self.re.match(serial)

    def test_StandardizedTypeWrong(self):
        """Test a standardized serialname with the wrong servo type fails."""
        # No SERVOVXP1 device type.
        serial = "SERVOVXP1-S-2009020002"
        assert not self.re.match(serial)

    def test_StandardizedInvalidDate(self):
        """Test a standardized serialname with an invalid date fails."""
        # No 31st month.
        serial = "SERVOV4P1-S-2031020002"
        assert not self.re.match(serial)

    def test_StandardizedInvalidSuffix(self):
        """Test a standardized serialname with an invalid suffix fails."""
        # Suffix at most 4 digits.
        serial = "SERVOV4P1-S-200902000222"
        assert not self.re.match(serial)
        # Suffix at most 4 digits.
        serial = "SERVOV4P1-S-200902000A"
        assert not self.re.match(serial)

    def test_LegacyStandardized(self):
        """Test a prior standardized format."""
        # The legacy standardized serial had no '-' or a type string up front.
        serial = "C2009020002"
        assert self.re.match(serial)

    def test_LegacyOne(self):
        """Test another prior format used."""
        # A previously used legacy format.
        serial = "NQ00001"
        assert self.re.match(serial)
        serial = "ND00203"
        assert self.re.match(serial)


if __name__ == "__main__":
    unittest.main()
