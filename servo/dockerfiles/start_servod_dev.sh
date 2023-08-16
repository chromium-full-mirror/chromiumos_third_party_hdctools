# Copyright 2021 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

#!/bin/bash

set -x

/usr/bin/fwupdtool install --filter="updatable" /usr/local/genesys/GenesysLogic_GL3590_64.17.cab | tr -d ?

# Optionally update the servo firmware, if the firmware is already at the correct
# version this is a no-op
# SERVO_FW_CHANNEL should be one of - stable, beta, dev, prev (it is case sensitive)
# SERVO_TYPE should be one of servo_v4 or servo_v4p1
#if ([ -n "$SERVO_FW_CHANNEL" ] && [ -n "$SERIAL" ] && [ -n "$SERVO_TYPE" ]); then
#    servo_updater -s $SERIAL -c $SERVO_FW_CHANNEL -b $SERVO_TYPE
#fi


servod --host 0.0.0.0 $1
