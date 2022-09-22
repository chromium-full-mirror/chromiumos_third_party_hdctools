# Servod drv Overview

One key component to servod are the drivers, or `drv`. The `drv` take a
reference to an interface (UART, I2C, the servod server, etc), and list of
parameters (from the control configuration in .xml), and execute the code/logic
behind a control. So every control has a `drv`. This is intended as an overview
to how `drv` work, and what to look out for when writing `drv`, debugging, or
anything else. This overview is also intended to explain how to use params, what
special params exist, and how to leverage them to write less code, and create
robust controls.\
The first key insight is that a servod control is entirely described in its
params, and that a combination of `drv`, `interface` and `params` entirely
defines a control, and its execution logic. The control name is simply a
symbolic name to access that logic.

## core system

Each `drv` inherits from [`HwDriver`][hw_driver]. When issuing a control, servod
will find the required `drv` from the control's parameters, and then instantiate
it as either a `set` or a `get` `drv`, depending on whether the control is being
used for `set` or `get`. Subsequently servod will call `.get()` or `.set(value)`
on the `drv` instance whenever executing it.

## dispatching

`HwDriver`'s `get` and `set` performs dispatching and value safety checks. Before
dispatching, `HwDriver` `set` checks the dispatched values and ensures it is a
valid choice. A `drv` should never override `set` and `get` unless it wants to
override the common dispatching logic.

`HwDriver` defines the common dispatching logic in `set` and `get`:
1. If `subtype` is provided in a control's params, the dispatcher looks for
   `_Set_[subtype]` or `_Get_[subtype]`and executes them. In case of not found,
   the dispatcher will throw an error.
2. If `subtype` is not provided through a control's params, the dispatcher
   delegates execution to `_set` and `_get`. A `drv` should override `_set`
   and `_get` for common getting/setting logic.

In general, a simple `drv` try to just expose `_get` and `_set` to make the code
easy to read, and the params easy to write. You should leverage subtypes if
there is
1. data you need to share across multiple functionalities
2. this data is best shared in a common class, rather than through inheritance

## mode

The `mode` is the value of the `cmd`=`mode` keyval control parameter that the
`drv` uses to decide whether to perform `get` or `set`. There are in
general the following types of `drv`:
1. `drv` that can do `set/get` with the same params e.g. a GPIO read/write
2. `drv` that can do `set/get` with different params e.g. some control that has
   a different API/requirement for set than get
3. `drv` that can **only** do `set/get` with their param set, and the other
   one is undefined


To aid with this, `system_config` implements the following policy.
1. if a `control` has two sets of params, both must have `cmd`, one must be
   `cmd="get"` and the other must be `cmd="set"`
2. if a `control` has one set of params *and defines* `cmd="[mode]"`, the
   assumption is that `drv` is **only** valid for that mode. In that case,
   `system_config` will create a error params for the other mode, so that if
   the user tries to issue the control in the unsupported mode, they will get an
   explicit error that the control does not support that mode.\
   For example. `dut-control servo_v4_version` only supports reading, and not
   writing anything to it. So if the user issues
   `dut-control servo_v4_version:rubbish` they receive an explicit error that
   'set is not supported'.
3. if a `control` has one set of params and *and does not define* `cmd="[mode]"`
   the system assumes that the params are valid for both set and get. It will
   create a copy of the params, add `cmd="set|get"` appropriately, and generate
   both modes of the controls.

This ensures two things
1. a mechanism for `control` writers to be explicit whether their control
   supports both modes or not
2. a guarantee to `drv` system that every set of params will have the mode
   written into it, and thus any logic that depends on whether the `drv`
   instance is for a set or a get drv that query that information from
   `self._params['cmd']`

## control complement

As mentioned before
1. a control is entirely defined by its parameters, and a combination of `drv`,
   `interface`, and `params` defines a control uniquely.
2. a control has at least one mode, and can have up to two valid modes.

From those two facts, we introduce the notion of a control's complement. The
control's complement is simply the control in the other mode e.g.
```
dut-control control_a
dut-control control_a:something
```
are each others complements.\
It sometimes becomes necessary for controls to be able to execute their own
complement in order to perform their function. A simple example is
read/modify/write operations on a register, or checking whether a mux
already points in a specific direction before changing the direction.\
To facilitate this, the framework provides each `drv` instance with a reference
to its complement control's `drv` instance. This allows a control to execute the
complement.\
There are a few things to note when leveraging this mechanism
1. There is always a complement, it will never be None, but that complement
   might be an error control. This stems from the guarantee above that each
   control will exist in both modes, but if the control is not valid in one
   mode then its implementation in that mode will throw a clear error indicating
   that it does not exist in that mode. Writer need to be aware of this whether
   a complement makes sense or exists
2. The complement logic is based on servod control configs, and not `drv`
   classes. This means that the complement is simply what the other mode's
   parameters described it would be. The complement might be an entirely
   different `drv`, with a different interface, etc. This is aligned with the
   goal that the mechanism is there to provide access to the other mode for a
   control

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
more parameters (to execute other things) you can
1. pass more parameters through the config (preferred)
2. write a super-set `control` and `drv` that uses `servo` as its interface
   (and thus can execute arbitrary other servod controls) like
   [usb muxing][usb_mux]

## safety

There are a few built in safety mechanisms.
1. required params: a `drv` can define `REQUIRED_[SET|GET]_PARAMS` to provide a
   list of params the control **has to** provide for the `drv` to function. This
   then automatically handles errors in case a `control` is missing a required
   parameter in its configuration
2. choices: if a `drv` uses `_set` or `_Set_[subtype]`, then `HwDriver` will
   check the value passed into the method to make sure it's a valid choice. By
   default, everything is a valid choice. The `drv` can define
   `self._choices = re.compile('^(choice1|choice2)$')` i.e. a compiled-regex of
   valid choices.\
   Note: choices are checked in their string representations i.e. if a user is
   trying to set a value, the choices check is done by casting value to string,
   and checking against the string choices.

## key params  {#params}

The following special parameters exist, and are useful to know about

*   `drv`

    Name of the python module that contains the driver for this control.

*   `interface`

    Index of the interface to use for this control or `servo` if the interface
    is intended to be the `servod` instance. The interface index for the devices
    can be found [here][interface_index]

*   `map`

    As a parameter map tells servod what map to use for input on this control.
    If a `map` name ends with `_re`, the map uses regex for matching, otherwise
    it performs simple string matching.

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

    Compiled-regex of valid input choices for a set control.


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
   console (EC, GSC, servo console), match against a regex, and return the
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
[usb_mux]: ../servo/drv/usb_image_manager.py
[interface_index]: ../servo/servo_interfaces.py
