# Copyright 2021 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Driver to download an image from a path/server to the 'image usbkey'."""

import shutil
import subprocess
try:
  from urllib import urlretrieve, ContentTooShortError
except ImportError:
  # TODO(b:177480273): remove this once python2 is turned off.
  from urllib.request import urlretrieve
  from urllib.error import ContentTooShortError

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
  _IMAGE_DEV = 'image_usbkey_dev'

  _HTTP_PREFIX = 'http://'

  def get(self):
    """Improved error reporting for misuse."""
    raise usbDownloaderError('Download requires image path. Please use set '
                             'version of the control to provide path.')

  def set(self, image_path):
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
    self._logger.debug('image_path(%s)', image_path)
    self._logger.debug('Detecting USB stick device...')
    usb_dev = self._interface.get(self._IMAGE_DEV)
    # |errormsg| is usd later to indicate the error
    errormsg = ''
    if not usb_dev:
      # No usb dev attached, skip straight to the end.
      errormsg = 'No usb device connected to servo'
    else:
      # There is a usb dev attached. Try to get the image.
      try:
        if image_path.startswith(self._HTTP_PREFIX):
          self._logger.debug('Image path is a URL, downloading image')
          urlretrieve(image_path, usb_dev)
        else:
          shutil.copyfile(image_path, usb_dev)
        # Ensure that after the download the usb-device is still attached, as
        # copyfile does not raise an error stick is removed mid-writing for
        # instance.
        if not self._interface.get('image_usbkey_dev'):
          raise usbDownloaderError('Device file %s not found again after '
                                   'copy completed.' % usb_dev)
      except ContentTooShortError:
        errormsg = 'Failed to download URL: %s to USB device: %s' % (image_path,
                                                                     usb_dev)
      except (IOError, OSError) as e:
        errormsg = ('Failed to transfer image to USB device: %s ( %s ) ' %
                    (e.strerror, e.errno))
      except usbDownloaderError as e:
        errormsg = 'Failed to transfer image to USB device: %s' % e.message
      except BaseException as e:
        errormsg = ('Unexpected exception downloading %s to %s: %s' %
                    (image_path, usb_dev, str(e)))
      finally:
        # We just plastered the partition table for a block device.
        # Pass or fail, we mustn't go without telling the kernel about
        # the change, or it will punish us with sporadic, hard-to-debug
        # failures.
        subprocess.call(['sync', usb_dev])
        subprocess.call(['blockdev', '--rereadpt', usb_dev])
    if errormsg:
      self._logger.error(errormsg)
      raise usbDownloaderError(errormsg)
