#!/usr/bin/env python3
# Copyright 2023 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import json

from servo.common.config.system_config import SystemConfig
from servo.common.proto import system_config_grpc
from servo.common.proto import system_config_pb2
from servo.common.utils.grpc_log_capture import LogCaptureContext
from servo.data import servo_interfaces
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
        scfg = get_system_config(
            vid=systemConfigRequest.VID,
            pid=systemConfigRequest.PID,
            serial=systemConfigRequest.serial,
        )

        # Create a response message of type SystemConfigResponse.
        response = system_config_pb2.SystemConfigResponse()

        # Populate the response message with data from the retrieved system configuration.
        # Convert sets to lists for JSON serialization.
        serializable_tags = {k: list(v) for k, v in scfg.control_tags.items()}
        response.systemConfig.add(
            control_tags=json.dumps(serializable_tags),
            aliases=json.dumps(scfg.aliases),
            syscfg_dict=json.dumps(scfg.syscfg_dict),
            hwinit=json.dumps(scfg.hwinit),
        )

        # Return the populated response message.
        return response

    def AddCfgFile(self, request, context):
        """
        Add a file to system config dict.

        Returns:
            SystemConfigResponse: A response message containing formatted system configuration data.
        """
        with LogCaptureContext() as loglines:
            # Retrieve the system configuration based on the provided message.
            scfg = get_system_config(
                vid=request.vid, pid=request.pid, serial=request.serial
            )
            scfg.add_cfg_file(name_prefix=request.prefix, filename=request.filename)

            # Create a response message of type SystemConfigResponse.
            response = system_config_pb2.SystemConfigResponse()

            # Populate the response message with data from the retrieved system configuration.
            # Convert sets to lists for JSON serialization.
            serializable_tags = {k: list(v) for k, v in scfg.control_tags.items()}
            response.systemConfig.add(
                control_tags=json.dumps(serializable_tags),
                aliases=json.dumps(scfg.aliases),
                syscfg_dict=json.dumps(scfg.syscfg_dict),
                hwinit=json.dumps(scfg.hwinit),
            )
            response.loglines.extend(loglines)

            # Return the populated response message.
            return response

    def IsControl(self, request, context):
        """
        Check if there is a control with specified name

        Returns:
            IsControlResponse: A response message with bool value, true if control exists
        """
        scfg = get_system_config(
            vid=request.vid, pid=request.pid, serial=request.serial
        )
        return system_config_pb2.IsControlResponse(
            value=scfg.is_control(request.control_name)
        )

    def GetControlDoc(self, request, context):
        """
        Get doc string for a control.
        """
        scfg = get_system_config(
            vid=request.vid, pid=request.pid, serial=request.serial
        )
        response = system_config_pb2.ControlDocResponse()
        if scfg.is_control(request.name):
            response.doc = scfg.get_control_docstring(request.name)
        return response

    def GetInitControls(self, request, context):
        """
        Get list of controls for hardware initialization.
        """
        scfg = get_system_config(
            vid=request.vid, pid=request.pid, serial=request.serial
        )
        response = system_config_pb2.InitControlsResponse()
        response.hwinit_json = json.dumps(scfg.hwinit)
        return response

    def GetDisplayConfig(self, request, context):
        """
        Get display config.
        """
        scfg = get_system_config(
            vid=request.vid, pid=request.pid, serial=request.serial
        )
        response = system_config_pb2.DisplayConfigResponse()
        response.display_config = scfg.display_config()
        return response

    def Finalize(self, request, context):
        """
        Finalize configuration setup.
        """
        scfg = get_system_config(
            vid=request.vid, pid=request.pid, serial=request.serial
        )
        scfg.finalize()
        return system_config_pb2.FinalizeResponse(value=True)

    def GetBoardModelConfig(self, request, context):
        """
        Get board/model config file.
        """
        scfg = get_system_config(
            vid=request.vid, pid=request.pid, serial=request.serial
        )
        board_config, board_id = scfg.get_board_model_config(
            board=request.board, model=request.model
        )
        return system_config_pb2.BoardModelConfigResponse(
            board_config=board_config if board_config else "",
            board_id=board_id if board_id else "",
        )

    def GetAvailableModels(self, request, context):
        """
        Get available models for a board.
        """
        scfg = SystemConfig()
        models = scfg.get_available_models(board=request.board)
        return system_config_pb2.AvailableModelsResponse(models=models)

    def GetAllControls(self, request, context):
        """
        Get all control names.
        """
        scfg = get_system_config(
            vid=request.vid, pid=request.pid, serial=request.serial
        )
        # Assuming get_all_controls returns a list of strings
        controls = scfg.get_all_controls()
        return system_config_pb2.GetAllControlsResponse(
            controls_json=json.dumps(list(controls))
        )

    def GetControlStr(self, request, context):
        """
        Get doc string for a control (formatted).
        """
        scfg = get_system_config(
            vid=request.vid, pid=request.pid, serial=request.serial
        )
        # SystemConfig.get_control_str(name)
        doc = scfg.get_control_str(request.name)
        return system_config_pb2.ControlStrResponse(doc=doc)

    def GetControlsForTag(self, request, context):
        """
        Get controls for a tag.
        """
        scfg = get_system_config(
            vid=request.vid, pid=request.pid, serial=request.serial
        )
        controls = scfg.get_controls_for_tag(request.tag)
        return system_config_pb2.ControlsForTagResponse(
            controls_json=json.dumps(list(controls))
        )

    def GetConfigFiles(self, request, context):
        """
        Get loaded config files.
        """
        scfg = get_system_config(
            vid=request.vid, pid=request.pid, serial=request.serial
        )
        return system_config_pb2.ConfigFilesResponse(
            files=[entry[0] for entry in scfg._loaded_xml_files]
        )

    def DumpToXml(self, request, context):
        """Dump the system config to a file."""
        scfg = get_system_config(
            vid=request.vid, pid=request.pid, serial=request.serial
        )
        scfg.dump_to_xml(request.filename)
        return system_config_pb2.DumpToXmlResponse(value=True)

    def GetServoInterfaces(self, request, context):
        """
        Get servo interfaces based on VID/PID/Board.
        """
        # Default behavior: look up in INTERFACE_DEFAULTS
        interfaces = servo_interfaces.INTERFACE_DEFAULTS[request.vid][request.pid]

        # Check for board-specific overrides
        if request.board:
            if (
                request.board in servo_interfaces.INTERFACE_BOARDS
                and request.vid in servo_interfaces.INTERFACE_BOARDS[request.board]
                and request.pid
                in servo_interfaces.INTERFACE_BOARDS[request.board][request.vid]
            ):
                interfaces = servo_interfaces.INTERFACE_BOARDS[request.board][
                    request.vid
                ][request.pid]

        return system_config_pb2.ServoInterfacesResponse(
            interface_list_json=json.dumps(interfaces)
        )

    def GetControlManifest(self, request, context):
        scfg = get_system_config(vid=request.VID, pid=request.PID, serial=request.serial)
        response = system_config_pb2.ManifestResponse()
        for control_name in scfg.get_all_controls():
            ctrl_def = response.controls.add()
            ctrl_def.name = control_name
            ctrl_def.doc = scfg.get_control_docstring(control_name)

            # Infer readonly/writeonly from syscfg dict
            get_params, set_params = scfg.lookup_control_params(control_name)

            get_defined = get_params and get_params.get("drv") != "undefined"
            set_defined = set_params and set_params.get("drv") != "undefined"

            ctrl_def.read_only = get_defined and not set_defined
            ctrl_def.write_only = set_defined and not get_defined

            ctrl_def.get_type = get_params.get("input_type", "str") if get_params else ""
            ctrl_def.set_type = set_params.get("input_type", "str") if set_params else ""

        return response
