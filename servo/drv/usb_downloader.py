# Copyright 2021 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Driver to download an image from a path/server to the 'image usbkey'."""

from servo.drv import hw_driver
from servo.utils.sys_interface import sys_interface


# pylint: disable=invalid-name
class usbDownloaderError(hw_driver.HwDriverError):
    """Error class for usbDownloader errors."""

    pass


# pylint: disable=invalid-name
# Servod driver discovery logic requires this naming convention
class usbDownloader(hw_driver.HwDriver):
    """Driver download an image to the 'image usbkey'."""

    # Control aliases to the image mux and power intended for image management
    _IMAGE_DEV = "image_usbkey_dev"

    def _get(self):
        """Improved error reporting for misuse."""
        raise usbDownloaderError(
            "Download requires image path. Please use set "
            "version of the control to provide path."
        )

    def _set(self, image_path):
        """Download image and save to the USB device found by host_usb_dev.

        Delegates to the standalone image_downloader script.

        Args:
          image_path: path or url to the recovery image.

        Raises:
          usbDownloaderError: if download fails for any reason.
        """
        self._logger.debug("image_path(%s)", image_path)
        usb_dev = self._servod_get(self._IMAGE_DEV)
        self._logger.debug("USB Device is at %s", usb_dev)

        if not usb_dev:
            raise usbDownloaderError("No usb device connected to servo")

        self._logger.info(
            "Using image_downloader to flash %s to %s", image_path, usb_dev
        )

        # Build the command: image_downloader --device=<usb_dev> --image_path=<path>
        # Note: image_downloader is a script from the platform/labstation repository.
        # It is expected to be installed and available in the PATH within the
        # servod environment.
        cmd = [
            "image_downloader",
            "--device=%s" % usb_dev,
            "--image_path=%s" % image_path,
        ]

        try:
            self._logger.debug("Calling: %s", " ".join(cmd))
            ret = sys_interface.call(cmd)
            if ret != 0:
                raise usbDownloaderError(
                    "image_downloader failed with return code %d" % ret
                )
        except Exception as e:
            raise usbDownloaderError(
                "Unexpected error during image download: %s" % str(e)
            )
        finally:
            # We just plastered the partition table for a block device.
            # Pass or fail, we mustn't go without telling the kernel about
            # the change, or it will punish us with sporadic, hard-to-debug
            # failures.
            # Note: image_downloader also calls these, but we keep them here for
            # safety and visibility within servod.
            usb_dev = self._servod_get(self._IMAGE_DEV)
            if usb_dev:
                self._logger.debug("Calling Sync")
                sys_interface.call(["sync", usb_dev])
                self._logger.debug("Calling blockdev")
                sys_interface.call(["blockdev", "--rereadpt", usb_dev])
