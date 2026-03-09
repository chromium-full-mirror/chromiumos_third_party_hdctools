# Copyright 2026 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
# Servod Test Plan: Download Image to USB

This test plan verifies the `download_image_to_usb` control path.
It ensures that the core servod service can correctly reach out to a provided HTTP/HTTPS URL, download a binary payload, and successfully write it to the connected Servo USB mass storage device.

> **Note:** This test requires a valid URL pointing to a non-zero-byte binary payload. 
> The mock URL below (`http://192.168.1.1/test_image.bin`) should be overridden dynamically by the Test Orchestrator using `sed` or an environment variable replacement prior to execution with a valid test payload server.

```bash
# 1. Provide a fake payload URL to trigger the download and write sequence.
dut-control download_image_to_usb_dev:http://192.168.124.67:7777/downloads/chromiumos_test_image.bin

# 2. Verify the command returned success (exit code 0).
# In bash, if the above command fails, the test block will immediately exit with a failure.
```
