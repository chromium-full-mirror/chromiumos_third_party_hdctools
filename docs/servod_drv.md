# Servod drv Overview

One key component to servod are the drivers, or `drv`. The `drv` take a
reference to an interface (UART, I2C, the servod server, etc), and list of
parameters (from the control configuration in .xml), and execute the code/logic
behind a control. So every control has a `drv`. This is intended as an overview
to how `drv` work, and what to look out for when writing `drv`, debugging, or
anything else. This overview is also intended to explain how to use params, what
special params exist, and how to leverage them to write less code, and create
robust controls.

## core system

Each `drv` inherits from [`HwDriver`][hw_driver]. When issuing a control, servod
will find the required `drv` from the control's parameters, and then instantiate
it as either a `set` or a `get` `drv`, depending on whether the control is being
used for `set` or `get`. Subsequently servod will call `.get()` or `.set(value)`
on the `drv` instance whenever executing it.

## dispatching

There are three layers of abstraction for dispatching. At the most basic level,
a `drv` can overwrite `set` and `get` at which point, the `drv` will just
execute those.\
The next layer is defining `_set` instead of `set`. This guarantees that some
safety checks are performed on the passed in value before running it, but is
otherwise identical to `set`.\
Should a driver not expose `set/_set` and/or `get`, then the `HwDriver`
dispatcher kicks in to look for `_Set_[subtype]` or `_Get_[subtype]` (where
subtype is provided through the params).


So in general, simple `drv` try to just expose `get` and `_set` to make the code
easy to read, and the params easy to write. You should leverage subtypes if
there is
1. data you need to share across multiple functionalities
2. this data is best shared in a common class, rather than through inheritance

## data sharing

Each `drv` is its own instance for each control and control mode (set/get). This
means that the same `drv` can be instantiated multiple times on the same servod
instance if it is used for multiple controls, or a control has set and get
defined.\
This has implications for data-sharing. If a `drv` needs to be able to share
data between multiple controls, or its own set/get implementation, it's best to
do so by using a shared container that you attach to the drv class. Take a look
at [the echo drv][echo] for a simple example of that.\
It's especially important to keep in mind which parameters a `drv` has access
to when trying to execute other modes/subtypes within a `drv`. The parameters a
`drv` instance knows about are from its control only. If it needs to know about
more paramters (to execute other things) you can
1. pass more parameters through the config (preferred)
2. write a sort of super-set `control` and `drv` that uses `servo` as its
   interface (and thus can execute arbitrary other servod controls)

## safety

There are a few built in safety mechanisms.
1. required params: a `drv` can define `REQUIRED_[SET|GET]_PARAMS` to provide a
   list of params the control **has to** provide for the `drv` to function. This
   then automatically handles errors in case a `control` is missing a required
   parameter in its configuration
2. choices: if a `drv` uses `_set` or `_Set_[subtype]`, then `HwDriver` will
   check the value passed into the method to make sure it's a valid choice. By
   default, everything is a valid choice. The `drv` can define
   `self._choices = {'choice1', 'choice2'}` i.e. a container of valid choices.
   Alternatively, the parameters can define a comma-separated list of valid
   choices that will be parsed out.\
   Note: choices are checked in their string representations i.e. if a user is
   trying to set a value, the choices check is done by casting value to string,
   and checking against the string choices.

## key params  {#params}

The following special parameters exist, and are useful to know about

*   `drv`

    String of the python module that contains the driver for this control.

*   `interface`

    Index of the interface to use for this control. `servo` if the interface is
    intended to be the `servod` instance.

*   `map`

    As a parameter map tells servod what map to use for input on this control.

*   `cmd`

    Either `set` or `get`. On controls with different params for `get` and `set`
    method this needs to be defined to associate the right params dictionary to
    the right method.

*   `fmt`

    [`fmt` function to execute][fmt] on output values. Currently only supports
    hex.

*   `subtype`

    If a driver has more than one method it exposes, then subtype defines what
    method should be called to execute a given control. The method
    [called][call] on the driver instance then is drv.`_(Set|Get)_|subtype|`.

*   `input_type`

    Input on set methods will be [cast][cst] to `input_type`. Currently `float`,
    `int`, and `str` are supported.

*   `choices`

    Comma-separated list of valid input choices for a set control. Note two
    important factors. The check is done after casting the input value to a
    string, and comparing it to the string defined in this list. The check also
    only happens if the driver either defines `_set` rather than `set` or
    defines a subtype (`_Set_[subtype]`)


### device specific params

In some cases, a control should function differently on a servo device than on
others. To that end, the config system supports overwriting `interface` and
`drv` with a device-specific version e.g. `servo_micro_drv`. If the control is
running on `servo_micro`, `servo_micro_drv` will be used instead of `drv`,
otherwise `drv` is used. This can be used to noop some controls on some devices
(by setting the `drv="na"`).

## general purpose drvs

While in general one could write a `drv` for every sort of code, the goal is to
slowly have more general-purpose `drv` that can execute many common functions
and where the differentiation is provided through the params. To that end, note
the following `drv`:

1. [echo][echo]: `echo` is a simple `drv` that will 'echo' back a value that was
   set in the params. This can be helpful to return hard-coded configs or
   information depending on a DUT/device

2. [simple ec][simple_ec]: `simple_ec` will execute a command on a cros ec
   console (EC, Cr50, servo console), match against a regex, and return the
   output value. This is a very common flow in Chrome OS, and a powerful drv to
   create all sorts of controls by just providing the console command and the
   regex through the config
3. [sflag][sflag]: `sflag` is a software flag i.e. the user can set it to on/off
   and then read out the last written value. This can be useful to signal state,
   or report errors
4. [ec i2c pin][ec_i2c_pin]: `ec_i2c_pin` is a `drv` that lets you toggle one
   'pin' over i2c through the console. This can be helpful to read out, or
   set/get GPIOs on an io-expander, or status bits over i2c. It specifically
   only allows 0, and 1 and supports a read/modify/write operation in the set
   functionality
5. [pty driver][pty_driver]: `pty_driver` is base `drv` that exposes how we talk
   to (most) UART consoles. Most `drv` that deal with UART communication are on
   top of `pty_driver`. It provides the lower-level logic of how to send a
   regex, what to wait for, and how to clean up the output

[echo]: ../servo/drv/echo.py
[simple_ec]: ../servo/drv/simple_ec.py
[sflag]: ../servo/drv/sflag.py
[ec_i2c_pin]: ../servo/drv/ec_i2c_pin.py
[pty_driver]: ../servo/drv/pty_driver.py
[hw_driver]: ../servo/drv/hw_driver.py
[call]: ../servo/drv/hw_driver.py#72
[fmt]: ../servo/system_config.py#455
[cst]: ../servo/system_config.py#382
