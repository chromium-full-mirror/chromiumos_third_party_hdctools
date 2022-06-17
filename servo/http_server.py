#!/usr/bin/env python2
# Copyright 2022 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import http.server
import os
import socket
import socketserver
import sys

# default port used in the http server
HTTP_SERVER_PORT = 9998

class ThreadedTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    """Create the thread for the TCP server"""
    pass

class HttpRequestHandler(http.server.SimpleHTTPRequestHandler):
    """The http handler which can use for passing the data, check for the availability of the using port"""

    def do_GET(self):
        """This function will pass the message to the html which connect to the http server"""
        # TODO: will replace this with actual APIs for serving measurement jsons and visualization html
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        message = "The server starts and can work well"
        self.wfile.write(bytes(message, "utf8"))

    def check_port(port):
        """A boolean function to check if the specific port is not been used

        Args:
          port: The http server port which need to be check if in use or not

        Returns:
          True: The checking port is in use
          False: The checking port is not in use
        """
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        result = sock.connect_ex(('localhost', port))
        sock.close()
        return result == 0

    def log_request(self, format, *args):
        """This function can help avoid showing the http.server's logging on the console"""
        pass
