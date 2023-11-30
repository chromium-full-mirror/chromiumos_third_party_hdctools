#!/usr/bin/env python3
# Copyright 2023 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import json
import os
import pathlib

from servo.common.config.system_config import SystemConfig
from servo.common.proto import system_config_grpc
from servo.common.proto import system_config_pb2
from servo.data.config.servo_file_discover import get_default_config_by_vid_pid


class SystemConfigImpl(system_config_grpc.SystemConfigServicer):

    def GetFileContent(self, systemConfigRequest, context):
        """
        Retrieve and format system configuration data as a response message.

        Args:
            systemConfigRequest (SystemConfigRequest): An object containing configuration request details.
            context: The context of the request.

        Returns:
            SystemConfigResponse: A response message containing formatted system configuration data.
        """
        # Retrieve the system configuration based on the provided message.
        scfg = self.get_system_config(systemConfigRequest)

        # Create a response message of type SystemConfigResponse.
        response = system_config_pb2.SystemConfigResponse()

        # Populate the response message with data from the retrieved system configuration.
        response.systemConfig.add(
            control_tags=json.dumps(scfg.control_tags),
            aliases=json.dumps(scfg.aliases),
            syscfg_dict=json.dumps(scfg.syscfg_dict),
            hwinit=json.dumps(scfg.hwinit)
        )

        # Return the populated response message.
        return response

    def get_system_config(self, systemConfigRequest):
        """
        Retrieve a system configuration based on VID and PID.

        Args:
            systemConfigRequest (SystemConfigRequest): An object containing VID and PID.

        Returns:
            SystemConfig: A SystemConfig object representing the retrieved configuration.
        """
        # Get the default configuration file path based on VID and PID.
        file_path = get_default_config_by_vid_pid(systemConfigRequest.VID, systemConfigRequest.PID)

        # Create an empty SystemConfig object.
        scfg = SystemConfig()

        # Add the configuration file to the SystemConfig object.
        scfg.add_cfg_file("", os.path.join(pathlib.Path(__file__).parent.parent.resolve(), file_path))

        # Return the SystemConfig object with the configuration file added.
        return scfg
