# Copyright 2022 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from array import array


# Currently all the pty data are collected manually from physical hardware tools
# by intercepting and logging the pty data of servod.
# We plan to automate it and collecting it with a script in the lab.
MOCKED_CR50_AP_DATA = {
    b"": b"\r\n>",
}

MOCKED_CR50_FPMCU_DATA = {
    b"": b"\r\n>",
}

MOCKED_CR50_CONSOLE_DATA = {
    b"": b"\r\n>",
    b"brdprop": b"brdprop\r\nproperties = 0x1242\r\ntpm board cfg = 0x0\r\n> ",
    b"ccd testlab open": b"\r\n> ",
    b"ccd testlab": b"ccd testlab\r\nCCD test lab mode enabled\r\n> ",
    b"ccdstate": b"ccdstate\r\nAP:      on\r\nAP UART: on\r\nEC:      on\r\nServo:   undetectable\r\nRdd:       connected\r\nKeepAlive: enabled\r\nCCD_MODE:  asserted\r\nState flags: UARTAP+TX UARTEC+TX I2C SPI USBEC+TX\r\nCCD ports blocked: (none)\r\n> ",
    b"ecrst off": b"ecrst off\r\nEC_RST_L is deasserted\r\n> ",
    b"ecrst on": b"ecrst on\r\nEC_RST_L is asserted\r\n> ",
    b"gpiocfg": b"gpiocfg\r\nGPIO0_GPIO0:\tread 1 drive 1\r\nGPIO0_GPIO1:\tread 0 drive 0\r\nGPIO0_GPIO2:\tread 0 drive 0\r\nGPIO0_GPIO5:\tread 0 drive 0\r\nGPIO0_GPIO11:\tread 0 drive 0\r\nGPIO1_GPIO0:\tread 1 INT_RISING\r\nGPIO1_GPIO4:\tread 1 INT_FALLING\r\nGPIO1_GPIO5:\tread 0 drive 1\r\n> ",
    b"gpioget AP_FLASH_SELECT": b"gpioget AP_FLASH_SELECT\r\n0  AP_FLASH_SELECT\r\n> ",
    b"gpioget CCD_REC_LID_SWITCH": b"gpioget CCD_REC_LID_SWITCH\r\n0  CCD_REC_LID_SWITCH\r\n> ",
    b"gpioget EC_FLASH_SELECT": b"gpioget EC_FLASH_SELECT\r\n  0  EC_FLASH_SELECT\r\n> ",
    b"gpioset CCD_REC_LID_SWITCH 0": b"gpioset CCD_REC_LID_SWITCH 0\r\n> ",
    b"recbtnforce enable": b"recbtnforce enable\r\nRecBtn: forced pressed\r\n> ",
    b"recbtnforce": b"recbtnforce\r\nRecBtn: forced pressed\r\n> ",
    b"sysrst off": b"\r\n> ",
    b"sysrst on": b"sysrst on\r\nSYS_RST_L is asserted\r\n> ",
    b"sysrst": b"sysrst\r\nSYS_RST_L is deasserted\r\n> ",
    b"wp": b"wp\r\nFlash WP: forced disabled\r\n at boot: forced disabled\r\n> ",
    b"gpioset CCD_REC_LID_SWITCH 1": b"gpioset CCD_REC_LID_SWITCH 1\r\n> ",
    b"recbtnforce disable": b"recbtnforce disable\r\nRecBtn: not pressed\r\n> ",
    b"ccd": b"State: Opened\r\nPassword: none\r\nFlags: 0x400001\r\nCapabilities: 0000000000000000\r\n  UartGscRxAPTx   Y 0=Default (Always)\r\n  UartGscTxAPRx   Y 0=Default (Always)\r\n  UartGscRxECTx   Y 0=Default (Always)\r\n  UartGscTxECRx   Y 0=Default (IfOpened)\r\n  FlashAP         Y 0=Default (IfOpened)\r\n  FlashEC         Y 0=Default (IfOpened)\r\n  OverrideWP      Y 0=Default (IfOpened)\r\n  RebootECAP      Y 0=Default (IfOpened)\r\n  GscFullConsole  Y 0=Default (IfOpened)\r\n  UnlockNoReboot  Y 0=Default (Always)\r\n  UnlockNoShortPP Y 0=Default (Always)\r\n  OpenNoTPMWipe   Y 0=Default (IfOpened)\r\n  OpenNoLongPP    Y 0=Default (IfOpened)\r\n  BatteryBypassPP Y 0=Default (Always)\r\n  Unused          Y 0=Default (Always)\r\n  I2C             Y 0=Default (IfOpened)\r\n  FlashRead       Y 0=Default (Always)\r\n  OpenNoDevMode   Y 0=Default (Always)\r\n  OpenFromUSB     Y 0=Default (Always)\r\n  OverrideBatt    Y 0=Default (IfOpened)\r\nread_tpm_nvmem: object at 0x100a not found\r\n[1231927.423343 Console unlock allowed]\r\nTPM:\r\nCapabilities are default.\r\nUse 'ccd help' to print subcommands\r\n> ",
    b"ecrst": b"EC_RST_L is deasserted\r\n> ",
    b"gettime": b"Time: 0x0000011ed826b625 = 1231987.062309 s\r\n> ",
    b"idle": b"idle action: sleep\r\ndeep sleep count: 9\r\n> ",
    b"powerbtn": b"powerbtn: released\r\n> ",
    b"sysinfo": b"Reset flags: 0x00010040 (hibernate rbox)\r\nReset count: 0\r\nChip:        g cr50 B2-C\r\nRO keyid:    0xaa66150f\r\nRW keyid:    0x87b73b67\r\nDEV_ID:      0x1002303d 0x92e5d453\r\nRollback:    1/0/1 3/3/3\r\nTPM MODE:    enabled (0)\r\nKey Ladder:  prod\r\n> ",
    b"version": b"Chip:    g cr50 B2-C\r\nBoard:   0\r\nRO_A:    0.0.10/29d77172\r\nRO_B:  * 0.0.11/4d655eab\r\nRW_A:    Error\r\nRW_B:  * 0.6.51/cr50_v1.9308_B.1054-0e610b99f9\r\nBID A:   46464646:00000000:00000010 Yes\r\nBID B:   46464646:00000000:00000010 Yes\r\nBuild:   0.6.51/cr50_v1.9308_B.1054-0e610b99f9\r\n         tpm2:v1.9308_26_0.66-388df8e\r\n         cryptoc:v1.9308_26_0.7-681a357\r\n         2021-08-27 22:21:47 @chromeos-ci-factory-us-central\r\n>",
}

MOCKED_SERVO41_CONSOLE_DATA = {
    b"": b">",
    b"ada_srccaps": b"ada_srccaps\r\n0: 5000mV/3000mA\r\n1: 9000mV/3000mA\r\n2: 15000mV/3000mA\r\n3: 20000mV/2250mA\r\n> ",
    b"adc": b"> adc\r\nCHARGER = 1672\r\nSOC = 1683\r\nVBUS = 14932\r\nSKU1 = 123\r\nSKU2 = 998\r\nCHG_CC1_PD = 5 mV\r\n  CHG_CC2_PD = 5 mV\r\n  DUT_CC1_PD = 12 mV\r\n  DUT_CC2_PD = 14 mV\r\n  SBU1_DET = 120 mV\r\n  SBU2_DET = 103 mV\r\n  SUB_C_REF = 562 mV> ",
    b"cc": b"cc\r\ncc: on\r\ndts mode: on\r\nchg mode: on\r\nchg allowed: on\r\ndrp enabled: off\r\ncc polarity: cc1\r\npd enabled: on\r\nemca: emarked\r\n> ",
    b"chan 0xffffffff": b"chan 0xffffffff\r\n> ",
    b"chan 1": b"chan 1\r\n> ",
    b"chan restore": b"chan restore\r\n> ",
    b"chan save": b"chan save\r\n> ",
    b"gpioget ATMEL_HWB_L": b"gpioget ATMEL_HWB_L\r\n  1* O H ATMEL_HWB_L\r\n> ",
    b"gpioget DUT_HUB_USB_RESET_L": b"gpioget DUT_HUB_USB_RESET_L\r\n  1* O H ODR DUT_HUB_USB_RESET_L\r\n> ",
    b"gpioget FASTBOOT_DUTHUB_MUX_EN_L": b"gpioget FASTBOOT_DUT HUB_MUX_EN_L\r\n  0  O L FASTBOOT_DUTHUB_MUX_EN_L\r\n> ",
    b"gpioget FASTBOOT_DUTHUB_MUX_SEL": b"gpioget FASTBOOT_DUTHUB_MUX_SEL\r\n  1* O H FASTBOOT_DUTHUB_MUX_SEL\r\n> ",
    b"gpioget SBU_MUX_EN": b"gpioget SBU_MUX_EN\r\n  1* O H SBU_MUX_EN\r\n> ",
    b"gpioget USB_FAULT_L": b"gpioget USB_FAULT_L\r\nParameter 1 invalid\r\n> ",
    b"gpioget USERVO_FAULT_L": b"gpioget USERVO_FAULT_L\r\nParameter 1 invalid\r\n>\r\n> ",
    b"gpioset ATMEL_HWB_L 1": b"gpioset ATMEL_HWB_L 1\r\n> ",
    b"macaddr": b"macaddr\r\nMAC address: 88:54:1f:0f:6a:95\r\n> ",
    b"panicinfo": b"panicinfo\r\nNo saved panic data available or panic data can't be safely interpreted.\r\n> ",
    b"pd 1 dev": b"pd 1 dev\r\nC1 st2\r\nmax req: 15000mV\r\n> ",
    b"usbc_action drswap": b"usbc_action drswap\r\nallow_dr_swap = 1\r\n> ",
    b"usbc_action prswap": b"usbc_action prswap\r\nallow_pr_swap = 1\r\n> ",
    b"version": b"version\r\nChip:    stm stm32f07x \r\nBoard:   3\r\nRO:      servo_v4p1_v2.0.8584+1a7e7e64c\r\nRW:      servo_v4p1_v2.0.8584+1a7e7e64c\r\nBuild:   servo_v4p1_v2.0.8584+1a7e7e64c\r\n         2021-04-30 23:54:40 dabros@dabros-l\r\n> ",
}

MOCKED_EC_PD_CONSOLE_DATA = {
    b"": b">",
    b"chan 0xffffffff": b"chan 0xffffffff\r\n> ",
    b"chan 1": b"chan 1\r\n> ",
    b"chan restore": b"chan restore\r\n> ",
    b"chan save": b"chan save\r\n> ",
    b"feat": b"feat\r\nCommand 'feat' not found or ambiguous. \r\n> ",
    b"hostevent set 0x4000": b"Events:\t0x0000000000004000\r\nEvents-B:\t0x0000000000204018\r\nSMI mask:\t0x0000000000000000\r\nSCI mask:\r0x00000000142609fb\r\nWake mask:\t0x0000000000000000\r\nAlways report mask:  0x000000002591c000",
    b"i2cxfer r 1 0x40 0x52": b"i2cxfer r 1 0x40 0x52\r\n0x6a [106]\r\n>",
    b"i2cxfer w 1 0x40 0x52 0x6a": b"i2cxfer w 1 0x40 0x52 0x6a\r\n>",
    b"pd 0 state": b"pd 0 state\r\nPort C0 CC1, Ena - Role: SNK-DFP State: SNK_READY, Flags: 0x14946\r\n> ",
    b"pd 1 state": b"pd 1 state\r\nPort C1 CC1, Ena - Role: SNK-UFP State: DRP_AUTO_TOGGLE, Flags: 0x60020\r\n> ",
    b"power off": b"power off\r\n> ",
    b"power on": b"power on\r\n> ",
    b"powerbtn  200": b"powerbtn  200\r\n> ",
    b"reboot ap-off": b"\r\nRebooting!",
    b"reboot wait-ext ap-off": b"Waiting for ext reset!\r\n> ",
    b"battery": b"battery\r\n  Status:    0x00e0 FULL DCHG INIT\r\n  Param flags:00000002\r\n  Temp:      0x0bc0 = 300.8 K (27.7 C)\r\n  V:         0x3032 = 12338 mV\r\n  V-desired: 0x0000 = 0 mV\r\n  I:         0x0000 = 0 mA\r\n  I-desired: 0x0000 = 0 mA\r\n  Charging:  Not Allowed\r\n  Charge:    100 %\r\n  Manuf:     Murata KT00304013\r\n  Device:    AP18K4K\r\n  Chem:      LiP\r\n  Serial:    0x003c\r\n  V-design:  0x2c88 = 11400 mV\r\n  Mode:      0x6101\r\n  Abs charge:78 %\r\n  Remaining: 3262 mAh\r\n  Cap-full:  3262 mAh\r\n    Design:  4200 mAh\r\n  Time-full: 0h:0\r\n    Empty:   0h:0\r\n> ",
    b"chgstate": b"chgstate\r\nstate = charge\r\nac = 1\r\nbatt_is_charging = 1\r\nchg.*:\r\n	voltage = 13200mV\r\n	current = 0mA\r\n	input_current = 2848mA\r\n	status = 0x10\r\n	option = 0x0\r\n	flags = 0x0\r\nbatt.*:\r\n	temperature = 27C\r\n	state_of_charge = 100%\r\n	voltage = 12338mV\r\n	current = 0mA\r\n	desired_voltage = 0mV\r\n	desired_current = 0mA\r\n	flags = 0x2\r\n	remaining_capacity = 3262mAh\r\n	full_capacity = 3262mAh\r\n	is_present = YES\r\nrequested_voltage = 0mV\r\nrequested_current = 0mA\r\nchg_ctl_mode = 0\r\nmanual_voltage = -1\r\nmanual_current = -1\r\nuser_current_limit = -1mA\r\nbattery_seems_to_be_dead = 0\r\nbattery_seems_to_be_disconnected = 0\r\nbattery_was_removed = 0\r\ndebug output = off\r\n> ",
    b"faninfo": b"faninfo\r\nCommand 'faninfo' not found or ambiguous.\r\n> ",
    b"flashinfo": b"flashinfo\r\nUsable:   512 KB\r\nWrite:      1 B (ideal 256 B)\r\nErase:   65536 B (to 1-bits)\r\nProtect: 65536 B\r\nFlags:  \r\nProtected now:\r\n    ........\r\n> ",
    b"gpioget": b"gpioget\r\n  1* USB_C0_PD_INT_ODL\r\n  1* USB_C1_PD_INT_ODL\r\n  1* USB_C0_SWCTL_INT_ODL\r\n  1* USB_C1_SWCTL_INT_ODL\r\n  1* PCH_SLP_S3_L\r\n  1* PCH_SLP_S5_L\r\n  1* S0_PGOOD\r\n  1* S5_PGOOD\r\n  1* POWER_BUTTON_L\r\n  1* LID_OPEN\r\n  1* AC_PRESENT\r\n  1* WP_L\r\n  1* VOLUME_DOWN_L\r\n  1* VOLUME_UP_L\r\n  1* USB_C0_CABLE_DET\r\n  0  6AXIS_INT_L\r\n  1* EC_RST_ODL\r\n  1* EN_PWR_A\r\n  1* EN_PP1800_SENSOR\r\n  0  ENABLE_BACKLIGHT_L\r\n  1* PCH_RSMRST_L\r\n  1* PCH_PWRBTN_L\r\n  1* PCH_WAKE_L\r\n  1* SYS_RESET_L\r\n  0  CCD_MODE_ODL\r\n  0  ENTERING_RW\r\n  0  EC_BATT_PRES_L\r\n  1* PCH_SYS_PWROK\r\n  1* CPU_PROCHOT\r\n  1* APU_ALERT_L\r\n  1* 3AXIS_INT_L\r\n  1* KB_BL_EN\r\n  1* EC_INT_L\r\n  0  I2C0_SCL\r\n  0  I2C0_SDA\r\n  0  I2C1_SCL\r\n  0  I2C1_SDA\r\n  0  I2C2_SCL\r\n  0  I2C2_SDA\r\n  0  I2C3_SCL\r\n  0  I2C3_SDA\r\n  0  I2C5_SCL\r\n  0  I2C5_SDA\r\n  0  I2C7_SCL\r\n  0  I2C7_SDA\r\n  1* EN_USB_A0_5V\r\n  1* EN_USB_A1_5V\r\n  1* EN_USB_C0_TCPC_PWR\r\n  1* USB_C0_OC_L\r\n  1* USB_C1_OC_L\r\n  1* USB_C0_PD_RST_L\r\n  1* USB_C1_PD_RST_L\r\n  0  USB_C0_BC12_VBUS_ON_L\r\n  1* USB_C1_BC12_VBUS_ON_L\r\n  0  USB_C0_BC12_CHG_DET\r\n  0  USB_C1_BC12_CHG_DET\r\n  0  USB_C0_DP_HPD\r\n  0  USB_C1_DP_HPD\r\n  0  BOARD_VERSION1\r\n  1* BOARD_VERSION2\r\n  1* BOARD_VERSION3\r\n  0  SKU_ID1\r\n  0  SKU_ID2\r\n  0  BAT_LED_1_L\r\n  1* BAT_LED_2_L\r\n  1* KBD_KSO2\r\n> ",
    b"lidstate": b"lidstate\r\nlid state: open\r\n> ",
    b"powerinfo": b"powerinfo\r\n[424278.745078 power state 3 = S0, in 0x000f]\r\n> ",
    b"pwr_avg": b"pwr_avg\r\nmv = 12338\r\nma = 0\r\nmw = 0\r\n> ",
    b"sysinfo": b"sysinfo\r\nReset flags: 0x00001802 (reset-pin hard ap-off)\r\nCopy:   RO\r\nJumped: no\r\nFlags:  unlocked\r\n> ",
    b"temps": b"temps\r\n  Charger             : 308 K = 35 C\r\n  SOC                 : 307 K = 34 C\r\n  CPU                 : 296 K = 23 C\r\n> ",
    b"version": b"version\r\nChip:    Nuvoton NPCX796F A.07\r\nboard:   6\r\nRO:      aleena_v2.1.333-a6ea0bc7f\r\nRW:      aleena_v2.1.333-a6ea0bc7f\r\nbuild:   aleena_v2.1.333-a6ea0bc7f\r\n         2021-02-04 04:05:36 @chromeos-ci-factory-us-central1-b-x32-0-9ql5\r\n> ",
}

MOCKED_SERVO41_I2C_DATA = {
    b"[0, 33, 1, 1, 0]": [array("B", [0, 0, 0, 0, 170])],
    b"[0, 33, 1, 1, 1]": [array("B", [0, 0, 0, 0, 158])],
    b"[0, 33, 1, 1, 2]": [
        array("B", [0, 0, 0, 0, 168]),
        array("B", [0, 0, 0, 0, 136]),
        array("B", [0, 0, 0, 0, 128]),
        array("B", [0, 0, 0, 0, 170]),
    ],
    b"[0, 33, 1, 1, 6]": [array("B", [0, 0, 0, 0, 0])],
    b"[0, 33, 2, 1, 2, 128]": [array("B", [0, 0, 0, 0, 190])],
    b"[0, 33, 2, 1, 2, 136]": [array("B", [0, 0, 0, 0, 190])],
    b"[0, 33, 2, 1, 2, 130]": [array("B", [0, 0, 0, 0, 190])],
    b"[0, 33, 2, 1, 2, 138]": [array("B", [0, 0, 0, 0, 190])],
    b"[0, 33, 2, 1, 2, 160]": [array("B", [0, 0, 0, 0, 190])],
    b"[0, 33, 2, 1, 2, 168]": [array("B", [0, 0, 0, 0, 190])],
    b"[0, 33, 2, 1, 2, 170]": [array("B", [0, 0, 0, 0, 190])],
    b"[0, 35, 1, 1, 0]": [array("B", [0, 0, 0, 0, 198])],
    b"[0, 64, 1, 2, 0]": [array("B", [0, 0, 0, 0, 65, 39])],
    b"[0, 64, 1, 2, 1]": [
        array("B", [0, 0, 0, 0, 2, 171]),
        array("B", [0, 0, 0, 0, 2, 181]),
    ],
    b"[0, 64, 1, 2, 2]": [
        array("B", [0, 0, 0, 0, 46, 242]),
        array("B", [0, 0, 0, 0, 46, 251]),
        array("B", [0, 0, 0, 0, 46, 255]),
    ],
    b"[0, 64, 1, 2, 3]": [
        array("B", [0, 0, 0, 0, 25, 173]),
        array("B", [0, 0, 0, 0, 25, 229]),
        array("B", [0, 0, 0, 0, 25, 67]),
    ],
    b"[0, 64, 1, 2, 4]": [
        array("B", [0, 0, 0, 0, 27, 0]),
        array("B", [0, 0, 0, 0, 41, 48]),
        array("B", [0, 0, 0, 0, 51, 32]),
    ],
    b"[0, 64, 1, 2, 5]": [
        array("B", [0, 0, 0, 0, 127, 255]),
        array("B", [0, 0, 0, 0, 4, 0]),
    ],
    b"[0, 64, 1, 2, 6]": [array("B", [0, 0, 0, 0, 0, 8])],
    b"[0, 64, 1, 2, 7]": [array("B", [0, 0, 0, 0, 0, 0])],
    b"[0, 64, 3, 2, 5, 127, 255]": [array("B", [0, 0, 0, 0, 127, 255])],
    b"[0, 65, 1, 2, 0]": [array("B", [0, 0, 0, 0, 65, 39])],
    b"[0, 65, 1, 2, 1]": [
        array("B", [0, 0, 0, 0, 2, 142]),
        array("B", [0, 0, 0, 0, 2, 178]),
    ],
    b"[0, 65, 1, 2, 2]": [array("B", [0, 0, 0, 0, 47, 7])],
    b"[0, 65, 1, 2, 3]": [
        array("B", [0, 0, 0, 0, 15, 241]),
        array("B", [0, 0, 0, 0, 25, 249]),
    ],
    b"[0, 65, 1, 2, 4]": [
        array("B", [0, 0, 0, 0, 27, 48]),
        array("B", [0, 0, 0, 0, 35, 176]),
    ],
    b"[0, 65, 1, 2, 5]": [
        array("B", [0, 0, 0, 0, 127, 255]),
        array("B", [0, 0, 0, 0, 4, 0]),
    ],
    b"[0, 65, 1, 2, 6]": [array("B", [0, 0, 0, 0, 0, 8])],
    b"[0, 65, 1, 2, 7]": [array("B", [0, 0, 0, 0, 0, 0])],
    b"[0, 65, 3, 2, 5, 127, 255]": [array("B", [0, 0, 0, 0, 127, 255])],
    b"[0, 66, 1, 2, 0]": [array("B", [0, 0, 0, 0, 65, 39])],
    b"[0, 66, 1, 2, 1]": [array("B", [0, 0, 0, 0, 2, 0])],
    b"[0, 66, 1, 2, 2]": [
        array("B", [0, 0, 0, 0, 15, 122]),
        array("B", [0, 0, 0, 0, 15, 123]),
    ],
    b"[0, 66, 1, 2, 3]": [
        array("B", [0, 0, 0, 0, 6, 94]),
        array("B", [0, 0, 0, 0, 6, 99]),
    ],
    b"[0, 66, 1, 2, 4]": [
        array("B", [0, 0, 0, 0, 32, 16]),
        array("B", [0, 0, 0, 0, 32, 32]),
    ],
    b"[0, 66, 1, 2, 5]": [
        array("B", [0, 0, 0, 0, 127, 255]),
        array("B", [0, 0, 0, 0, 4, 0]),
    ],
    b"[0, 66, 1, 2, 6]": [
        array("B", [0, 0, 0, 0, 0, 0]),
        array("B", [0, 0, 0, 0, 0, 8]),
    ],
    b"[0, 66, 1, 2, 7]": [array("B", [0, 0, 0, 0, 0, 0])],
    b"[0, 66, 3, 2, 5, 127, 255]": [array("B", [0, 0, 0, 0, 127, 255])],
}

MOCKED_CR50_I2C_DATA = {
    b"[0, 32, 1, 1, 1]": [array("B", [0, 0, 0, 0, 158])],
    b"[0, 38, 1, 1, 1]": [array("B", [0, 0, 0, 0, 158])],
    b"[0, 38, 1, 1, 3]": [array("B", [0, 0, 0, 0, 158])],
    b"[0, 38, 2, 1, 1, 150]": [array("B", [0, 0, 0, 0, 150])],
    b"[0, 38, 2, 1, 3, 150]": [array("B", [0, 0, 0, 0, 150])],
    b"[0, 32, 1, 1, 0]": [array("B", [0, 0, 0, 0, 150])],
    b"[0, 32, 1, 1, 3]": [array("B", [0, 0, 0, 0, 158])],
    b"[0, 32, 1, 1, 7]": [array("B", [0, 0, 0, 0, 1])],
    b"[0, 32, 2, 1, 3, 142]": [array("B", [0, 0, 0, 0, 158])],
    b"[0, 32, 2, 1, 3, 30]": [array("B", [0, 0, 0, 0, 158])],
    b"[0, 32, 2, 1, 7, 65]": [array("B", [0, 0, 0, 0, 158])],
    b"[0, 32, 1, 1, 6]": [array("B", [0, 0, 0, 0, 158])],
    b"[0, 32, 2, 1, 6, 190]": [array("B", [0, 0, 0, 0, 158])],
    b"[0, 32, 2, 1, 6, 222]": [array("B", [0, 0, 0, 0, 158])],
    b"[0, 38, 2, 1, 1, 156]": [array("B", [0, 0, 0, 0, 158])],
    b"[0, 38, 2, 1, 3, 156]": [array("B", [0, 0, 0, 0, 158])],
    b"[0, 38, 1, 1, 0]": [array("B", [1, 128, 0, 0, 0])],
}

MOCKED_SERVO41_ATMEGA_DATA = {b"a": b"a"}

MOCKED_SERVO_MICRO_PD_CR50_CONSOLE_DATA = {
    b"": b"\r\n> ",
    b"brdprop": b"brdprop\r\nproperties = 0x1242\r\ntpm board cfg = 0x0\r\n> ",
    b"cc": b"cc\r\ncc: on\r\ndts mode: on\r\nchg mode: off\r\nchg allowed: on\r\ndrp enabled: off\r\ncc polarity: cc1\r\npd enabled: on\r\nemca: emarked\r\n> ",
    # This is different from the standard CR50_CONSOLE_DATA. The State Flags show Servo micro is enabled.
    b"ccdstate": b"ccdstate\r\nAP:      on\r\nAP UART: on\r\nEC:      on\r\nServo:   connected\r\nRdd:       connected\r\nKeepAlive: enabled\r\nCCD_MODE:  asserted\r\nState flags: UARTAP UARTEC I2C USBEC+TX\r\nCCD ports blocked: (none)\r\n> ",
    b"chan 0xffffffff": b"chan 0xffffffff\r\n> ",
    b"chan 1": b"chan 1\r\n> ",
    b"chan restore": b"chan restore\r\n> ",
    b"chan save": b"chan save\r\n> ",
    b"ecrst": b"EC_RST_L is deasserted\r\n> ",
    b"ecrst off": b"ecrst off\r\nEC_RST_L is deasserted\r\n> ",
    b"ecrst on": b"ecrst on\r\nEC_RST_L is asserted\r\n> ",
    b"gpioget ATMEL_HWB_L": b"gpioget ATMEL_HWB_L\r\n  1  O H ATMEL_HWB_L\r\n> ",
    b"gpioset ATMEL_HWB_L 1": b"gpioset ATMEL_HWB_L 1\r\n> ",
    b"gpioget DUT_HUB_USB_RESET_L": b"gpioget DUT_HUB_USB_RESET_L\r\n  1  O H ODR DUT_HUB_USB_RESET_L\r\n> ",
    b"gpioget FASTBOOT_DUTHUB_MUX_EN_L": b"gpioget FASTBOOT_DUTHUB_MUX_EN_L\r\n  0  O L FASTBOOT_DUTHUB_MUX_EN_L\r\n> ",
    b"gpioget FASTBOOT_DUTHUB_MUX_SEL": b"gpioget FASTBOOT_DUTHUB_MUX_SEL\r\n  1  O H FASTBOOT_DUTHUB_MUX_SEL\r\n> ",
    b"version": b"version\r\nChip:    stm stm32f07x \r\nBoard:   3\r\nRO:      servo_v4p1_v2.0.8584+1a7e7e64c\r\nRW:      servo_v4p1_v2.0.8584+1a7e7e64c\r\nBuild:   servo_v4p1_v2.0.8584+1a7e7e64c\r\n         2021-04-30 23:54:40 dabros@dabros-l\r\n> ",
    b"wp": b"wp\r\nFlash WP: forced disabled\r\n at boot: forced disabled\r\n> ",
    b"ccd testlab open": b"\r\n> ",
    b"ccd testlab": b"ccd testlab\r\nCCD test lab mode enabled\r\n> ",
}

MOCKED_SERVO_MICRO_SERVO41_CONSOLE_DATA = {
    b"": b"\r\n> ",
    b"chan 0xffffffff": b"chan 0xffffffff\r\n> ",
    b"chan 1": b"chan 1\r\n> ",
    b"chan restore": b"chan restore\r\n> ",
    b"chan save": b"chan save\r\n> ",
    b"gpioget JTAG_BUFIN_EN_L": b"gpioget JTAG_BUFIN_EN_L\r\n  0  O L JTAG_BUFIN_EN_L\r\n> ",
    b"gpioget JTAG_BUFOUT_EN_L": b"gpioget JTAG_BUFOUT_EN_L\r\n  1  O H JTAG_BUFOUT_EN_L\r\n> ",
    b"gpioget SERVO_JTAG_RTCK": b"gpioget SERVO_JTAG_RTCK\r\n  0  O L SERVO_JTAG_RTCK\r\n> ",
    b"gpioget SERVO_JTAG_TDI": b"gpioget SERVO_JTAG_TDI\r\n  0  O L SERVO_JTAG_TDI\r\n> ",
    b"gpioget SERVO_JTAG_TDI_DIR": b"gpioget SERVO_JTAG_TDI_DIR\r\n  0  O L SERVO_JTAG_TDI_DIR\r\n> ",
    b"gpioget SERVO_JTAG_TDO_BUFFER_EN": b"gpioget SERVO_JTAG_TDO_BUFFER_EN\r\n  1  O H SERVO_JTAG_TDO_BUFFER_EN\r\n> ",
    b"gpioget SERVO_JTAG_TDO_SEL": b"gpioget SERVO_JTAG_TDO_SEL\r\n  1  O H SERVO_JTAG_TDO_SEL\r\n> ",
    b"gpioget SERVO_JTAG_TMS": b"gpioget SERVO_JTAG_TMS\r\n  0  O L SERVO_JTAG_TMS\r\n> ",
    b"gpioget SERVO_JTAG_TMS_DIR": b"gpioget SERVO_JTAG_TMS_DIR\r\n  0  O L SERVO_JTAG_TMS_DIR\r\n> ",
    b"gpioget SERVO_JTAG_TRST_DIR": b"gpioget SERVO_JTAG_TRST_DIR\r\n  0  O L SERVO_JTAG_TRST_DIR\r\n> ",
    b"gpioget SERVO_JTAG_TRST_L": b"gpioget SERVO_JTAG_TRST_L\r\n  1  O H SERVO_JTAG_TRST_L\r\n> ",
    b"gpioget SPI1_BUF_EN_L": b"gpioget SPI1_BUF_EN_L\r\n  1  O H SPI1_BUF_EN_L\r\n> ",
    b"gpioget SPI1_MUX_SEL": b"gpioget SPI1_MUX_SEL\r\n  1  O H SPI1_MUX_SEL\r\n> ",
    b"gpioget SPI1_VREF_18": b"gpioget SPI1_VREF_18\r\n  0  O L SPI1_VREF_18\r\n> ",
    b"gpioget SPI1_VREF_33": b"gpioget SPI1_VREF_33\r\n  0  O L SPI1_VREF_33\r\n> ",
    b"gpioget SPI2_BUF_EN_L": b"gpioget SPI2_BUF_EN_L\r\n  1  O H SPI2_BUF_EN_L\r\n> ",
    b"gpioget SPI2_VREF_18": b"gpioget SPI2_VREF_18\r\n  0  O L SPI2_VREF_18\r\n> ",
    b"gpioget SPI2_VREF_33": b"gpioget SPI2_VREF_33\r\n  0* O L SPI2_VREF_33\r\n> ",
    b"gpioget TCA6416_RESET_L": b"gpioget TCA6416_RESET_L\r\n  1  O H TCA6416_RESET_L\r\n> ",
    b"gpioget UART1_EN_L": b"gpioget UART1_EN_L\r\n  0  O L UART1_EN_L\r\n> ",
    b"gpioget UART2_EN_L": b"gpioget UART2_EN_L\r\n  0  O L UART2_EN_L\r\n> ",
    b"gpioget UART3_RX_JTAG_BUFFER_TO_SERVO_TDO": b"gpioget UART3_RX_JTAG_BUFFER_TO_SERVO_TDO\r\n  1  ALT UART3_RX_JTAG_BUFFER_TO_SERVO_TDO\r\n> ",
    b"gpioget UART3_TX_SERVO_JTAG_TCK": b"gpioget UART3_TX_SERVO_JTAG_TCK\r\n  1  ALT UART3_TX_SERVO_JTAG_TCK\r\n> ",
    b"gpioset JTAG_BUFIN_EN_L 0": b"gpioset JTAG_BUFIN_EN_L 0\r\n> ",
    b"gpioset JTAG_BUFIN_EN_L 1": b"gpioset JTAG_BUFIN_EN_L 1\r\n> ",
    b"gpioset SERVO_JTAG_TDO_BUFFER_EN 0": b"gpioset SERVO_JTAG_TDO_BUFFER_EN 0\r\n> ",
    b"gpioset SERVO_JTAG_TDO_BUFFER_EN 1": b"gpioset SERVO_JTAG_TDO_BUFFER_EN 1\r\n> ",
    b"gpioset SERVO_JTAG_TDO_SEL 1": b"gpioset SERVO_JTAG_TDO_SEL 1\r\n> ",
    b"gpioset SPI1_BUF_EN_L 1": b"gpioset SPI1_BUF_EN_L 1\r\n> ",
    b"gpioset SPI1_MUX_SEL 1": b"gpioset SPI1_MUX_SEL 1\r\n> ",
    b"gpioset SPI1_VREF_18 0": b"gpioset SPI1_VREF_18 0\r\n> ",
    b"gpioset SPI1_VREF_33 0": b"gpioset SPI1_VREF_33 0\r\n> ",
    b"gpioset SPI2_VREF_18 0": b"gpioset SPI2_VREF_18 0\r\n> ",
    b"gpioset SPI2_VREF_33 1": b"gpioset SPI2_VREF_33 1\r\n> ",
    b"gpioset UART1_EN_L 0": b"gpioset UART1_EN_L 0\r\n> ",
    b"gpioset UART3_RX_JTAG_BUFFER_TO_SERVO_TDO 0": b"gpioset UART3_RX_JTAG_BUFFER_TO_SERVO_TDO 0\r\n> ",
    b"gpioset UART3_RX_JTAG_BUFFER_TO_SERVO_TDO ALT": b"gpioset UART3_RX_JTAG_BUFFER_TO_SERVO_TDO ALT\r\n> ",
    b"gpioset UART3_TX_SERVO_JTAG_TCK 0": b"gpioset UART3_TX_SERVO_JTAG_TCK 0\r\n> ",
    b"gpioset UART3_TX_SERVO_JTAG_TCK ALT": b"gpioset UART3_TX_SERVO_JTAG_TCK ALT\r\n> ",
    b"hold_usart usart2": b"hold_usart usart2\r\nUSART status: normal\r\n> ",
    b"version": b"version\r\nChip:    stm stm32f07x \r\nBoard:   0\r\nRO:      servo_micro_v2.4.57-ce329f64f\r\nRW:      servo_micro_v2.4.57-ce329f64f\r\nBuild:   servo_micro_v2.4.57-ce329f64f\r\n         2020-12-03 18:26:08 @chromeos-ci-factory-us-east1-d-x32-1-bi6z\r\n> ",
}

MOCKED_SERVO_MICRO_I2C_DATA = {
    b"[0, 32, 1, 1, 0]": [array("B", [0, 0, 0, 0, 255])],
    b"[0, 32, 1, 1, 1]": [array("B", [0, 0, 0, 0, 255])],
    b"[0, 32, 1, 1, 2]": [array("B", [0, 0, 0, 0, 255])],
    b"[0, 32, 1, 1, 6]": [array("B", [0, 0, 0, 0, 252])],
    b"[0, 32, 1, 1, 7]": [array("B", [0, 0, 0, 0, 255])],
}

MOCKED_SERVO_MICRO_AP_DATA = {}

MOCKED_SERVO_MICRO_EC_DATA = {
    b"": b"",
    b"cbi": b"",
    b"chan 0xffffffff": b"",
    b"chan 1": b"",
    b"chan restore": b"",
    b"chan save": b"",
    b"gpioget LID_OPEN": b"",
    b"lidstate": b"",
    b"pdc sbumux": b"CCD Port: C0, Mode: NORMAL (0)\r\n> ",
    b"pdc sbumux normal": b"Set CCD port (C0) SBU mux mode to NORMAL (0)\r\n> ",
    b"pdc sbumux debug": b"Set CCD port (C0) SBU mux mode to FORCE_DEBUG (1)\r\n> ",
    b"powerinfo": b"powerinfo\r\n[424278.745078 power state 3 = S0, in 0x000f]\r\n> ",
    b"power on": b"",
    b"version": b"version\r\nChip:    Nuvoton NPCX796F A.07\r\nboard:   6\r\nRO:      aleena_v2.1.333-a6ea0bc7f\r\nRW:      aleena_v2.1.333-a6ea0bc7f\r\nbuild:   aleena_v2.1.333-a6ea0bc7f\r\n         2021-02-04 04:05:36 @chromeos-ci-factory-us-central1-b-x32-0-9ql5\r\n> ",
}

MOCKED_C2D2_H1_CONSOLE_DATA = {
    b"": b"\r\n> ",
    b"cc": b"cc\r\ncc: on\r\ndts mode: on\r\nchg mode: off\r\nchg allowed: on\r\ndrp enabled: off\r\ncc polarity: cc1\r\npd enabled: on\r\nemca: emarked\r\n> ",
    b"chan 0xffffffff": b"chan 0xffffffff\r\n> ",
    b"chan 1": b"chan 1\r\n> ",
    b"chan restore": b"chan restore\r\n> ",
    b"chan save": b"chan save\r\n> ",
    b"ecrst": b"EC_RST_L is deasserted\r\n> ",
    b"ecrst off": b"ecrst off\r\nEC_RST_L is deasserted\r\n> ",
    b"ecrst on": b"ecrst on\r\nEC_RST_L is asserted\r\n> ",
    b"gpioget ATMEL_HWB_L": b"gpioget ATMEL_HWB_L\r\n  1  O H ATMEL_HWB_L\r\n> ",
    b"gpioset ATMEL_HWB_L 1": b"gpioset ATMEL_HWB_L 1\r\n> ",
    b"gpioget DUT_HUB_USB_RESET_L": b"gpioget DUT_HUB_USB_RESET_L\r\n  1  O H ODR DUT_HUB_USB_RESET_L\r\n> ",
    b"gpioget FASTBOOT_DUTHUB_MUX_EN_L": b"gpioget FASTBOOT_DUTHUB_MUX_EN_L\r\n  0  O L FASTBOOT_DUTHUB_MUX_EN_L\r\n> ",
    b"gpioget FASTBOOT_DUTHUB_MUX_SEL": b"gpioget FASTBOOT_DUTHUB_MUX_SEL\r\n  1  O H FASTBOOT_DUTHUB_MUX_SEL\r\n> ",
    b"sysrst": b"sysrst\r\nSYS_RST_L is deasserted\r\n> ",
    b"sysrst off": b"\r\n> ",
    b"sysrst on": b"sysrst on\r\nSYS_RST_L is asserted\r\n> ",
    b"version": b"version\r\nChip:    stm stm32f07x \r\nBoard:   3\r\nRO:      servo_v4p1_v2.0.8584+1a7e7e64c\r\nRW:      servo_v4p1_v2.0.8584+1a7e7e64c\r\nBuild:   servo_v4p1_v2.0.8584+1a7e7e64c\r\n         2021-04-30 23:54:40 dabros@dabros-l\r\n> ",
}

MOCKED_C2D2_SERVO41_CONSOLE_DATA = {
    b"": b"\r\n> ",
    b"chan 0xffffffff": b"chan 0xffffffff\r\n> ",
    b"chan 1": b"chan 1\r\n> ",
    b"chan restore": b"chan restore\r\n> ",
    b"chan save": b"chan save\r\n> ",
    b"enable_spi": b"enable_spi\r\nSPI Vref: 0\r\n> ",
    b"gpioget EN_CLK_CSN_EC_UART": b"gpioget EN_CLK_CSN_EC_UART\r\n  1  EN_CLK_CSN_EC_UART\r\n> ",
    b"gpioset EN_CLK_CSN_EC_UART 1": b"gpioset EN_CLK_CSN_EC_UART 1\r\n> ",
    b"h1_reset": b"h1_reset\r\nH1 reset held: no\r\n> ",
    b"hold_usart usart1": b"hold_usart usart1\r\nUSART status: normal\r\n> ",
    b"version": b"version\r\nChip:    stm stm32f07x \r\nBoard:   0\r\nRO:      c2d2_v2.4.35-f1113c92b\r\nRW:      c2d2_v2.4.35-f1113c92b\r\nBuild:   c2d2_v2.4.35-f1113c92b\r\n         2020-07-24 06:53:49 @chromeos-ci-legacy-us-central1-b-x32-27-npfi\r\n> ",
}

MOCKED_C2D2_I2C_DATA = {}

MOCKED_C2D2_AP_DATA = {}

MOCKED_C2D2_EC_DATA = {
    b"": b"",
    b"cbi": b"",
    b"chan 0xffffffff": b"",
    b"chan 1": b"",
    b"chan restore": b"",
    b"chan save": b"",
    b"gpioget LID_OPEN": b"",
    b"lidstate": b"",
    b"pdc sbumux": b"CCD Port: C0, Mode: NORMAL (0)\r\n> ",
    b"pdc sbumux normal": b"Set CCD port (C0) SBU mux mode to NORMAL (0)\r\n> ",
    b"pdc sbumux debug": b"Set CCD port (C0) SBU mux mode to FORCE_DEBUG (1)\r\n> ",
    b"powerinfo": b"powerinfo\r\n[424278.745078 power state 3 = S0, in 0x000f]\r\n> ",
    b"power off": b"",
    b"version": b"version\r\nChip:    Nuvoton NPCX796F A.07\r\nboard:   6\r\nRO:      aleena_v2.1.333-a6ea0bc7f\r\nRW:      aleena_v2.1.333-a6ea0bc7f\r\nbuild:   aleena_v2.1.333-a6ea0bc7f\r\n         2021-02-04 04:05:36 @chromeos-ci-factory-us-central1-b-x32-0-9ql5\r\n> ",
}
