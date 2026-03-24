# Copyright 2020 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Software flag module to store and report binary status."""

import re

from servo.drv import hw_driver


# pylint: disable=invalid-name
# This follows servod drv naming convention
class sflag(hw_driver.HwDriver):
    """A driver to store and report an on/off flag."""

    # This is not a constant but at the class level so that
    # it can be shared between set and get.
    # We use a list to allow for sharing across as the class will not make it
    # an instance variable if we write into the lists' 0th element.
    vstore = [None]

    def _drv_init(self):
        """Driver specific initializer."""
        super()._drv_init()
        # Set the valid input choices for this driver. Choices need to be set
        # to be strings.
        self._choices = re.compile("^(0|1)$")

    def _set(self, value):
        """Set the value to |value|."""
        # While these controls _should_ be using a map so that the values
        # are converted to on/off, we still need to make sure.
        self.vstore[0] = value

    def _get(self):
        """Return the |self.vstore| for this flag."""
        if self.vstore[0] is None:
            # Initialize with a 0 unless a default is provided. Pass through |set|
            # rather than just modifying the vstore, to ensure that the value
            # is a valid choice.
            self.set(int(self._params.get("default_value", 0)))
        return self.vstore[0]
