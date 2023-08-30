# Copyright 2021 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Driver to download an image from a path/server to the 'image usbkey'."""

import contextlib
import os
import shutil
import subprocess
from urllib.error import ContentTooShortError
from urllib.request import urlopen

from requests import get
from requests import head
from requests.exceptions import Timeout

from servo.drv import hw_driver


# pylint: disable=invalid-name
class usbDownloaderError(hw_driver.HwDriverError):
    """Error class for usbDownloader errors."""

    pass


# pylint: disable=invalid-name
# Servod driver discovery logic requires this naming convension
class usbDownloader(hw_driver.HwDriver):
    """Driver download an image to the 'image usbkey'."""

    # Control aliases to the image mux and power intended for image management
    _IMAGE_DEV = "image_usbkey_dev"

    _HTTP_PREFIX = "http://"

    def _get(self):
        """Improved error reporting for misuse."""
        raise usbDownloaderError(
            "Download requires image path. Please use set "
            "version of the control to provide path."
        )

    def _urlretrieve(self, url, filename, bs, reporthook=None):
        """
        Retrieve a URL into a temporary location on disk.
        Requires a URL argument. If a filename is passed, it is used as
        the temporary file location.

        The reporthook argument should be a callable that accepts a block
        number, a read size, and the total file size of the URL target.
        The data argument should be valid URL encoded data.
        Returns a tuple containing the path to the newly created
        data file as well as the resulting HTTPMessage object.
        """

        with contextlib.closing(get(url, timeout=900, stream=True)) as resp:
            headers = resp.headers
            self._logger.debug("Block size %d", bs)
            self._logger.debug("Request Get Headers %s", headers)
            tfp = open(filename, "wb", 0)
            with tfp:
                result = filename, headers
                size = -1
                read = 0
                blocknum = 0
                if "content-length" in headers:
                    size = int(headers["Content-Length"])
                if reporthook:
                    reporthook(blocknum, bs, size)

                for block in resp.iter_content(chunk_size=bs):
                    if not block:
                        break
                    read += len(block)
                    tfp.write(block)
                    tfp.flush()
                    blocknum += 1
                    if reporthook:
                        reporthook(blocknum, bs, size)
                tfp.flush()
                self._logger.debug("Closing handle to block file")
            self._logger.debug("Closing urlopen")
        if size >= 0 and read < size:
            raise ContentTooShortError(
                "retrieval incomplete: got only %i out of %i bytes" % (read, size),
                result,
            )
        self._logger.debug("All done....")
        return result

    def _set(self, image_path):
        """Download image and save to the USB device found by host_usb_dev.

        If the image_path is a URL, it will download this url to the USB path;
        otherwise it will simply copy the image_path's contents to the USB path.

        Args:
          image_path: path or url to the recovery image.

        Raises:
          usbDownloaderError: if download fails for any reason.
        """
        # pylint: disable=broad-except
        # Ensure that any issue gets caught & reported as UsbImageError
        self._logger.debug("image_path(%s)", image_path)
        self._logger.debug("Detecting USB stick device...")
        usb_dev = self._servod_get(self._IMAGE_DEV)
        self._logger.debug("USB Device is at %s", usb_dev)
        # |errormsg| is usd later to indicate the error
        errormsg = ""
        if not usb_dev:
            # No usb dev attached, skip straight to the end.
            errormsg = "No usb device connected to servo"
        else:
            # There is a usb dev attached. Try to get the image.
            try:
                if image_path.startswith(self._HTTP_PREFIX):
                    self._logger.debug("Image path is a URL, downloading image")

                    # Check the webserver is working by getting the first 100
                    # bytes of the file.
                    self._logger.debug("Testing webserver")
                    response = head(image_path, timeout=900)
                    response.raise_for_status()
                    self._logger.debug("Test Headers %s" % response.headers)
                    self._logger.debug("Webserver test pass")

                    # Get the block size of the device so we can write in
                    # the same chunk size.
                    bs = os.statvfs(usb_dev).f_bsize
                    if bs < 0:
                        bs = 4096

                    # Test we can write to the USB stick
                    self._logger.debug("Testing device")
                    tfp = open(usb_dev, "wb")
                    tfp.write(b"000000000000000000000000000")
                    tfp.close()
                    self._logger.debug("Device testing pass")

                    def show_progress(block_num, block_size, total_size):
                        if block_num and block_num % 1000 == 0:
                            self._logger.debug(
                                "Show progress Block Num %d Block Size %d  Total %d"
                                % (block_num, block_size, total_size)
                            )
                            self._logger.debug(
                                "Urlretrieve Progress %d%%"
                                % (((block_num * block_size) / total_size) * 100)
                            )

                    self._logger.debug("Copy Started %s %s" % (image_path, usb_dev))
                    self._urlretrieve(image_path, usb_dev, bs, show_progress)
                    self._logger.debug("Copy Ended")
                else:
                    shutil.copyfile(image_path, usb_dev)
                # Ensure that after the download the usb-device is still attached, as
                # copyfile does not raise an error stick is removed mid-writing for
                # instance.
                self._logger.debug("Checking stable after copy")
                if not self._servod_get("image_usbkey_dev"):
                    raise usbDownloaderError(
                        "Device file %s not found again after "
                        "copy completed." % usb_dev
                    )
            except ContentTooShortError:
                self._logger.debug("Error ContentTooShortError")
                errormsg = "Failed to download URL: %s to USB device: %s" % (
                    image_path,
                    usb_dev,
                )
            except Timeout as e:
                errormsg = (
                    "Requesting the headers of the URL timed out after 900 seconds: %s"
                    % e.message
                )
            except (IOError, OSError) as e:
                self._logger.debug("Error IOError/OSError")
                errormsg = "Failed to transfer image to USB device: %s ( %s ) " % (
                    str(e),
                    e.errno,
                )
            except usbDownloaderError as e:
                self._logger.debug("Error usbDownloaderError")
                errormsg = "Failed to transfer image to USB device: %s" % e.message
            except BaseException as e:
                self._logger.debug("Error BaseException")
                errormsg = "Unexpected exception downloading %s to %s: %s" % (
                    image_path,
                    usb_dev,
                    str(e),
                )
            finally:
                # We just plastered the partition table for a block device.
                # Pass or fail, we mustn't go without telling the kernel about
                # the change, or it will punish us with sporadic, hard-to-debug
                # failures.
                usb_dev = self._servod_get(self._IMAGE_DEV)
                self._logger.debug("USB Device is at %s", usb_dev)
                if usb_dev:
                    self._logger.debug("Calling Sync")
                    subprocess.call(["sync", usb_dev])
                    self._logger.debug("Calling blockdev")
                    subprocess.call(["blockdev", "--rereadpt", usb_dev])
        if errormsg:
            self._logger.error(errormsg)
            raise usbDownloaderError(errormsg)
