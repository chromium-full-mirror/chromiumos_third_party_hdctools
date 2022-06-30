# Copyright 2022 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import http.server
import json
import logging
import os
import socket
import socketserver
import sys

# default port used in the http server
HTTP_SERVER_PORT = 9998

class ThreadedTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    """Create the thread for the TCP server
       Attributes:
           daemon_threads: Default setting is False, set to True to allow
                           the thread terminates when the program stop
           allow_reuse_address: Default setting is False, set to True,
                                to allow binding to exist port
    """
    pass
    def __init__(self, server_address, RequestHandlerClass):
      """ The init function of TCP Treaded"""
      self.daemon_threads = True
      self.allow_reuse_address = True
      
      socketserver.TCPServer.__init__(self, server_address, RequestHandlerClass)
        
class HttpRequestHandler(http.server.SimpleHTTPRequestHandler):
    """The handler can pass the data, check for the availability of the port"""

    def __init__(self, sample_data_container):
        """Initializa the HttpRequestHandler

           Args:
               _sample_data_container: The constructor of generating the sample data,
                                      call the get_sample_container function to fetch
                                      the latest data which need to be passed
                                      to the visualization UI
               _logger: Http Server handler log
        """
        self._sample_data_container = sample_data_container
        self._logger = logging.getLogger(type(self).__name__)

    def __call__(self, *args, **kwargs):
        """Let the handler to be callable"""
        super().__init__(*args, **kwargs)

    def do_POST(self):
        """This function passes the message to the html which connect to the server"""
        power_data = self._sample_data_container.get_data_sample()
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Content-Type', 'text/plain')
        self.send_header("Content-Length", len(power_data))
        self.end_headers()
        self.wfile.write(power_data)

    def do_GET(self):
        """This function passes the message to the html which connect to the server"""
        self.send_response(200)
        message = "The server starts and can work well"
        self.send_header('Content-type', 'text/html')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header("Content-Length", len(message))
        self.end_headers()
        self.wfile.write(bytes(message, "utf8"))

    def is_port_used(self, port):
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
        """This function helps avoid showing the http.server's logging on the console"""
        pass
