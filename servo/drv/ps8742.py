# Copyright 2017 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Driver for Parade PS8742 USB mux.."""

from servo.drv import hw_driver
from servo.drv import i2c_reg


class Ps8742Error(hw_driver.HwDriverError):
    """Error occurred accessing ps8742."""


class ps8742(hw_driver.HwDriver):
    """Object to access drv=ps8742 controls."""

    # I2C Addr of typical ps8742.
    USB_MUX_ADDR = 0x20
    # Control reg offset.
    USB_MUX_CTRL = 0
    # USB3 line passthrough enable.
    USB_MUX_CTRL_USB3_EN = 0x20

    def _drv_init(self):
        """Driver specific initializer.

        Required params:
          child: integer, 7-bit i2c child address
          offset: integer, gpio's bit position from lsb
        """
        super()._drv_init()
        child = self._get_child()
        self._i2c_obj = i2c_reg.I2cReg.get_device(
            self._interface,
            child,
            addr_len=1,
            reg_len=1,
            msb_first=True,
            no_read=False,
            use_reg_cache=False,
        )

    def _Get_usb3(self):
        """Getter for usb3 enable.

        Returns:
          0: USB2 only.
          1: USB3.
        """
        value = self._i2c_obj._read_reg(self.USB_MUX_CTRL)
        if self.USB_MUX_CTRL_USB3_EN & value:
            return 1
        return 0

    def _Set_usb3(self, enable):
        """Setter for usb3 enable.

        Args:
          enable: 0 - USB2 only. 1 - enable USB3.
        """
        try:
            value = self._i2c_obj._read_reg(self.USB_MUX_CTRL, auto_release=False)
            if not enable:
                value = value & ~(self.USB_MUX_CTRL_USB3_EN)
            else:
                value = value | self.USB_MUX_CTRL_USB3_EN
            self._i2c_obj._write_reg(self.USB_MUX_CTRL, value, auto_release=False)
        finally:
            self._i2c_obj.release()

    def _get_child(self):
        """Check and return needed params to call driver.

        Returns:
          child: 7-bit i2c address
        """
        if "child" not in self._params:
            raise Ps8742Error("getting child address")
        child = int(self._params["child"], 0)
        return child
