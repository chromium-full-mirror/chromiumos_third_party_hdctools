# Copyright 2023 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""
This uses the i2c-pseudo driver to implement a local Linux I2C adapter of a
Servo/DUT I2C bus.
"""

import ctypes
import errno
import fcntl
import logging
import os
import select
import threading

from servo.interface import i2c_pseudo_base
from servo.utils.linux_i2c import i2c
from servo.utils.linux_i2c import i2c_pseudo


# pylint: disable=undefined-variable

_CONTROLLER_DEVICE_PATH = b"/dev/i2c-pseudo"
_I2C_ADAPTER_TIMEOUT_MS = 5000
_EPOLL_EVENTMASK = select.EPOLLIN | select.EPOLLERR | select.EPOLLHUP

# These must be in numerical order of progression.
_STATE_INIT = 0
_STATE_RUN = 1
_STATE_SHUTDOWN = 2


def _err_str(err_num):
    """Nicely format an errno number for logging or exception messages.

    Args:
      err_num: int - errno value, such as from OSError.errno

    Returns:
      str - A string incorporating the errno's numerical value, name if available, and
        description if available.  The exact format is not specific and is subject to
        change, it is meant only for human understanding, not machine parsing.
    """
    return "errno {:d} {} ({})".format(
        err_num, errno.errorcode.get(err_num, "UNKNOWN"), os.strerror(err_num)
    )


class I2cPseudoV2Adapter(i2c_pseudo_base.BaseI2cPseudoAdapter):
    """This class implements a Linux I2C adapter for the servo I2C bus.

    This class is a controller for the i2c-pseudo Linux kernel module.  See its
    documentation for background.

    Thread safety:
      This class is internally multi-threaded.
      It is safe to use the public interface from multiple threads concurrently.

    Usage:
      adap = I2cPseudoAdapter()
      adap.init(servo_i2c_bus)
      adap.start()
      ...
      adap.shutdown()
    """

    @classmethod
    def default_pseudo_device(cls):
        """Get the default i2c-pseudo controller device path.

        Returns:
          bytes - absolute path
        """
        path = _CONTROLLER_DEVICE_PATH
        assert isinstance(path, bytes)
        assert os.path.isabs(path)
        return path

    def __init__(self):
        i2c_pseudo_base.BaseI2cPseudoAdapter.__init__(self)
        self._logger = logging.getLogger("i2c_pseudo_v2")

        self._servo_i2c_bus = None
        self._pseudo_device_path = None
        self._device_fd = None
        self._i2c_adapter_num = None

        self._epoll = select.epoll(sizehint=1)
        self._io_thread = threading.Thread(
            name="I2C-Pseudo-PyID-0x%X" % (id(self),), target=self._io_thread_run
        )
        self._io_thread.daemon = True

        # i2c_base.BaseI2CBus interface only supports up to 1 write, followed by
        # up to 1 read, per I2C transaction.  So we only need to support a maximum
        # of 2 I2C messages per transaction, anything else can be rejected by the
        # driver because we can't support it anyways.
        self._msgs = (i2c.i2c_msg * 2)()
        self._data_buf = (ctypes.c_uint8 * 1024)()
        self._req_arg = i2c_pseudo.i2cp_ioctl_xfer_req_arg(
            msgs=self._msgs,
            data_buf=self._data_buf,
            msgs_len=len(self._msgs),
            data_buf_len=len(self._data_buf),
        )

        self._run_lock = threading.Lock()
        self._state = _STATE_INIT

        self._logger.info("finished initializing I2C pseudo adapter (not started yet!)")

    def _internal_init(self, servo_i2c_bus, pseudo_device_path):
        """Initialize the instance.  This does NOT create the pseudo adapter.

        Args:
          servo_i2c_bus: implementation of i2c_base.BaseI2CBus
          pseudo_device_path: bytes or str - path to the i2c-pseudo device file
        """
        self._logger.info(
            "initializing (not starting yet!) I2C pseudo adapter "
            "servo_i2c_bus=%r pseudo_device_path=%r",
            servo_i2c_bus,
            pseudo_device_path,
        )
        self._servo_i2c_bus = servo_i2c_bus
        self._pseudo_device_path = pseudo_device_path

    def start(self):
        """Create and start the i2c-pseudo adapter.

        This may only be called once, before any call to shutdown().

        If this fails with an exception, the state of the object is undefined.
        shutdown() may still be called, but otherwise the object should be abandoned.
        """
        with self._run_lock:
            assert self._state < _STATE_RUN
            self._start_impl()

    @property
    def servo_i2c_bus(self):
        """Get the i2c_base.BaseI2CBus implementation this object is using.

        Returns:
          None or i2c_base.BaseI2CBus - The servo I2C bus this pseudo controller
              is using, or None if init() has not completed yet.
        """
        return self._servo_i2c_bus

    @property
    def pseudo_device_path(self):
        """Get the i2c-pseudo controller device file this object is using.

        Returns:
          None or bytes or str - The path to the i2c-pseudo device file this
              pseudo controller is using, or None if init() has not completed
              yet.
        """
        return self._pseudo_device_path

    @property
    def i2c_adapter_num(self):
        """Get the Linux I2C adapter number.

        Returns:
          None or int - The Linux I2C adapter number, or None if start() has not
              completed yet.
        """
        return self._i2c_adapter_num

    @property
    def is_running(self):
        """Check whether the pseudo controller is running.

        Returns:
          bool - True if the pseudo controller and its I/O thread are running, False
              otherwise, e.g. if the controller was either never started, or has
              been shutdown.
        """
        return self._io_thread.is_alive()

    def _start_impl(self):
        """start() implementation that requires self._run_lock to be held."""
        assert self._state < _STATE_RUN
        self._logger.info("attempting to start I2C pseudo adapter")
        self._state = _STATE_RUN

        start_arg = i2c_pseudo.i2cp_ioctl_start_arg(
            functionality=i2c.I2C_FUNC_I2C | i2c.I2C_FUNC_SMBUS_EMUL,
            timeout_ms=_I2C_ADAPTER_TIMEOUT_MS,
            name=b"servod pid=%d obj_id=%d" % (os.getpid(), id(self)),
        )
        self._device_fd = os.open(self._pseudo_device_path, os.O_RDWR | os.O_NONBLOCK)
        fcntl.ioctl(self._device_fd, i2c_pseudo.I2CP_IOCTL_START, start_arg, True)
        self._i2c_adapter_num = start_arg.output.adapter_num

        self._epoll.register(self._device_fd, _EPOLL_EVENTMASK)
        self._io_thread.start()
        self._logger.info("finished starting I2C pseudo adapter")

    def _xfer_reply(self, reply_arg):
        """Send I2CP_IOCTL_XFER_REPLY.  Retry if interrupted by a signal.

        Args:
          reply_arg: i2cp_ioctl_xfer_reply_arg
        """
        while True:
            try:
                fcntl.ioctl(
                    self._device_fd, i2c_pseudo.I2CP_IOCTL_XFER_REPLY, reply_arg, True
                )
            except OSError as error:
                if error.errno == errno.EINTR:
                    continue
                # ETIME from I2CP_IOCTL_XFER_REPLY means we replied too late,
                # and therefore the requesting I2C device driver already got a
                # response from the I2C pseudo adapter.  That response should
                # have been ETIMEDOUT, unless a bug in this program caused a
                # redundant response to be sent for a single xfer_id.
                if error.errno == errno.ETIME:
                    self._logger.warning(
                        "I2CP_IOCTL_XFER_REPLY failed with {}, this may indicate the "
                        "I2C pseudo adapter timeout is set too short, or the system is "
                        "operating much slower than expected.".format(
                            _err_str(error.errno)
                        )
                    )
                    break
                raise
            break

    def _reply_error(self, xfer_id, err_num, log_msg):
        """Send I2CP_IOCTL_XFER_REPLY with non-zero error and zero num_msgs.

        If I2CP_IOCTL_XFER_REPLY fails with ETIME, indicating reply sent too
        late, that error will be suppressed and a warning for the failure will
        be logged.  All other failures from the ioctl() will be allowed to
        propagate.

        Args:
          xfer_id: int - i2cp_ioctl_xfer_reply_arg.xfer_id
          err_num: int - i2cp_ioctl_xfer_reply_arg.error; must be > 0
          log_msg: str - Human friendly detailed information about what went wrong.
        """
        assert err_num > 0
        self._logger.warning("{}\nReplying with {}.".format(log_msg, _err_str(err_num)))
        self._xfer_reply(
            i2c_pseudo.i2cp_ioctl_xfer_reply_arg(
                xfer_id=xfer_id, num_msgs=0, error=err_num
            )
        )

    # pylint: disable-next=unused-argument
    def _attempt_xfer(self, event):
        """Handle a poll event from the I2C pseudo controller device.

        Args:
          event: int - epoll event mask

        Returns:
          bool - True if another I2CP_IOCTL_XFER_REQ should be attempted before polling
              again, False otherwise.
        """
        assert self._state >= _STATE_RUN
        if self._state != _STATE_RUN:
            return False

        req_arg = self._req_arg
        try:
            fcntl.ioctl(self._device_fd, i2c_pseudo.I2CP_IOCTL_XFER_REQ, req_arg, True)
        except OSError as error:
            if error.errno == errno.EAGAIN or error.errno == errno.EWOULDBLOCK:
                return False
            if error.errno == errno.EINTR:
                return True
            if error.errno == errno.EMSGSIZE:
                self._reply_error(
                    req_arg.output.xfer_id,
                    errno.EMSGSIZE,
                    "An I2C device attempted {:d} messages in a transaction, servod "
                    "supports a maximum of {:d} (one write and/or one read).".format(
                        req_arg.output.num_msgs, len(self._msgs)
                    ),
                )
                return True
            self._logger.error(
                "I2CP_IOCTL_XFER_REQ error {}: {}".format(
                    errno.errorcode.get(error.errno) or "<UNKNOWN>", error
                )
            )
            raise

        assert req_arg.output.num_msgs > 0
        assert req_arg.output.num_msgs <= len(self._msgs)
        i2c_addr = None
        write_list = None
        read_msg = None

        for msg_idx in range(req_arg.output.num_msgs):
            i2c_msg = req_arg.msgs[msg_idx]
            # I2C_M_RECV_LEN is not supported by the servod I2C bus interface.
            # Messages using it should be rejected by the kernel I2C subsystem
            # on behalf of our I2C pseudo adapter, so this simple assertion
            # will do.
            assert not i2c_msg.flags & i2c.I2C_M_RECV_LEN
            if i2c_addr is not None and i2c_msg.addr != i2c_addr:
                self._reply_error(
                    req_arg.output.xfer_id,
                    errno.ENOTSUP,
                    "servod only supports communicating with one 7-bit I2C address per "
                    "I2C transaction",
                )
                return True
            i2c_addr = i2c_msg.addr
            if i2c_msg.flags & i2c.I2C_M_RD:
                if read_msg is not None:
                    self._reply_error(
                        req_arg.output.xfer_id,
                        errno.ENOTSUP,
                        "servod only supports up to 1 read per I2C transaction",
                    )
                    return True
                read_msg = i2c_msg
            else:
                if read_msg is not None:
                    self._reply_error(
                        req_arg.output.xfer_id,
                        errno.ENOTSUP,
                        "servod only supports write before read within an "
                        "I2C transaction",
                    )
                    return True
                if write_list is not None:
                    self._reply_error(
                        req_arg.output.xfer_id,
                        errno.ENOTSUP,
                        "servod only supports up to 1 write per I2C transaction",
                    )
                    return True
                write_list = [i2c_msg.buf[i] for i in range(i2c_msg.len)]

        try:
            retval = self._servo_i2c_bus.wr_rd(
                i2c_addr, write_list, read_msg.len if read_msg is not None else 0
            )
        except OSError as error:
            self._logger.exception("Servo device I2C transaction failed")
            self._reply_error(
                req_arg.output.xfer_id,
                error.errno,
                "Servo device I2C transaction failed with OSError, replying with errno",
            )
            return True
        except Exception:
            self._logger.exception("Servo device I2C transaction failed")
            self._reply_error(
                req_arg.output.xfer_id,
                errno.EIO,
                "Servo device I2C transaction failed, replying with EIO",
            )
            return True

        # The servod I2C interface API unfortunately allows for None and [] to be
        # returned interchangeably.  There is no way to distinguish between no read and
        # zero-byte read, so we must always assume the most lenient interpretation.
        if read_msg is None:
            if retval:
                self._logger.error(
                    "Servo device I2C returned unrequested read of {:d} bytes, "
                    "ignoring the read bytes".format(len(retval))
                )
        else:
            if retval is None:
                retval = []
            if len(retval) < read_msg.len:
                self._reply_error(
                    req_arg.output.xfer_id,
                    errno.ECANCELED,
                    "Servo device I2C returned short read, requested {:d} bytes, "
                    "received {:d} bytes".format(read_msg.len, len(retval)),
                )
                return True
            if len(retval) > read_msg.len:
                self._logger.error(
                    "Servo device I2C read returned {:d} bytes when request was for "
                    "{:d} bytes, ignoring the extra {:d} bytes".format(
                        len(retval), read_msg.len, len(retval) - read_msg.len
                    )
                )
            for i in range(read_msg.len):
                read_msg.buf[i] = retval[i]

        self._xfer_reply(
            i2c_pseudo.i2cp_ioctl_xfer_reply_arg(
                msgs=req_arg.msgs,
                xfer_id=req_arg.output.xfer_id,
                num_msgs=req_arg.output.num_msgs,
                error=0,
            )
        )
        return True

    def _poll_loop(self):
        """Keep polling the I2C pseudo controller in a loop."""
        assert self._state >= _STATE_RUN
        while self._state == _STATE_RUN:
            try:
                epoll_ret = self._epoll.poll()
            except OSError as error:
                if error.errno == errno.EINTR:
                    continue
                raise
            for fd, event in epoll_ret:
                if fd == self._device_fd:
                    while self._attempt_xfer(event):
                        pass

    def _io_thread_run(self):
        """Entry point for thread which handles all I2C pseudo controller I/O.

        This handles both I/O with i2c-pseudo kernel module, and I/O with the Servo
        I2C bus.  Those two sides of this controller could be split into separate
        threads, and the i2c-pseudo side could be further split into separate read
        and write threads, however any performance difference is likely minimal and
        not worth the added complexity.
        """
        assert self._state >= _STATE_RUN
        try:
            self._poll_loop()
        finally:
            self._close_fd()

    def _close_fd(self):
        """Attempt to close self._device_fd."""
        with self._run_lock:
            self._epoll.close()
            if self._device_fd is not None:
                try:
                    os.close(self._device_fd)
                finally:
                    self._device_fd = None

    def get_xfer_counters(self):
        """Get the I2C pseudo controller transfer counters.

        This may only be called after successful start().

        Returns:
            {str: int} - Mapping of counter names to counts.
        """
        assert self._state >= _STATE_RUN
        xfer_counters = i2c_pseudo.i2cp_ioctl_xfer_counters()
        fcntl.ioctl(
            self._device_fd, i2c_pseudo.I2CP_IOCTL_GET_COUNTERS, xfer_counters, True
        )
        # Use field[0] by index instead of unpacking because the tuple may have
        # 2 or 3 items.
        return {
            field[0]: getattr(xfer_counters, field[0])
            for field in xfer_counters._fields_
        }

    def shutdown(self, timeout):
        """Shutdown the I2C pseudo adapter.

        This may be called multiple times, including concurrently, and including after a
        prior call failed with an exception.

        Args:
          timeout: None, int, or float - Wait this many seconds for the I/O thread
              to complete, or None to wait indefinitely.  Use 0 or 0.0 to not wait.

        Returns:
          bool - True if the pseudo controller and its I/O thread stopped before
              expiration of the timeout or was never started, False otherwise.
        """
        with self._run_lock:
            self._state = _STATE_SHUTDOWN
            if self._device_fd is not None:
                fcntl.ioctl(self._device_fd, i2c_pseudo.I2CP_IOCTL_SHUTDOWN)

        if self._io_thread.is_alive() and (timeout is None or timeout > 0):
            self._io_thread.join(timeout=timeout)

        if self._io_thread.is_alive():
            return False

        self._close_fd()
        return True

    def __del__(self):
        self.shutdown(timeout=0)
