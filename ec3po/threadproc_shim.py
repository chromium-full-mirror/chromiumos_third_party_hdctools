# Copyright 2018 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""This is a shim library for the ec3po transition from subprocesses to threads.

This is necessary because ec3po is split between the platform/ec/ and
third_party/hdctools/ repositories, so the transition cannot happen atomically
in one change.  See http://b/79684405 #39.

This contains only the multiprocessing objects or threading-oriented equivalents
that are actually in use by ec3po.  There is no need for further functionality,
because this shim will be deleted after the migration is complete.

TODO(b/79684405): Stop using multiprocessing.Pipe.  The
multiprocessing.Connection objects it returns serialize and deserialize objects
(via Python pickling), which is necessary for sending them between processes,
but is unnecessary overhead between threads.  This will not be a simple change,
because the ec3po Console and Interpreter classes use the underlying pipe/socket
pairs with select/poll/epoll alongside other file descriptors.  A drop-in
replacement would be non-trivial and add undesirable complexity.  The correct
solution will be to split off the polling of the pipes/queues from this module
into separate threads, so that they can be transitioned to another form of
cross-thread synchronization, e.g. directly waiting on queue.Queue.get() or a
lower-level thread synchronization primitive.

TODO(b/79684405): After this library has been updated to contain
threading-oriented equivalents to its original multiprocessing implementations,
and some reasonable amount of time has elapsed for thread-based ec3po problems
to be discovered, migrate both the platform/ec/ and third_party/hdctools/ sides
of ec3po off of this shim and then delete this file.  IMPORTANT: This should
wait until after completing the TODO above to stop using multiprocessing.Pipe!
"""

from queue import Queue  # pylint: disable=unused-import
import select
import socket
from threading import Thread as ThreadOrProcess  # pylint: disable=unused-import


# True if this module has ec3po using subprocesses, False if using threads.
USING_SUBPROCS = False


class SocketConnection:
    """A socket-based mock of multiprocessing.connection.Connection.

    It sends bytes directly without the pickling/unpickling serialization overhead
    of multiprocessing.Pipe, which is highly resource-intensive and unnecessary
    for cross-thread communication.
    """

    def __init__(self, sock, readable=True, writable=True):
        self._sock = sock
        self._readable = readable
        self._writable = writable

    def send(self, data):
        """Sends bytes via the underlying socket."""
        if not self._writable:
            raise OSError("Connection is not writable")
        if not isinstance(data, bytes):
            raise TypeError(
                "SocketConnection only supports sending bytes (to bypass pickling)."
            )
        self._sock.sendall(data)

    def recv(self, maxsize=4096):
        """Receives bytes from the underlying socket."""
        if not self._readable:
            raise OSError("Connection is not readable")
        data = self._sock.recv(maxsize)
        if not data:
            raise EOFError
        return data

    def poll(self, timeout=0.0):
        """Returns True if there is data available to read."""
        if not self._readable:
            raise OSError("Connection is not readable")
        r, _w, _x = select.select([self._sock], [], [], timeout)
        return bool(r)

    def fileno(self):
        """Returns the file descriptor for epoll integration."""
        return self._sock.fileno()

    def close(self):
        """Closes the underlying socket."""
        self._sock.close()


# pylint: disable=invalid-name
def Pipe(duplex=True):
    """Returns a pair of connected SocketConnection objects."""
    s1, s2 = socket.socketpair()
    if duplex:
        return SocketConnection(s1), SocketConnection(s2)
    # A non-duplex Pipe returns (read_only, write_only)
    return SocketConnection(s1, writable=False), SocketConnection(s2, readable=False)


def _do_nothing():
    """Do-nothing function for use as a callback with do_if()."""


def do_if(subprocs=_do_nothing, threads=_do_nothing):
    """Return a callback or not based on ec3po use of subprocesses or threads.

    Args:
      subprocs: callback that does not require any args - This will be returned
          (not called!) if and only if ec3po is using subprocesses.  This is
          OPTIONAL, the default value is a do-nothing callback that returns None.
      threads: callback that does not require any args - This will be returned
          (not called!) if and only if ec3po is using threads.  This is OPTIONAL,
          the default value is a do-nothing callback that returns None.

    Returns:
      Either the subprocs or threads argument will be returned.
    """
    return subprocs if USING_SUBPROCS else threads


def value(ctype, *args):
    return ctype(*args)
