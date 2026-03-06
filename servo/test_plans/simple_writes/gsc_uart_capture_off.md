# Copyright 2026 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
# Servod Test Plan: Isolated Write - gsc_uart_capture:off

This test plan verifies the write path for `gsc_uart_capture:off`.
It is designed to run in isolation. By starting and stopping `servod` for this single command, we ensure a clean, known-good state and prevent cascading hardware failures during testing.

```bash
dut-control gsc_uart_capture:off
```
