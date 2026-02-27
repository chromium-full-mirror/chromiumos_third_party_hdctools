# Copyright 2026 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
import xmlrpc.client


# The tunnel maps Seabank:9998 -> Local:9999
URL = "http://localhost:9998/"
proxy = xmlrpc.client.ServerProxy(URL)

try:
    print("--- Attempting to list methods ---")
    # Note: some servers require an empty string or no args
    methods = proxy.system.listMethods()
    print(f"Success! Found {len(methods)} methods.")
    for m in methods:
        print(f" - {m}")
except Exception as e:
    print(f"Error: {e}")
