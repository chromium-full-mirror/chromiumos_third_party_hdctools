# Copyright 2021 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Helper functions to exec commands."""

import logging
import subprocess
import time

# Frequency with which to poll the subprocess.
PROCESS_POLL_S = 0.01
# Timeout after which to kill the subprocess. 1 minutes.
# Note: this is used twice. one, then a warning is printed, then once again.
PROCESS_TIMEOUT_S = 1 * 60


def _exec_line(cmd, hint=None):
  """Helper to format the exec line for logging purposes.

  Args:
    cmd: list of arguments to execute
    hint: optional debug str of what is being performed e.g. writing, reading

  Returns:
    formatted line to use in log messages
  """
  return '%s (%s)' % (cmd[0], hint) if hint else cmd[0]


def exec_nonblocking(cmd, hint=None):
  """Helper to run |cmd| and return subprocess.

  Args:
    cmd: list of args to use to execute
    hint: optional debug str of what is being performed e.g. writing, reading

  Returns:
    Popen object with the command executing
  """
  logging.info('executing: %s', _exec_line(cmd, hint))
  # Dump the full command into the debug logs.
  logging.debug('executing: %r', ' '.join(cmd))
  return subprocess.Popen(cmd, stderr=subprocess.PIPE,
                          stdout=subprocess.PIPE)


def exec_blocking(cmd, hint=None, timeout=PROCESS_TIMEOUT_S):
  """Helper to run |cmd| and capture all output to logs before errors.

  Args:
    cmd: list of args to use to execute
    hint: optional debug str of what is being performed e.g. writing, reading
    timeout: seconds to wait for the process to finish before aborting

  Returns:
    tuple (exit_code, stdout, stderr) of the process
  """
  process = exec_nonblocking(cmd, hint=hint)
  warning_marker = time.time() + timeout
  end = warning_marker + timeout
  warning_sent = False
  while process.poll() is None:
    if time.time() > warning_marker and not warning_sent:
      logging.error('Still waiting on %r', ' '.join(cmd))
      warning_sent = True
    if time.time() > end:
      logging.error('Killing %r', ' '.join(cmd))
      process.kill()
      break
    time.sleep(PROCESS_POLL_S)
  ret = process.poll()
  stdout, stderr = process.communicate()
  logging.info('finished: %s', _exec_line(cmd, hint))
  for line in stdout.splitlines():
    logging.debug(line)
  for line in stderr.splitlines():
    logging.debug(line)
  return ret, stdout, stderr
