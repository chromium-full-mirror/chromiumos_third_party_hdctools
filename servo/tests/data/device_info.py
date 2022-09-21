# Copyright 2022 The ChromiumOS Authors.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

SECONDARY_SERVOS_NAMES = ( 'servo_micro', 'ccd_cr50', 'ccd_ti50', 'c2d2')

SERVO_DEVICE_DATA = {
  'miniservo_v1':
  ( (0x18d1, 0x5000),
    ('001', '540052'),
    'miniservo.xml',
  ),

  'servo_v1':
  ( (0x18d1, 0x5001),
    ('483881', '498432'),
    'servo.xml',
  ),

 'servo_v2_r0':
  ( (0x18d1, 0x5002),
    ('609600', '629871'),
    'servo_v2_r0.xml',
  ),

 'servo_v2':
  ( (0x18d1, 0x5002),
    ('641200', '686203', '730422', '780735', '868534', '875286', 'force-v2-lotid'),
    'servo_v2_r1.xml',
  ),

 'servo_v4':
  ( (0x18d1,  0x501b),
    (),
    'servo_v4.xml',
  ),

 'servo_v4p1':
  ( (0x18d1, 0x520d),
    (),
    'servo_v4p1.xml',
  ),

 'servo_micro':
  ( (0x18d1, 0x501a),
    (),
    'servo_micro.xml',
  ),

 'ccd_cr50':
  ( (0x18d1, 0x5014),
    (),
    'ccd_cr50.xml',
  ),

 'ccd_ti50':
  ( (0x18d1, 0x504a),
    (),
    'ccd_ti50.xml',
  ),

 'sweetberry':
  ( (0x18d1, 0x5020),
    (),
    'sweetberry.xml',
  ),

 'c2d2':
  ( (0x18d1, 0x5041),
    (),
    'c2d2.xml',
  ),

 'reston':
  ( (0x18d1, 0x5007),
    (),
    'reston.xml',
  ),

 'fruitpie':
  ( (0x18d1, 0x5009),
    (),
    'fruitpie.xml',
  ),

 'plankton':
  ( (0x18d1, 0x500c),
    (),
    'plankton.xml',
  ),

 'fluffy':
  ( (0x18d1, 0x503b),
    (),
    'fluffy.xml',
  ),
}
