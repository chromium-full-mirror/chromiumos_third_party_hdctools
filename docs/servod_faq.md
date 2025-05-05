# Servod FAQ

[TOC]

## How do I turn off servod?

### tl;dr:

*   `servodtool -p $PORT stop`
*   `<unplug the servo device>`
*   `<Ctrl-C>` also works

### the longer read

There are currently two mechanisms to help with `servod` management:
[ServoScratch (through servodtool)][5] and [ServoDeviceWatchdog][6].

ServoScratch leaves information about each servod instance around (e.g. port,
pid). This information can be used to turn off servod.

ServoDeviceWatchdog regularly polls to ensure all devices (i.e. servos) that the
system started with are still attached. If not, it will gracefully terminate
servod.

## What does the servod version mean

### tl;dr:

\[major-number\].\[minor-number\].\[commits-since-minor\]\[.dev\]

### the longer read:

The servod version needs to do two things: it needs to provide a pep440
compliant version string (the package version) and it needs to provide useful
information for debugging. Lastly, there are (usually) two environemnts where
servod is built: locally using cros\_workon, and remotely when building an
image. With that in mind `version` has to be a 'rather' meaningless number,
especially when building locally as we don't have access to git tags, git
history, and cannot use a git hash in pep440.

The solution is to have two notions of version:

-   one is the python version that applies to the package and the scripts, and
    is returned through `servod --version`. This one receives a .dev when
    git-information is missing as that's likely coming from building locally.

-   the other one is sversion, a more comprehensive version that reports the
    version string, the git-hash, the build-time and builder. This can be
    queried by doing `servod --sversion` (or any of the other command-line tools

## Where is the code logic for the control `control`?

### tl;dr:

Look for the control name in `data/` to see its configuration. Look for the
python module inside `drv/` named the same as the controls `drv` param. In there
look for either `set()`/`get()` method, or if `subtype` defined in params for
`_Set_|subtype|`/`_Get_|subtype|`.

### the longer read

As you might have read in the [`servod` docs], servo control routing uses the
`drv` and `cmd` and `subtype` arguments inside a control's params to determine
where to look for the control.

The `drv` param describes what python module from the `drv/` directory houses
the controls `drv` class. The class name is obtained by converting the `drv`
name into [camel case][1].

If no subtype is defined then the `drv` class' (or a parent class') `get()` or
`set()` method will be invoked.

If a subtype is defined, then a method called `_Get_|subtype|` or
`_Set_|subtype|` will be called.

The `cmd` param in params defines if a param is set or get. If it is missing,
then the params will be used for both set and get.

## What is the interface object passed into these drivers?

### tl;dr:

It's a servo_interface or the Servod instance (if `interface=="servo"`). The
control's config defines what interface to use. That number is the index into
the `servo_interfaces.py` interface list for the servo device you're using (v2,
micro, ccd, etc).

Common interfaces are:

*   `2`: DUT i2c for INAs
*   `8`: AP console
*   `9`: GSC console
*   `10`: EC console

## How do I reroute/overwrite a control for a board? {#reroute-control}

By default, redefining an existing control of the same name or alias is an
error. This behavior can be changed using the `<params>` attribute `clobber_ok`.
There are several behaviors supported:

* `clobber_ok="patch"`: This will update the params of an existing control, but
  will quietly (without error) avoid defining a new control. Use this when
  overriding a specific subset of params of a control that you expect to already
  exist from an included config.

   * With `"patch"` only the specified `<params>` will be updated. Any
     `<params>` of the existing control that are not specified will remain
     unchanged in the patched control.

* `clobber_ok="full"`: This will completely replace all params of any existing
  control, and will define a new control if there isn't one to replace. Use this
  when fully reimplementing a control that has a default implementation. For
  example, if you are changing `drv=` to a different driver, that should usually
  use `"full"`, not `"patch"`, because params from the original control might
  not be valid or have the same meaning for the different driver.

   * With `"full`" any `<params>` attributes from an existing control will NOT
     be retained.

* `clobber_ok="never"`: This control definition will be quietly ignored
  (no error) without overriding anything if there is an existing control of the
  same name/alias. If there is no existing control, then this control definition
  will be used.

* `clobber_ok=""`: **DEPRECATED, do not use in new control definitions!**
  https://issuetracker.google.com/287541200 tracks removal of this option.
  This is like `"patch"` except this will define a new control if there isn't
  one to update. Don't use this! If your control is meant to update one already
  defined, use `"patch"`. If your control is fully specified and needs to
  replace one that's already defined, use `"full"`. If there is no
  already-defined control that your control needs to patch or replace, don't use
  `clobber_ok` at all!

   * With `""` only the specified `<params>` will be updated. Any `<params>` of
     an existing control that are not specified will remain unchanged in the
     patched control.

## How do I add a new control?

### tl;dr:

Add your control to the an existing configuration file in `data/` or create a
new one. Use an existing driver in `drv/` or create a new one. In your control
be sure to set `drv` and `subtype` so that the method and driver you intend to
call get called.

### the longer read

Reading the [`servod` docs] will help a lot with this.

Adding a new control involves adding a new configuration outlining what the
control does and adding driver support to execute the control.

The first decision to make is if the new functionality should extend an existing
configuration or not. Creating a new configuration means having to ensure it's
included in all the right places, which might be more appropriate for niche
controls.

The next decision to make is whether to extend an existing driver, or implement
a new driver. When implementing a new driver, ensure that its added to
`drv/__init__.py` as otherwise servod won't be able to find it.

Once a driver with the appropriate method and the control exist, you can test out
how you want to manage information. Hard-coding aspects into the driver makes
configuration files simpler as the params attribute needs fewer entries. However
it makes the driver less flexible, as that control's params now cannot be
overwritten on a per-board/servo device basis.

## How do I share data between methods in a driver?

### tl;dr:

Use class variables and dictionaries inside your driver to ensure that data can
be shared between different methods.

### the longer read

As you might have read in the [`servod` docs] each `servod` control gets its own
instance of the driver class, with its parameters passed to that instance's
constructor. So in order to share data across methods (to cache results, or
build out more complex functionality) the simplest way is to use class variables
inside the driver to share the information.

Keep in mind that while class variables in python are accessible through
`self.varname`, assigning anything new to `self.varname` does not assign to the
class variable but rather creates a new instance variable that masks the class
variable. Either explictly call the class variable, or use a mutable object as
your class variable (`list`, `dict`).

## How do I get started with servo scripting/automation?

### tl;dr:

You can either `import servo.client` if `hdctools` is installed when executing
these automations (a moblab, a chroot etc) and then just use the `Sclient` class
to create a proxy and send controls/use servod. [Example code using sclient][2].

Alternatively, you can create your own XMLRPC proxy and execute the exposed rpc
functions (the `Servod` class' methods) through that proxy.
[Example code using proxy][3].

## How do I add a new device to servod?

### tl;dir:

*   Consult ChromeOS Hardware Tools team whether the new device should be supported through servod
*   Develop on a development branch of /third-party/hdctools
*   Read servod code to understand how it supports other devices

### the longer read

Servod is a daemon process that supports servo devices. Not every hardware tool should be supported through servod. If you are not sure, it is ideal to consult ChromeOS Hardware Tools team before implementing.

Any commits checked into the main branch of /third-party/hdctools are visible to all servod users. Therefore, any major changes, including adding a new device, should be done in a development branch, in order to minimize the risk of introducing breaking changes. Please contact ChromeOS Hardware Tools team if you need to open a new development branch.

If the new device is similar to any device supported by servod right now, above, you can read servod code to understand how it is supported. Servod currently supports the following devices
*   Open case debuggers (Servo Micro, C2D2(deprecated), Servo V2(deprecated))
*   Close case debuggers (CCD)
*   Hub servos (Servo V4p1, Servo V4)
*   Other devices (Sweetberry, Fluffy, etc)

In general, there are several key changes to support a device
*   Add the device's vendor id, product id, default config to [servo_dev_template.py][7]
*   Add the device's interfaces to [servo_interfaces.py][8]
*   Add the device's default config to [/hdctools/servo/data][9]. The config defines the controls of this device. A config can include other configs.
*   Add some drvs to [/hdctools/servo/drv][10]. A drv is the actual executor of a control and can communicate with the hardware interfaces as well as the servod daemon. The device config dictates which control is handled by which drv.
*   If special setup instructions are needed for the device (e.g. the device can only work with servo v4p1), take a look of [servo_dev_finder.py][11] and define the setup policies there.

[1]: ../servo/servo_server.py#519
[2]: ../servo/dut_control.py#354
[3]: https://chromium.googlesource.com/chromiumos/third_party/autotest/+/HEAD/server/hosts/servo_host.py#177
[5]: ./servod.md#servod-tool
[6]: ./servod.md#servo-device-watchdog
[7]: ../servo/servo_dev_templates.py
[8]: ../servo/servo_interfaces.py
[9]: ../servo/data/
[10]: ../servo/drv/
[11]: ../servo/servo_dev_finder.py
[`servod` docs]: ./servod.md
