#!/usr/bin/env python3
# Copyright 2011 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Helper module to generate system control files for INA adcs."""

import argparse
import copy
import glob
import importlib.util
import json
import os
import re
import sys
import time


# This file is run in a builder setup or command line, and therefore, we need
# to ensure that the current directory is part of the path.
sys.path.append(os.path.dirname(__file__))

# Do not change these to relative imports. This file is mostly run through a
# module import on setup.py, and cannot support relative imports at that point.
from adc_templates import GetTemplate
from servo_config_generator import ServoConfigFileGenerator
from servo_config_generator import ServoControlGenerator
from sweetberry_preprocessor import SweetberryPreprocessor


class INAConfigGeneratorError(Exception):
    """Error class for INA control generation errors."""

    pass


class INAConfigGenerator:
    """Base class for any INA Configuration Generator.

    Shared base class that handles file name logic.

    Attributes:
      _configs_to_generate: a list of configurations that this template produces.
    """

    def __init__(self, module_name, ina_pkg):
        """Init all INA Configuration Generators.

        This sets up the common logic of deciding how many configurations to produce
        based on a given template.

        Args:
          module_name: name of template module
          ina_pkg: template loaded as a module
        """
        self._configs_to_generate = []
        if hasattr(ina_pkg, "revs"):
            # modules need to be named board_[anything].py
            board = re.sub(r"_.*", "", module_name)
            for rev in ina_pkg.revs:
                try:
                    self._configs_to_generate.append("%s_rev%d" % (board, int(rev)))
                except ValueError:
                    raise INAConfigGeneratorError(
                        "Rev: %s has to be an integer." % str(rev)
                    )
        else:
            # if rev doesn't exist, then it's an old-style INA file, in which case
            # this script produces just one control named the same as the module.
            self._configs_to_generate.append(module_name)

    def ExportConfig(self, outdir):
        """Export the configuration(s) of a template to outdir.

        Args:
          outdir: output directory to dump generated configs to

        This is required for each Generator class to implement.
        """
        raise NotImplementedError()


class PowerlogINAConfigGenerator(INAConfigGenerator):
    """Generator to make sweetberry configurations given a template.

    Attributes:
      _board_content = content of string for .board Sweetberry file.
      _scenario_content = content of string for .scenario Sweetberry file.
    """

    def __init__(self, module_name, ina_pkg):
        """Setup Generator by generating file contents as string.

        Args:
          module_name: name of the template module
          ina_pkg: template loaded as a module
        """
        super().__init__(module_name, ina_pkg)
        self._board_content, self._scenario_content = self.DumpADCs(ina_pkg.inas)

    def DumpADCs(self, adcs):
        """Dump json formatted INA231 configurations for powerlog configuration.

        This uses the same adcs template formate as servod (for compatibility)
        but sweetberry configuration only needs child, name, sense, and is_calib.

        Args:
          adcs: array of adc elements.  Each array element is a tuple consisting of:
              drvname: string name of adc driver to enumerate to control the adc
              child: string format '0xAA:B': AA is i2c child addr and B is i2c port
              name: string name of the power rail
              nom: float of nominal voltage of power rail
              sense: float of sense resistor size in ohms
              mux: string name of bank on sweetberry these ADC's live on: j2, j3, j4
              is_calib: boolean to indicate if calibration is possible for this rail
                        if false, no config will be exported

        The adcs list above is in order, meaning this function looks for name at
        adc[2], where adc is the tuple for a particular adc.

        Returns:
          Tuple of (board_content, scenario_content):
            board_content: json list of dictionaries describing INAs used
            scenario_content: json list of INA names in board_content
        """
        adc_list = []
        rails = []
        # pylint: disable=unused-variable
        # continue to properly name variables even if unused here so that in case
        # of future need, developers know what came out of |adcs|
        for drvname, child, name, nom, sense, mux, is_calib in adcs:
            if is_calib:
                addr, port = [int(entry, 0) for entry in child.split(":")]
                adc_list.append(
                    "  %s"
                    % json.dumps(
                        {
                            "name": name,
                            "rs": float(sense),
                            "sweetberry": "A",
                            "addr": addr,
                            "port": port,
                        }
                    )
                )
            rails.append(name)
        adc_lines = ",\n".join(adc_list)
        return ("[\n%s\n]" % adc_lines, json.dumps(rails, indent=2))

    def ExportConfig(self, outdir):
        """Write the configuration files in the outdir.

        Dump the Sweetberry Configuration(s) for this generator.

        Args:
          outdir: Directory to place the configuration files into.
        """
        for outfile in self._configs_to_generate:
            board_outpath = os.path.join(outdir, "%s.board" % outfile)
            scenario_outpath = os.path.join(outdir, "%s.scenario" % outfile)
            with open(scenario_outpath, "w") as f:
                f.write(self._scenario_content)
            with open(board_outpath, "w") as f:
                f.write(self._board_content)


class ServoINAConfigGenerator(INAConfigGenerator):
    """Generator to make servod configurations given a template.

    Attributes:
      _servo_drv_dir = servo directory to check for ina driver.
      _outfile_gen = servo config xml generator.
    """

    def __init__(self, module_name, ina_pkg, servo_data_dir, servo_drv_dir=None):
        """Setup Generator by preparing an xml generator to output entire config.

        Args:
          module_name: name of the template module
          ina_pkg: template loaded as a module
          servo_data_dir: servo data directory to include configs
          servo_drv_dir: servo drv directory to check drv availability

        Raises:
          INAConfigGeneratorError: if a a non-int interface is defined in |ina_pkg|
        """
        super().__init__(module_name, ina_pkg)
        if not servo_drv_dir:
            # The drivers were moved from servo/data/drv to servo/drv
            servo_drv_dir = os.path.join(os.path.dirname(servo_data_dir), "drv")
        self._servo_drv_dir = servo_drv_dir
        power_tools_cfg = os.path.join(servo_data_dir, "power_tools.xml")
        ina2xx_drv_cfg = os.path.join(servo_data_dir, "ina2xx.xml")
        # Note: the 'interface' attribute is to support an old API that allowed
        # users to specify a specific interface if it was not default.
        # The modern API is to include that in the 'params' attribute.
        if hasattr(ina_pkg, "interface"):
            interface = ina_pkg.interface
            if not isinstance(interface, int):
                raise INAConfigGeneratorError(
                    "Invalid interface %r, should be int." % interface
                )
        else:
            interface = 2  # default I2C interface

        if hasattr(ina_pkg, "params"):
            params = ina_pkg.params
        else:
            params = {}
        if not isinstance(params, dict):
            raise INAConfigGeneratorError(
                "Invalid params %r, should be a dict." % params
            )
        # package the interface into params
        if "interface" not in params:
            params["interface"] = interface

        comments = "Autogenerated on %s" % time.asctime()
        includes = []
        body = ""

        if os.path.isfile(power_tools_cfg):
            includes.append(os.path.basename(power_tools_cfg))
        if os.path.isfile(ina2xx_drv_cfg):
            includes.append(os.path.basename(ina2xx_drv_cfg))
        if hasattr(ina_pkg, "inline"):
            inline = ina_pkg.inline
        else:
            inline = ""

        ctrl_gens = self.DumpADCs(ina_pkg.inas, params)
        self._outfile_gen = ServoConfigFileGenerator(
            ctrl_generators=ctrl_gens,
            includes=includes,
            inline=inline,
            intro_comments=comments,
        )

    def DumpADCs(self, adcs, params):
        """Dump XML formatted INAxxx adcs for servod.

        Args:
          adcs: array of adc elements.  Each array element is a tuple consisting of:
              drvname: string name of adc driver to enumerate to control the adc.
              child: int representing the i2c child address.
                   optional channel/port if ADC (INA3221 only) has multiple channels
                   or adc is on a different i2c port (sweetberry only). For example,
                     "0x40"   : address 0x40 ... no channel/port
                     "0x40:1" : address 0x40, channel/port 1
              name: string name of the power rail
              nom: float of nominal voltage of power rail.
              sense: float of sense resistor size in ohms
              mux: string name of i2c mux leg these ADC's live on
              is_calib: boolean to indicate if calibration is possible for this rail
          params: a dictionary of extra params to feed into servod control
                  generation. Must contain `interface`

        The adcs list above is in order, meaning this function looks for name at
        adc[2], where adc is the tuple for a particular adc.

        Returns:
          string (large) of XML for the system config of these ADCs to eventually be
          parsed by servod daemon ( servo/system_config.py )
        """
        control_generators = []
        # Pop out interface as we might rewrite it later depending on the servo
        # device
        if "interface" not in params:
            raise INAConfigGeneratorError(
                "Please provide a servod interface "
                "in the |params| to generate ADC ctrls"
            )
        interface = params.pop("interface")
        for drvname, child, name, nom, sense, mux, is_calib in adcs:
            drvpath = os.path.join(self._servo_drv_dir, drvname + ".py")
            if not os.path.isfile(drvpath):
                raise INAConfigGeneratorError(
                    "Unable to locate driver for %s at %s" % (drvname, drvpath)
                )
            ina_type = drvname
            addr = child
            # Only some types of ADCs support this extra information.
            i2c_port = 0
            channel = 0

            if ina_type in ["ina3221", "pac1934", "pac1954"]:
                addr, channel = addr.split(":")
            elif ina_type == "ina231" and type(addr) == str and ":" in addr:
                # This only happens on sweetberry configurations. This is to report
                # which i2c port the ina219 is on.
                addr, i2c_port = addr.split(":")
            # Convert all to integers as needed.
            if not isinstance(addr, int):
                # Some config files are written with the integer directly, and not a
                # hex string. Those should not be converted.
                addr = int(addr, 16)
            i2c_port = int(i2c_port)
            channel = int(channel)
            # The template is used to get the parameters for all the register
            # controls.
            adc_temp = GetTemplate(ina_type)(addr, channel)
            for suffix, ctrl_params in adc_temp.GetFunctionalParams(sense).items():
                if not is_calib and suffix in ["ma", "mw", "avg_mw"]:
                    # in some instances we may not know sense resistor size ( re-work ),
                    # the size might be 0, or other custom factors may not allow for
                    # calibration and those reliable readings on the current and power
                    # registers.
                    # This boolean determines which controls should be enumerated based
                    # on rails input specification.
                    continue
                # Nominal voltage is just informational. Add it here to maintain
                # same interface as before, but TODO: consider if this info is needed at
                # all.
                ctrl_params["nom"] = nom
                # Let the controls know about their own channel
                ctrl_params["channel"] = channel
                # Provide the rails with access to the 'base name' so that they
                # can find register controls for their own ADC by symbolic name
                ctrl_params["base_name"] = name
                docstring = adc_temp.FUNC_DOCSTRING_TEMPLATES[suffix] % name
                cname = "%s_%s" % (name, suffix)
                control_generators.append(
                    ServoControlGenerator(cname, docstring, ctrl_params)
                )
            # Only sweetberry has |i2c_port| as non-zero. In that case, the actual
            # interface is |interface| (2) + i2c_port
            # |einterface| stands for effective interface.
            einterface = interface + i2c_port
            for reg, reg_params in adc_temp.GetRegisterParams(einterface).items():
                docstring = "Raw register value of %s on i2c_mux:%s" % (reg, mux)
                ctrl_name = "%s_%s_reg" % (name, reg)
                # We need to supplement the register params with params fed
                # in.
                reg_params.update(params)
                control_generators.append(
                    ServoControlGenerator(ctrl_name, docstring, reg_params)
                )
        return control_generators

    def ExportConfig(self, outdir):
        """Write the configuration files in the outdir.

        Dump the XML Servo Configuration(s) for this generator.

        Args:
          outdir: Directory to place the configuration files into.
        """
        for outfile in self._configs_to_generate:
            outfile_dest = os.path.join(outdir, "%s.xml" % outfile)
            self._outfile_gen.WriteToFile(outfile_dest)


def GenerateINAControls(
    servo_data_dir, servo_drv_dir=None, outdir=None, export=True, candidates=[]
):
    """Attempt to generate INA configurations for all modules.

    Generates the configuration for every module found inside
    |self._servo_data_dir| during init.

    Optionally also provide where to write configurations to, and where to
    look for servo drv files if not at known location.

    Args:
      servo_data_dir: directory where to look for .py files to generate
                      controls.
      servo_drv_dir: directory where servo drivers are. Used to verify
                     that defined controls have a driver they can use.
                     If |None|, generator will look for drivers at
                     servo_data_dir/../drv/ (i.e. servo/drv/)
      outdir: directory where to dump generated configuration files.
              If |None|, config files are dumped into |servo_data_dir|
      export: if True config files will be exported to |outdir|
              if False it's only a dry-run to detect errors
      candidates: list of files in |servo_data_dir| to generate configs for.
                  if empty, all files in |servo_data_dir| will be considered.
    """
    if not outdir:
        outdir = servo_data_dir
    generators = []
    if not candidates:
        candidates = os.listdir(servo_data_dir)
    for candidate in candidates:
        if candidate.endswith(".py"):
            module_name = candidate[:-3]
            spec = importlib.util.spec_from_file_location(module_name, os.path.join(servo_data_dir, candidate))
            ina_pkg = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(ina_pkg)
            if not hasattr(ina_pkg, "inas"):
                continue
            if hasattr(ina_pkg, "config_type"):
                config_type = ina_pkg.config_type
            else:
                # If config_type is not defined, it is a servod config
                config_type = "servod"
            if config_type not in ["sweetberry", "servod"]:
                raise INAConfigGeneratorError("Unknown config type %s" % config_type)
            if config_type == "sweetberry":
                # translate inas from pin-style to i2c-addr style config (if applicable)
                ina_pkg.inas = SweetberryPreprocessor.Preprocess(ina_pkg.inas)
                # also output powerlog config files (.board/.scenario)
                generators.append(PowerlogINAConfigGenerator(module_name, ina_pkg))
            # always output Servod configurations
            generators.append(
                ServoINAConfigGenerator(
                    module_name, ina_pkg, servo_data_dir, servo_drv_dir
                )
            )
    if export:
        for generator in generators:
            generator.ExportConfig(outdir)


def main(cmdline=sys.argv[1:]):
    """cmdline interface to generate &| verify config files.

    Args:
      cmdline: sys command line args (without the program name)

    Note: This is mainly intended as a development tool to verify a new or
    modified powermap before submitting it, and without having to build the full
    hdctools.
    """
    parser = argparse.ArgumentParser(
        description="cmdline tool to generate and "
        "validate servod power configurations."
    )
    parser.add_argument(
        "--dry-run",
        default=False,
        action="store_true",
        help="Do not export files, only verify that no errors "
        "on config generation occur.",
    )
    parser.add_argument(
        "-i",
        "--input",
        action="store",
        default=os.path.dirname(__file__),
        help="file or directory to perform conversions on.",
    )
    args = parser.parse_args(cmdline)
    if os.path.isdir(args.input):
        servo_data_dir = args.input
        candidates = glob.glob(os.path.join(servo_data_dir, "*.py"))
    if os.path.isfile(args.input):
        servo_data_dir = os.path.dirname(args.input)
        candidates = [args.input]
    # having only the basename is required for load_module to work better
    candidates = [os.path.basename(candidate) for candidate in candidates]
    # if dry_run is set then we don't want to export.
    export = not args.dry_run
    for candidate in candidates:
        try:
            GenerateINAControls(
                servo_data_dir=servo_data_dir, export=export, candidates=[candidate]
            )
            msg_prefix = "Success:"
        except Exception as e:
            msg_prefix = "FAILURE: %s" % e.message
            return 1
        print("%s for candidate file %s" % (msg_prefix, candidate))

    return 0


if __name__ == "__main__":
    main()
