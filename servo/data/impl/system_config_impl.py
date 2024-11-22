#!/usr/bin/env python3
# Copyright 2023 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import json
import logging

from servo.common.proto import system_config_grpc
from servo.common.proto import system_config_pb2
from servo.data.impl.system_config_service import get_system_config


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
        scfg = get_system_config(vid=systemConfigRequest.VID, pid=systemConfigRequest.PID)

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
    def AddCfgFile(self, request, context):
        """
        Add a file to system config dict.

        Returns:
            SystemConfigResponse: A response message containing formatted system configuration data.
        """
        # Retrieve the system configuration based on the provided message.
        scfg = get_system_config(vid=request.vid, pid=request.pid)
        scfg.add_cfg_file(name_prefix=request.prefix, filename=request.filename)

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

    def IsControl(self, request, context):
        """
        Check if there is a control with specified name

        Returns:
            IsControlResponse: A response message with bool value, true if control exists
        """
        scfg = get_system_config(vid=request.vid, pid=request.pid)
        return system_config_pb2.IsControlResponse(value = scfg.is_control(request.control_name))
