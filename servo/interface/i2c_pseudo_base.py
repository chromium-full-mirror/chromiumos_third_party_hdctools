# Copyright 2023 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""This provides an abstract base class for i2c-pseudo integrations to implement."""


class BaseI2cPseudoAdapter:
    """Subclasses implement a Linux I2C adapter for the servo I2C bus.

    Subclasses implement a controller for the i2c-pseudo Linux kernel module.
    See its documentation for background.

    Thread safety:
      Implementations may be internally multi-threaded.
      Implementations must support accessing any and all parts of their public
      interface from multiple threads concurrently.

    Usage that implementations must support:
      adap = I2cPseudoAdapter()
      adap.init(i2c_bus)
      adap.start()
      ...
      adap.shutdown()
    """

    @classmethod
    def default_controller_path(cls):
        """Get the default i2c-pseudo controller device path.

        Returns:
          bytes - absolute path
        """
        raise NotImplementedError

    def init(self, i2c_bus, controller_device_path=None):
        """Initialize the instance.  This does NOT create the pseudo adapter.

        Args:
          i2c_bus: implementation of i2c_base.BaseI2CBus
          controller_device_path: None or bytes or str - path to the
              i2c-pseudo device file
        """
        if controller_device_path is None:
            controller_device_path = self.default_controller_path()
        self._internal_init(i2c_bus, controller_device_path)

    def _internal_init(self, i2c_bus, controller_device_path):
        """Initialize the instance.  This does NOT create the pseudo adapter.

        Args:
          i2c_bus: implementation of i2c_base.BaseI2CBus
          controller_device_path: bytes or str - path to the i2c-pseudo device file
        """
        raise NotImplementedError

    def start(self):
        """Create and start the i2c-pseudo adapter.

        This method may be invoked repeatedly, including overlapping invocations
        from multiple threads.  Redundant invocations are a no-op.  When any one
        invocation has returned successfully (no exceptions), the I2C pseudo adapter
        has been started.

        If an invocation fails with an exception, the state of the object is
        undefined, and it should be abandoned.

        This MUST NOT be called during or after shutdown().
        """
        raise NotImplementedError

    @property
    def i2c_bus(self):
        """Get the i2c_base.BaseI2CBus implementation this object is using.

        Returns:
          i2c_base.BaseI2CBus
        """
        raise NotImplementedError

    @property
    def controller_device_path(self):
        """Get the i2c-pseudo controller device file this object is using.

        Returns:
          bytes or str - path to the i2c-pseudo controller device file
        """
        raise NotImplementedError

    @property
    def i2c_pseudo_id(self):
        """Get the i2c-pseudo controller ID.

        Returns:
          None or int - The i2c-pseudo controller ID, or None if start() has not
            completed yet.
        """
        raise NotImplementedError

    @property
    def i2c_adapter_num(self):
        """Get the Linux I2C adapter number.

        Returns:
          None or int - The Linux I2C adapter number, or None if start() has not
              completed yet.
        """
        raise NotImplementedError

    @property
    def is_running(self):
        """Check whether the pseudo controller is running.

        Returns:
          bool - True if the pseudo controller and its I/O thread are running, False
              otherwise, e.g. if the controller was either never started, or has
              been shutdown.
        """
        raise NotImplementedError

    def shutdown(self, timeout):
        """Shutdown the I2C pseudo adapter.

        start() MUST NOT be called during or after this.

        Args:
          timeout: None, int, or float - Wait this many seconds for the I/O thread
              to complete, or None to wait indefinitely.  Use 0 or 0.0 to not wait.

        Returns:
          bool - True if the pseudo controller and its I/O thread stopped before
              expiration of the timeout, False otherwise.
        """
        raise NotImplementedError
