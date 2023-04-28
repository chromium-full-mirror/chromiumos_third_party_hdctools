# hdctools: Chrome OS Hardware Debug & Control Tools

This repository contains source code and documentation for the Servo debug
boards. The tools in this repository are only supported in the
[CrOS SDK chroot][Developer guide] or the [hdctools Docker container].

[TOC]

## Servo

*   [Servo: Debug Board](./docs/servo.md)
    *   [Servo v2](./docs/servo_v2.md)
    *   [Servo v4](./docs/servo_v4.md)
    *   [Servo v4.1](./docs/servo_v4p1.md)
    *   [Servo Micro](./docs/servo_micro.md)

## servod

*   [`servod`: Daemon for Servo](./docs/servod.md)
*   [`servod` FAQ](./docs/servod_faq.md)

## Closed Case Debugging (CCD)

*   [Closed Case Debugging (CCD) Overview](./docs/ccd.md)

## Power Measurement

*   [Power Measurement](./docs/power_measurement.md)
*   [Sweetberry Power Monitoring Board](./docs/sweetberry.md)
*   [INA: Instrumentation Amplifier](./docs/ina.md)

## Resources

*   [hdctools Docker container]: Run common hardware debug tasks outside the chroot.
*   [File a Bug](https://issuetracker.google.com/issues/new?component=983411&template=1678684)
*   [Contact](https://chromium.googlesource.com/chromiumos/docs/+/HEAD/contact.md)

[hdctools Docker container]: https://docs.google.com/document/d/e/2PACX-1vRGZ8yAfwzp6vlLZVGpJYQIFdv7_gR7yt6F6_Afk_2gWBlun5p-juZvOuHia9vfcOK88f4d6lIR1HqZ/pub
[Developer guide]: https://chromium.googlesource.com/chromiumos/docs/+/HEAD/developer_guide.md
