# Copyright 2022 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Servo Device Templates."""

import collections
import logging
import pathlib

from google.protobuf import text_format

from servo.common.proto import servo_dev_pb2 as ServoDeviceProto


# Protobuf text file path
_TEXTPROTO_PATH = (
    str(pathlib.Path(__file__).parent.resolve())
    + "/../common/proto/servo_dev_info.textproto"
)

# Main devices have an empty prefix. This constant here is to make those checks
# uniform.
MAIN_DEV_PREFIX = "main"
# This alias is used for the main device on servo_server (the device w  ithout a
# prefix) to allow for precise routing and server controls that need to indicate
# which device they want things to happen on.
MAIN_DEV_PREFIX_ALIAS = ""
MAIN_DEV_PREFIXES = [MAIN_DEV_PREFIX, MAIN_DEV_PREFIX_ALIAS]

# The root hub device of the main device gets the prefix 'root'
ROOT_DEV_PREFIX = "root"

# SERVO_VID_PID_TEMPLATE_MAP, SERVO_LOTID_TEMPLATE_MAP, SERVO_ID_DEFAULTS,
# and SERVO_NAME_TEMPLATE_MAP, get populated when protobufs are read from to keep
# a single source of truth about the device information - their template classes.
#
# A 2d map to fetch a servo device template given a vendor id and a product id.
SERVO_VID_PID_TEMPLATE_MAP = collections.defaultdict(
    lambda: collections.defaultdict(set)
)
# A dict to fetch a servo device template given a lot id.
SERVO_LOTID_TEMPLATE_MAP = collections.defaultdict(set)
# A set of tuples of the vid/pid pairs of all known servo devices.
SERVO_ID_DEFAULTS = set()
# A map from name to template.
SERVO_NAME_TEMPLATE_MAP = {}

# Lot IDs are used to distinguish between servo v2 and servo v2 r0. If a device
# has a lot-id that is not known, it gets assigned a fake lot id to ensure that
# it registers as v2 as after a while all the new(er) lotids are v2.
_FORCE_V2_LOTID = "force-v2-lotid"


class DeviceTemplateError(Exception):
    """Error class for device templates."""


def get_template_class_by_name(name):
    """Get the ServoDevTemplate protobuf message class associated with |name|.

    Args:
      name: str, should match a TYPE field of the classes below

    Returns:
      servo dev template protobuf message class associated with |name|

    Raises:
      DeviceTemplateError if template message class not found
    """
    if name not in SERVO_NAME_TEMPLATE_MAP:
        raise DeviceTemplateError("Unknown servo device %r type" % name)
    return SERVO_NAME_TEMPLATE_MAP[name]


def get_template_class(vid, pid, serial=None):
    """Get the ServoDevTemplate message class associated with (vid, pid, serial).

    Note: the serialname is only used when (vid, pid) leave ambiguity (more than
    one template class) and the serialname is needed to determine the lot-id

    Args:
      vid: vendor id for a servo device
      pid: product id for a servo device
      serial: serialname of servo device in question

    Returns:
      servo dev template protobuf message class associated with (vid, pid, serial)

    Raises:
      DeviceTemplateError: If template message class not found, or not uniquely
                           identified
    """
    dev_class_candidates = SERVO_VID_PID_TEMPLATE_MAP[vid][pid].copy()
    if len(dev_class_candidates) > 1:
        # Might need the lotid to distinguish what device is used.
        if serial:
            try:
                lotid, _unused = serial.split("-")
                logging.info("Retrieved lot-id %r for sid: %r.", lotid, serial)
            except ValueError:
                logging.debug("Could not retrieve lot-id for sid: %r.", serial)
                lotid = ""
            if lotid not in SERVO_LOTID_TEMPLATE_MAP:
                # This usually means that it's a servo-v2 and not servo-v2-r0, so
                # assign a fake lot-id to force servo-v2.
                logging.info(
                    "Lotid %r not in lotid map. Assigning fake lot id "
                    "to force servo v2 selection.",
                    lotid,
                )
                lotid = _FORCE_V2_LOTID
            dev_class_candidates &= SERVO_LOTID_TEMPLATE_MAP[lotid]
    dev_str = "[%04x:%04x%s]" % (vid, pid, " " + serial if serial else "")
    if not dev_class_candidates:
        logging.error("Could not find a ServoDev class for %s.", dev_str)
        return None
    if len(dev_class_candidates) > 1:
        logging.error(
            "Multiple ServoDev template classes found for %s. This "
            "should not happen.",
            dev_str,
        )
        for dev_class in dev_class_candidates:
            logging.error("Found ServoDev template class %s", dev_class.__name__)
        return None
    return get_template_class_by_name(dev_class_candidates.pop())


def get_id(name):
    """Get the ID from the servo class associated with |name|.

    Args:
      name: str, should match a TYPE field of protobuf message class

    Returns:
      id: set((int) vid, (int) pid)

    Raises:
      DeviceTemplateError if ID not found for |name|
    """
    if name not in SERVO_NAME_TEMPLATE_MAP:
        raise DeviceTemplateError("Unknown servo device %r type" % name)
    dev = SERVO_NAME_TEMPLATE_MAP[name]
    return (dev.VID, dev.PID)


def get_vid(name):
    """Get the VID from the servo class associated with |name|.

    Args:
      name: str, should match a TYPE field of protobuf message class

    Returns:
      vid: int

    Raises:
      DeviceTemplateError if VID not found for |name|
    """
    if name not in SERVO_NAME_TEMPLATE_MAP:
        raise DeviceTemplateError("Unknown servo device %r type" % name)
    dev = SERVO_NAME_TEMPLATE_MAP[name]
    return dev.VID


def get_pid(name):
    """Get the PID from the servo class associated with |name|.

    Args:
      name: str, should match a TYPE field of protobuf message class

    Returns:
      pid: int

    Raises:
      DeviceTemplateError if PID not found for |name|
    """
    if name not in SERVO_NAME_TEMPLATE_MAP:
        raise DeviceTemplateError("Unknown servo device %r type" % name)
    dev = SERVO_NAME_TEMPLATE_MAP[name]
    return dev.PID


def get_all_servo_ids():
    """Get a set of types of the vid/pid pairs of all known servo devices.

    Returns:
      all_servo_ids: set((int vid1, int pid1), (int vid2, int pid2)...)
    """
    return SERVO_ID_DEFAULTS


def _init_maps(device_list):
    """Helper to initialize the vid/pid/lotid maps for easy retrieval.
    This helper gets called on protobuf import to populate the vid/pid/lotid
    maps with the right classes, to facilitate retrieval of the template class.

    Args:
      device_list: list of protobuf messages containing servo device info
    """
    for device in device_list.servo_devices:
        # Link to the name
        SERVO_NAME_TEMPLATE_MAP[device.TYPE] = device
        if device.VID and device.PID:
            # This means the device refers to a physical servo device.
            # Generate the servo device ID - (vid, pid)
            device_id = (device.VID, device.PID)
            # Populate the SERVO_ID_DEFAULTS set
            SERVO_ID_DEFAULTS.add(device_id)
            # Populate the lookup maps to allow for retrieval.
            SERVO_VID_PID_TEMPLATE_MAP[device.VID][device.PID].add(device.TYPE)
            if device.LOTIDS:
                for lotid in device.LOTIDS:
                    SERVO_LOTID_TEMPLATE_MAP[lotid].add(device.TYPE)


def _read_text_proto(file_path):
    """Retrieve values from the TextProto file

    Args:
      file_path: str, path to the .textproto file

    Returns:
      device_templates: a message containing a protocol message
    """
    with open(file_path, "rb") as file:
        return text_format.Parse(file.read(), ServoDeviceProto.ServoDeviceList())


# Import servo device info and initialize maps
device_templates = _read_text_proto(_TEXTPROTO_PATH)
_init_maps(device_templates)
# Servo types used to categorize servo devices
DEBUG_HEADER_SERVO_TYPES = set(["servo_micro", "servo_v2", "c2d2"])
CCD_SERVO_TYPES = set(["ccd_cr50", "ccd_gsc", "ccd_gsc_nt"])
