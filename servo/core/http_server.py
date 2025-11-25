# Copyright 2022 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import codecs
import http.server
import logging
import os
from pathlib import Path
import socket
import socketserver


# The position while we are going to save the sample data in html
INSERT_DATA_POSITION = "/* {BEGIN_PARALLAX_DATA_INJECTION} */"
PARALLAX_DATA = "\n const PARALLAX_DATA = "

# default port used in the http server
HTTP_SERVER_PORT = 9998

# Release html which will be used when we need to save it
RELEASE_HTML = "release.html"

# Get the path of 'home/$USER/'
USER_HOME_PATH = Path.home()

# Get the path to visualization html file
VISUALIZATION_RELEASE_HTML_FILE_PATH = (
    str(USER_HOME_PATH) + "/chromiumos/src/platform2/parallax/dist/release.html"
)
VISUALIZATION_REPORT_HTML_FILE_PATH = (
    str(USER_HOME_PATH) + "/chromiumos/src/platform2/parallax/dist/report.html"
)


class ThreadedTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    """Create the thread for the TCP server
    Attributes:
      daemon_threads: Default setting is False, set to True to allow
        the thread terminates when the program stop
      allow_reuse_address: Default setting is False, set to True,
        to allow binding to exist port
    """

    def __init__(self, server_address, RequestHandlerClass):
        """The init function of TCP Treaded"""
        self.daemon_threads = True
        self.allow_reuse_address = True
        socketserver.TCPServer.__init__(self, server_address, RequestHandlerClass)


class _ActualHttpRequestHandler(http.server.SimpleHTTPRequestHandler):
    """The actual handler that processes requests."""

    def __init__(self, request, client_address, server, data_sampler):
        self._data_sampler = data_sampler
        super().__init__(request, client_address, server)

    def do_post(self):
        """This function passes the message to the html which connect to the server"""
        power_data = self._data_sampler.get_data_sample()
        self.send_response(200)
        self.send_header("Access-Control-Allow-Credentials", "true")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Type", "text/plain")
        self.send_header("Content-Length", str(len(power_data)))
        self.end_headers()
        self.wfile.write(power_data.encode("utf_8"))
        # clearing the input bufer
        self.wfile.flush()

    def do_GET(self):
        """This function passes the message to the html which connect to the server"""
        self.send_response(200)
        message = "The server starts and can work well"
        self.send_header("Content-Type", "text/html")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Length", len(message))
        self.end_headers()
        self.wfile.write(bytes(message, "utf8"))
        # clearing the input bufer
        self.wfile.flush()

    def log_request(self, code="-", size="-"):
        """This function helps avoid showing the http.server's logging on the console"""


class HttpRequestHandler:
    """The handler can pass the data, check for the availability of the port"""

    def __init__(self, data_sampler):
        """Initialize the HttpRequestHandler

        Args:
          _data_sampler: A data sampler of generating the sample data for
            the visualization UI
          _logger: Http Server handler log
        """
        self._data_sampler = data_sampler
        self._logger = logging.getLogger(type(self).__name__)

    def __call__(self, request, client_address, server):
        """Let the handler to be callable"""
        return _ActualHttpRequestHandler(
            request, client_address, server, self._data_sampler
        )

    def is_port_used(self, port):
        """A boolean function to check if the specific port is not been used

        Args:
          port: The http server port which need to be check if in use or not

        Returns:
          True: The checking port is in use
          False: The checking port is not in use
        """
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        result = sock.connect_ex(("localhost", port))
        sock.close()
        return result == 0

    def get_visualization_html_exist(self):
        """This function helps to determine if the report.html file exists"""
        if os.path.exists(VISUALIZATION_RELEASE_HTML_FILE_PATH):
            return VISUALIZATION_RELEASE_HTML_FILE_PATH
        if os.path.exists(VISUALIZATION_REPORT_HTML_FILE_PATH):
            return VISUALIZATION_REPORT_HTML_FILE_PATH
        return None

    def save_visualization_html(self, save_path):
        """This function helps to get the text from report.html and do the string concat
        with current power data to generate a copy of report.html and save it

        Args:
          save_path: Provide the path where we can save the copy of html
        """

        # Check if the release.html for saving is existed or not,
        # if not, it means that we are using the report.html which is for developer
        if not os.path.exists(VISUALIZATION_RELEASE_HTML_FILE_PATH):
            self._logger.info(
                "You only has the report.html for the developer, "
                "therefore, you do not have release.html to save, "
                "if you hope to save the html\n"
                "run: npm run build -- release\n"
                "Then, run the program again"
            )
            return

        # Open the html file as text
        html_reader = codecs.open(VISUALIZATION_RELEASE_HTML_FILE_PATH, "r")
        html_content = html_reader.read()

        # Find the place we are going to insert our sample data
        position = html_content.index(INSERT_DATA_POSITION)

        # Remain the up part of html text
        uptext = html_content[0 : position + len(INSERT_DATA_POSITION)]

        # Get the power data
        power_data = self._data_sampler.get_data_sample()
        power_saving_data = PARALLAX_DATA + str(repr(power_data))

        # Remain the bottom part of html text
        downtext = html_content[position + len(INSERT_DATA_POSITION) :]

        # Concat the data
        save_data = uptext + power_saving_data + downtext
        save_html_path = save_path + "/" + RELEASE_HTML

        # Create the file and write the text
        save_html_reader = codecs.open(save_html_path, "w")
        save_html_reader.write(save_data)

        self._logger.info("Save the release.html in %s", save_html_path)
        save_html_reader.close()
        html_reader.close()
