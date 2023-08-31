# Copyright 2021 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Base Manufacturer implementing the common interface."""

import logging

from servo_mfg import tiny_servod as _tiny_servod


# pylint: disable=g-bad-exception-name
class ManufacturerError(Exception):
    """Manufacturer error class."""


class Manufacturer(object):
    """Class go through flow instructing user and programming devices."""

    # The default interface that the servo console is on is 0.
    # If the specific servo firmware has a different interface, overwrite
    # this value.
    SERVO_IFACE = 0

    def __init__(self, validation=False):
        """Initialize the logger, and the task holders.

        Args:
          validation: flag whether the manufacturer should only check if programming
                      was done successfully, or also program the value (if they
                      are blank, or misprogrammed)
        """
        self._logger = logging.getLogger(type(self).__name__)
        self._validation = validation
        self._dfu_task = None
        # The task might be a real value, but it might still be skipped.
        # Keep a second flag to know whether DFU is happening.
        self._dfu_registered = False
        self._pre_dfu_tasks = []
        self._post_dfu_tasks = []

    def _set_dfu_task(self, programmer, task_desc):
        """Helper for subclass to set the dfu task.

        Args:
          programmer: Programmer used to program in dfu mode
          task_desc: string describing the operation
        """
        self._dfu_task = Task(task_desc, programmer)
        self._dfu_registered = self._dfu_task.programmer is not None

    def _register_pre_dfu_task(self, programmer, task_desc):
        """Helper for register a task to run before dfu mode.

        Note: these are in order, so if the subclass needs to run a particular
        programmer A before a programmer B, they should be registered in the order
        that they need to run.

        Args:
          programmer: Programmer to run
          task_desc: string describing the operation
        """
        self._pre_dfu_tasks.append(Task(task_desc, programmer))

    def _register_post_dfu_task(self, programmer, task_desc):
        """Helper for register a task to run after dfu mode.

        Note: these are in order, so if the subclass needs to run a particular
        programmer A before a programmer B, they should be registered in the order
        that they need to run.

        Args:
          programmer: Programmer to run
          task_desc: string describing the operation
        """
        self._post_dfu_tasks.append(Task(task_desc, programmer))

    # NOTE: The |*_prep| and |*_post| helpers are slot to do maintenance and
    # prepare the next stage or clean up after a stage. In general, there are
    # 3 stages: pre-dfu, dfu, post-dfu
    # Tasks could be
    # - issuing instructions to the user
    # - waiting for usb devices to connect or disconnect
    # It's important to note that
    # - post() will only run if all programmers in the section succeeded
    # - pre() will always run. The only exception is for dfu. There pre and post()
    # only run if dfu was requested, otherwise they are skipped.

    def _pre_dfu_prep(self):
        """Use this slot to do anything before pre-dfu tasks are running."""

    def _pre_dfu_post(self):
        """Use this slot to do anything after pre-dfu tasks have run."""

    def _dfu_prep(self):
        """Use this slot to do anything before dfu has run."""

    def _dfu_post(self):
        """Use this slot to do anything after dfu has run."""

    def _post_dfu_prep(self):
        """Use this slot to do anything before post-dfu has run."""

    def _post_dfu_post(self):
        """Use this slot to do anything after post-dfu has run."""

    def manufacture(self, report, **kwargs):
        """Main manufacturing flow.

        Note: this just goes through the phases, and the registered
              programmers as described above. It's on the child class to fill out
              those classes with the work that needs to be done at each phase.

        Args:
          report: the report to fill out for this specific device
          **kwargs: device specific args needed for the programmers

        Returns:
          True if all devices program and verify successfully, False otherwise
        """
        result = True
        self._pre_dfu_prep()
        for t in self._pre_dfu_tasks:
            self._logger.debug("Going to run %s.", t.task_desc)
            if t.programmer:
                result = self._program(t.programmer, **kwargs)
                report.report_task(t.task_desc, bool(result))
            else:
                self._logger.debug("Skipping (as requested) to run %s.", t.task_desc)
                # None is used to indicate a skipped programmer.
                report.report_task(t.task_desc, None)
            if not result:
                return result
        self._pre_dfu_post()
        if self._dfu_task.programmer:
            self._dfu_prep()
            result = self._program(self._dfu_task.programmer, **kwargs)
            report.report_task(self._dfu_task.task_desc, bool(result))
            if not result:
                return result
            self._dfu_post()
        else:
            # No need to go through the phases here.
            report.report_task(self._dfu_task.task_desc, None)
        # Now we have arrived at the post dfu phase i.e. the phase to program
        # specific devices, set serial numbers, etc.
        self._post_dfu_prep()
        # At this point the servo device is found. Build a tiny servod and
        # pass it around for users that need to interact with the console.
        tiny_servod = _tiny_servod.TinyServod(
            self.SERVO_VID, self.SERVO_PID, self.SERVO_IFACE
        )
        for t in self._post_dfu_tasks:
            self._logger.debug("Going to run %s.", t.task_desc)
            if t.programmer:
                result = self._program(t.programmer, tiny_servod=tiny_servod, **kwargs)
                report.report_task(t.task_desc, bool(result))
            else:
                self._logger.debug("Skipping (as requested) to run %s.", t.task_desc)
                # None is used to indicate a skipped programmer.
                report.report_task(t.task_desc, None)
            if not result:
                return result
        self._post_dfu_post()
        tiny_servod.close()

        return bool(result)

    def _program(self, programmer, **kwargs):
        """Wrapper to execute with validation mode or not.

        Args:
          programmer: the programmer to run
          **kwargs: args to pass to the programmer

        Returns:
          Result of the programmer's requested operation: validate or program
        """
        if self._validation:
            return programmer.validate(**kwargs)
        return programmer.program(**kwargs)

    def check_env(self):
        """Whether this environment can program successfully."""
        success = True
        for task in self._pre_dfu_tasks + [self._dfu_task] + self._post_dfu_tasks:
            if task is not None:
                if task.programmer is not None:
                    s = task.programmer.verify_programming_env()
                    suffix = ": can run." if s else ": cannot run."
                else:
                    s = True
                    suffix = ": skipped."
                self._logger.info(task.task_desc + suffix)
                success = success & s
        return success


class Task(object):
    """Holder object for a programmer and some metadata."""

    def __init__(self, task_desc, programmer=None):
        """Store the data.

        Args:
          task_desc: string describing the task
          programmer: the programmer to run, or None if this task should be skipped.
        """
        self.programmer = programmer
        self.task_desc = task_desc
