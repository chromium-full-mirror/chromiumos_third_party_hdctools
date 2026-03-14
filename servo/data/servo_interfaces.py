# Copyright 2011 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Defines the interfaces for the different servo models."""

import collections


INTERFACE_DEFAULTS = collections.defaultdict(dict)

# servo V2
# Empty interface 1 == JTAG via openocd
# Empty interface 5,6 == SPI via flashrom
# ec3po_uart interface 9,10 == usbpd console, ec console.
SERVO_V2_DEFAULTS = [(0x18D1, 0x5002)]
for vid, pid in SERVO_V2_DEFAULTS:
    INTERFACE_DEFAULTS[vid][pid] = [
        "empty",
        "ftdi_empty",  # 1
        "ftdi_i2c",  # 2
        "ftdi_uart",  # 3: uart3/legacy
        "ftdi_uart",  # 4: ATMEGA
        "ftdi_empty",  # 5
        "ftdi_empty",  # 6
        "ftdi_uart",  # 7: EC
        "ftdi_uart",  # 8: AP
        {
            "name": "ec3po_uart",  # 9: EC3PO(USBPD)
            "raw_pty": "raw_usbpd_uart_pty",
            "source": "PD/Cr50",
        },
        {
            "name": "ec3po_uart",  # 10: EC3PO(EC)
            "raw_pty": "raw_ec_uart_pty",
            "source": "EC",
        },
        {
            "name": "ec3po_uart",  # 11: EC3PO(AP)
            "raw_pty": "raw_cpu_uart_pty",
            "source": "CPU",
        },
    ]


# pacman servod configs
PACMAN_DEFAULTS = [(0x18D1, 0x5211)]
for vid, pid in PACMAN_DEFAULTS:
    INTERFACE_DEFAULTS[vid][pid] = [
        "empty",
        "empty",
        {"name": "ftdi_i2c", "interface": 1},  # 2: FTDI i2c 0/interface 1
    ]

# ftdi generic 4232H
FTDI4232H_MODULE_DEFAULTS = [(0x0403, 0x6011)]
for vid, pid in FTDI4232H_MODULE_DEFAULTS:
    INTERFACE_DEFAULTS[vid][pid] = [
        "empty",
        "empty",  # 1
        {"name": "ftdi_i2c", "interface": 1},  # 2: FTDI i2c 0/interface 0
        "empty",  # 3
        {"name": "ftdi_i2c", "interface": 2},  # 4: FTDI i2c 1/interface 1
    ]

# Ryu Raiden CCD
RAIDEN_DEFAULTS = [(0x18D1, 0x500F)]
for vid, pid in RAIDEN_DEFAULTS:
    INTERFACE_DEFAULTS[vid][pid] = [
        "empty",
        {"name": "stm32_uart", "interface": 0},  # 1: EC_PD
        {"name": "stm32_uart", "interface": 1},  # 2: AP
        "empty",  # 3
        "empty",  # 4
        "empty",  # 5
        "empty",  # 6
        "empty",  # 7
        "empty",  # 8
        "empty",  # 9
        {
            "name": "ec3po_uart",  # 10: dut ec console
            "raw_pty": "raw_ec_uart_pty",
            "source": "EC",
        },
        "empty",  # 11
    ]


# cr50 CCD
CCD_CR50_DEFAULTS = [(0x18D1, 0x5014)]
for vid, pid in CCD_CR50_DEFAULTS:
    INTERFACE_DEFAULTS[vid][pid] = [
        "empty",
        {"name": "stm32_uart", "interface": 0},  # 1: Cr50 console
        {"name": "stm32_i2c", "interface": 5},  # 2: i2c
        "empty",  # 3
        "empty",  # 4
        "empty",  # 5
        "empty",  # 6
        {"name": "stm32_uart", "interface": 2},  # 7: EC/PD
        {"name": "stm32_uart", "interface": 1},  # 8: AP
        {
            "name": "ec3po_uart",  # 9: EC3PO(Cr50)
            "raw_pty": "raw_cr50_uart_pty",
            "source": "Cr50",
        },
        {
            "name": "ec3po_uart",  # 10: EC3PO(EC)
            "raw_pty": "raw_ec_uart_pty",
            "source": "EC",
        },
        {
            "name": "ec3po_uart",  # 11: EC3PO(AP)
            "raw_pty": "raw_cpu_uart_pty",
            "source": "CPU",
        },
    ]

# ti50 CCD - Both DT (0x504A) and NT (0x5066) are supported.
CCD_TI50_DEFAULTS = [(0x18D1, 0x504A), (0x18D1, 0x5066)]
for vid, pid in CCD_TI50_DEFAULTS:
    INTERFACE_DEFAULTS[vid][pid] = [
        "empty",
        {"name": "stm32_uart", "interface": 0},  # 1: Ti50 console
        {"name": "stm32_i2c", "interface": 5},  # 2: i2c
        "empty",  # 3
        "empty",  # 4
        "empty",  # 5
        {"name": "stm32_uart", "interface": 6},  # 6: FPMCU
        {"name": "stm32_uart", "interface": 2},  # 7: EC/PD
        {"name": "stm32_uart", "interface": 1},  # 8: AP
        {
            "name": "ec3po_uart",  # 9: EC3PO(Cr50)
            "raw_pty": "raw_cr50_uart_pty",
            "source": "Cr50",
        },
        {
            "name": "ec3po_uart",  # 10: EC3PO(EC)
            "raw_pty": "raw_ec_uart_pty",
            "source": "EC",
        },
        {
            "name": "ec3po_uart",  # 11: EC3PO(AP)
            "raw_pty": "raw_cpu_uart_pty",
            "source": "CPU",
        },
        {
            "name": "ec3po_uart",  # 12: EC3PO(FPMCU)
            "raw_pty": "raw_fpmcu_uart_pty",
            "source": "FPMCU",
        },
    ]

CCD_DEFAULTS = CCD_CR50_DEFAULTS + CCD_TI50_DEFAULTS

# Sweetberry
SWEETBERRY_ID_DEFAULTS = [(0x18D1, 0x5020)]
for vid, pid in SWEETBERRY_ID_DEFAULTS:
    INTERFACE_DEFAULTS[vid][pid] = [
        "empty",
        "empty",
        {"name": "stm32_i2c", "interface": 3},  # 2: i2c bus 0
        {"name": "stm32_i2c", "interface": 3, "port": 1},  # 3: i2c bus 1
        {"name": "stm32_i2c", "interface": 3, "port": 2},  # 4: i2c bus 2
        {"name": "stm32_i2c", "interface": 3, "port": 3},  # 5: i2c bus 3
        {"name": "stm32_uart", "interface": 0},  # 6: sweetberry console
        {
            "name": "ec3po_uart",  # 7: EC3PO(Sweetberry)
            "raw_pty": "raw_sweetberry_uart_pty",
            "source": "sweetberry",
        },
    ]

# Servo micro
SERVO_MICRO_DEFAULTS = [(0x18D1, 0x501A)]
for vid, pid in SERVO_MICRO_DEFAULTS:
    INTERFACE_DEFAULTS[vid][pid] = [
        "empty",
        {"name": "stm32_uart", "interface": 0},  # 1: PD/Cr50 console
        {"name": "stm32_i2c", "interface": 4},  # 2: i2c
        {"name": "stm32_uart", "interface": 3},  # 3: servo console
        "empty",  # 4: empty
        "empty",  # 5: empty
        {
            "name": "ec3po_uart",  # 6: servo console
            "raw_pty": "raw_servo_micro_uart_pty",
            "source": "servo_micro",
        },
        {"name": "stm32_uart", "interface": 6},  # 7: uart1/EC console
        {"name": "stm32_uart", "interface": 5},  # 8: uart2/AP console
        {
            "name": "ec3po_uart",  # 9: EC3PO for PD/Cr50
            "raw_pty": "raw_usbpd_uart_pty",
            "source": "PD/Cr50",
        },
        {
            "name": "ec3po_uart",  # 10: EC3PO for EC
            "raw_pty": "raw_ec_uart_pty",
            "source": "EC",
        },
        {
            "name": "ec3po_uart",  # 11: EC3PO for CPU
            "raw_pty": "raw_cpu_uart_pty",
            "source": "CPU",
        },
    ]

# C2D2
C2D2_DEFAULTS = [(0x18D1, 0x5041)]
for vid, pid in C2D2_DEFAULTS:
    INTERFACE_DEFAULTS[vid][pid] = [
        "empty",
        {"name": "stm32_uart", "interface": 0},  # 1: H1 console
        {"name": "stm32_i2c", "interface": 4, "port": 1},  # 2: i2c 2 // INAs etc
        {"name": "stm32_uart", "interface": 3},  # 3: servo console
        {"name": "stm32_i2c", "interface": 4},  # 4: i2c
        "empty",  # 5: empty
        {
            "name": "ec3po_uart",  # 6: servo console
            "raw_pty": "raw_c2d2_uart_pty",
            "source": "c2d2",
        },
        {"name": "stm32_uart", "interface": 6},  # 7: uart1/EC console
        {"name": "stm32_uart", "interface": 5},  # 8: uart2/AP console
        {
            "name": "ec3po_uart",  # 9: EC3PO for H1
            "raw_pty": "raw_usbpd_uart_pty",
            "source": "H1",
        },
        {
            "name": "ec3po_uart",  # 10: EC3PO for EC
            "raw_pty": "raw_ec_uart_pty",
            "source": "EC",
        },
        {
            "name": "ec3po_uart",  # 11: EC3PO for CPU
            "raw_pty": "raw_cpu_uart_pty",
            "source": "CPU",
        },
    ]

# Servo v4
# Note: the (0x18d1, 0x520d) pair is actually servo v4.1
# However, servo v4 and v4.1 have the same usb end-points and therefore
# interfaces (for now). Should this change, break v4.1 into its own logic.
SERVO_V4_DEFAULTS = [(0x18D1, 0x501B), (0x18D1, 0x520D)]
SERVO_V4_SLOT_SIZE = 20
SERVO_V4_SLOT_POSITIONS = {
    "default": 1,
    "hammer": 41,
    "staff": 41,
    "secondary_ccd": 61,
}
SERVO_V4_CONFIGS = {
    "hammer": "servo_micro_for_hammer.xml",
    "staff": "servo_micro_for_hammer.xml",
}
for vid, pid in SERVO_V4_DEFAULTS:
    # Interface #0 is reserved for no use.
    INTERFACE_DEFAULTS[vid][pid] = ["empty"]

    # Empty slots for servo micro/CCD use (interface #1-20).
    INTERFACE_DEFAULTS[vid][pid] += ["empty"] * SERVO_V4_SLOT_SIZE

    # Servo v4 interfaces.
    INTERFACE_DEFAULTS[vid][pid] += [
        "empty",  # 21: just nothing.
        {"name": "stm32_uart", "interface": 0},  # 22: servo console.
        {"name": "stm32_i2c", "interface": 2},  # 23: i2c
        {"name": "stm32_uart", "interface": 3},  # 24: dut sbu uart
        {"name": "stm32_uart", "interface": 4},  # 25: atmega uart
        {
            "name": "ec3po_uart",  # 26: servo v4 console
            "raw_pty": "raw_servo_v4_uart_pty",
            "source": "servo_v4",
        },
    ]

    # Buffer slots for servo v4 (interface #27-40).
    INTERFACE_DEFAULTS[vid][pid] += ["empty"] * (40 - 27 + 1)

    # Slots for relocating Hammer interfaces.
    INTERFACE_DEFAULTS[vid][pid] += ["empty"] * SERVO_V4_SLOT_SIZE

# Maui Proto
# ftdi generic 232H and PD12
MAUI_PROTO_DEFAULTS = [(0x0403, 0x6002)]
for vid, pid in MAUI_PROTO_DEFAULTS:
    INTERFACE_DEFAULTS[vid][pid] = [
        "empty",
        {"name": "ftdi_uart", "interface": 0},  # 1: UART
    ]

# Fluffy
FLUFFY_ID_DEFAULTS = [(0x18D1, 0x503B)]
for vid, pid in FLUFFY_ID_DEFAULTS:
    # Interface #0 is reserved for no use.
    INTERFACE_DEFAULTS[vid][pid] = ["empty"]

    # Empty slots for servo micro/CCD, servo v4, and servo micro relocation use
    # (interface #1-60).
    INTERFACE_DEFAULTS[vid][pid] += ["empty"] * SERVO_V4_SLOT_SIZE * 3

    INTERFACE_DEFAULTS[vid][pid] += [
        {"name": "stm32_uart", "interface": 0},  # 61 - Fluffy console
    ]

# Allow Board overrides of interfaces as we've started to overload some servo V2
# pinout functionality.  To-date just swapping EC SPI and JTAG interfaces for
# USB PD MCU UART.
INTERFACE_BOARDS = collections.defaultdict(lambda: collections.defaultdict(dict))

# re-purposes EC SPI to be UART for USBPD MCU
for board in ["elm", "hana", "oak", "samus"]:
    INTERFACE_BOARDS[board][0x18D1][0x5002] = list(INTERFACE_DEFAULTS[0x18D1][0x5002])
    INTERFACE_BOARDS[board][0x18D1][0x5002][6] = "ftdi_uart"

# re-purposes JTAG to be UART for USBPD MCU or H1
for board in [
    "asuka",
    "asurada",
    "atlas",
    "caroline",
    "cave",
    "chell",
    "cherry",
    "cheza",
    "d2db",
    "dragonegg",
    "drallion",
    "endeavour",
    "excelsior",
    "eve",
    "fizz",
    "flapjack",
    "goroh",
    "grunt",
    "hatch",
    "hayato",
    "herobrine",
    "jacuzzi",
    "kalista",
    "kingler",
    "krabby",
    "kukui",
    "kunimitsu",
    "lars",
    "meowth",
    "nami",
    "nautilus",
    "nocturne",
    "octopus_ite",
    "octopus_npcx",
    "pbody",
    "poppy",
    "puff",
    "rammus",
    "reef",
    "sarien",
    "scarlet",
    "sentry",
    "soraka",
    "spherion",
    "strago",
    "strongbad",
    "trogdor",
    "volteer",
    "zoombini",
    "zork",
]:
    INTERFACE_BOARDS[board][0x18D1][0x5002] = list(INTERFACE_DEFAULTS[0x18D1][0x5002])
    INTERFACE_BOARDS[board][0x18D1][0x5002][1] = "ftdi_uart"
