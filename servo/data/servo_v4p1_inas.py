# Copyright 2020 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
inas = [
        # TODO(nsanders): Come up with a way to support multiple voltages.
        ('ina231', 0x40, 'ppdut5', 5.0, 0.005, 'rem', True),
        ('ina231', 0x41, 'ppchg5', 5.0, 0.005, 'rem', True),
        ('ina231', 0x42, 'ppservo5', 5.0, 0.005, 'rem', True),
       ]
# TODO(b/197780517)
params = dict(interface=23)
