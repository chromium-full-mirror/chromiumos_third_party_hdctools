# Writing XML data files for servod

[TOC]

## Glossary

* Host - typically your local development machine or a labstation in fleet
* DUT - Device under test
* Control - Basic communication unit of servod
* Driver - Code written in python
* Tag - Entry in XML
  `<tag></tag>`
* Attribute - Additional parameter assigned to the tag
  `<tag attribute="value" other_attr="another_value"></tag>`
* Board - Type of DUT, can contain one or more models
* Model - One specific version of DUT, belongs to board family
* `dut-control` - Command Line Interface to servod, used to manage controls

## Intro

Servod is a daemon that allows the communication between host and DUT using servo
device.  
Basic item in the communication is called control.
The API to servod can be customized for each DUT. The customization can be at a board
or a board and model level. Customizations are written by defining controls that are
loaded at runtime.
Each control defines one thing that represents either a state (has value), or an action
to do. Action controls receive values to set, but don't contain these value, so they
don't support getter functions.
For example state of the USB mux or state of the GPIO, or action like sending text
message to console.  

Controls are defined in data files. These data files are written in XML and located in
the [servod source](../servo/data/). Data files can inherit from other data files. This
allows for generic controls to be specified but overridden for specific board/models as
required. This allow tests to use consistent API control names but actually executing
different functions on the DUT.

Different files are loaded for different boards, selected by either autodetection or by
parameter to `start-servod` script.
Autodetection is not always reliable, so it's suggested to always provide the board and
model parameters when starting servod.

## Drivers

Logically, the driver is a function used to retrieve or set property on the DUT or other
equipment used during tests or development. For example, such property may be a state of
the GPIO of Embedded Controller, like lid switch or value from current sensor.
Programmatically, drivers are classes written in python, derived from
[HwDriver class](../servo/drv/hw_driver.py) and implementing getter and/or
setter methods.

Drivers contain logic that communicate with different devices like Servo v4.1, EC,
GSC, power measurement boards.

Drivers are located in the `servo/drv` directory. Name of the file, without extension,
is used in the control definition to select the driver to use.

This paragraph is only a short description of most important parts of the drivers.
For more detailed description, read document dedicated to
[servod drivers](servod_data.md).

### Initialization

Inherited class should *NOT* provide its own `__init__` function. The initialization
may be done in `_drv_init` function that should be overridden by inheriting class. It
will be called be base class initialization.
If driver doesn't require initialization, this function may be skipped, since base
class provides implementation of it, which should be called using `super()` method
in case of overriding it.

### Getter

The default function used to get control's value is implemented by overriding:
`_get(self)`

There is a possibility to implement different subtypes of getter function
by specifying `subtype` attribute to the control definition. It will then use function:
`_Get_<subtype>(self)`.

Value should be returned by this function or exception threw in case of error.

### Setter

The default function used to set control's value is implemented by overriding:
`_set(self, logical_value)`

There is a possibility to implement different subtypes of setter function
by specifying `subtype` attribute to the control definition. It will then use function:
`_Set_<subtype>(self, logical_value)`.

## Data files

Data files are written in XML and their role is to define available
[controls](#control), connect them with the drivers written in python and optionally
provide additional parameters.

Example of how the data file should look like:
```xml
<root>
  <include>
    <name>base.xml</name>
  </include>
  <map>
    <name>example_map</name>
    <params on="1" off="0"/>
  </map>
  <control>
    <name>example_control</name>
    <params drv="some_driver" interface="some_interface" map="example_map"/>
  </control>
</root>
```

### Available tags

* root
* include
  * name
* map
  * name
  * doc
  * params
* control
  * name
  * doc
  * params
    * content
      * item

### Include

This tag allows splitting data into multiple files, sharing common controls between
multiple devices of one family, while defining model-specific ones in the model
configuration file.
Includes are always done before parsing any other data from the XML file, so the most
nested files will be parsed first.

```xml
<include>
 <name>common.xml</name>
</include>
```

The value in the name tag consists of the filename and extension, without the path.  
All included files should be located in the [servo/data](../servo/data) directory.

### Interface

Transport layer for drivers, they have integer identifiers which differ by servo version
connected between host and DUT. It allows to select the destination of commands while
using one USB cable to servo.
Some controls define `servo` as interface. It's used by controls that don't require
any interface to communicate, because, for example, they return constant data, or data
set in the control definition.
Interfaces are defined in the
[`servo/servo_interfaces.py`](../servo/servo_interfaces.py) file.

Common interfaces are:
* `2`: DUT i2c for INAs
* `8`: AP console
* `9`: GSC console
* `10`: EC console

### Mapping

Mappings allow to convert integer values to more human-readable ones.
They also allow to specify available range of values that could be set to the control.
It’s still possible to use integer values instead of mappings, so drivers have to take
this into account and validate provided values.

```xml
<map>
  <name>onoff_sbu_uart_sel</name>
  <doc>Select between CCD or UART on SBU. Default is CCD</doc>
  <params ccd="0" uart="1"></params>
</map>
```

* `name` - name of the mapping to use in the control definition
* `doc` - documentation
* `params` - specifies all available values to get and set to the control using this
  mapping

In the example above, there are two values available ccd and uart.

```console
$ dut-control -- sbu_uart_sel
sbu_uart_sel:ccd
$ dut-control -- sbu_uart_sel:uart
$ dut-control -- sbu_uart_sel
sbu_uart_sel:uart
```

However, integer values may be used, instead of mapped strings. But returned values will
always be mapped.
```console
$ dut-control -- sbu_uart_sel:0
$ dut-control -- sbu_uart_sel
sbu_uart_sel:ccd
$ dut-control -- sbu_uart_sel:1
$ dut-control -- sbu_uart_sel
sbu_uart_sel:uart
$ dut-control -- sbu_uart_sel:5
Problem with ['sbu_uart_sel:5'] :: 5
$ dut-control -- sbu_uart_sel
sbu_uart_sel:uart
```

Mappings can be used to hide implementation details, for example if GPIO is using normal
or inverted logic (like reset pins usually). We can create two mapping for both logics
and use them accordingly, allowing users to use `high` or `low` values to `dut-control`
despite one pin being in inverted logic to the other one.

```xml
<map>
 <name>gpio_state</name>
 <doc>Physical state of the GPIO</doc>
 <params off="0" on="1" high_z="2" />
</map>
```

```xml
<map>
 <name>gpio_state_i</name>
 <doc>Physical state of the GPIO with inverted logic</doc>
 <params off="1" on="0" high_z="2" />
</map>
```

### Control

Control is a basic thing that the `dut-control` and `servod` operates on.
It’s the layer of communication between host and DUT.

Controls use drivers defined in the `servo/drv/<name>.py` files, where `<name>`
(without py suffix) is the name of a driver.
Control tag should have a params tag with attributes that specify
which driver it uses (`drv`), on what interface (`interface`), which mapping is used if
any (`map`) and what to do if control with such name is defined more than once
(`clobber_ok`).

Controls are distinguished by their names, and since controls may be specified within
multiple files, there is a risk of name collisions. To prevent that, controls by default
cannot be overridden and trying to do so will result in error during startup of servod.
To change this behavior, control must define clobber_ok attribute which defines if and
how the control may be overridden.

Attribute `clobber_ok` has few values possible to set:
* `patch`
  * If control of the same name doesn’t exist, it won’t be created
  * If there are parameters specified in previous control definition but not overridden
  in this, they are **NOT** removed
  * Only change parameters specified in this control
* `full`
  * If control of the same name doesn’t exist, it will be created
  * Remove all parameters from previous definition of the control and add only new ones
* `never`
  * If control of the same name exists, whole tag is skipped
  * If there’s no control with the same name, define a new control with specified
  parameters

Example of control definition:

```xml
<control>
  <name>ec3po_c2d2_uart</name>
  <alias>c2d2_uart_pty</alias>
  <doc>C2D2 console provided via EC-3PO console interpreter.</doc>
  <params cmd="get" subtype="pty" interface="6" drv="uart"/>
</control>
```

* `name` - defines name used to get and set value for the control
  (`dut-control -- name` / `dut-control -- name:new_value`)
* `alias` - additional name to reference the control
  (`dut-control -- name` == `dut-control -- alias`)  
  Multiple aliases should be defines in one tag, separated by commas (`,`).
* `doc` - documentation (visible with `dut-control -- --get-all --verbose`)
* `params` - sets parameters of the function. May be specified once or twice within one
  control, depending if function support both getting and setting or if the parameters
  are the same or different for getter and setter.
  Can contain `content` tag within, described [later](#params-content).  
  May contain following attributes:
  * `cmd` - specifies if the defined parameters are for `get` or `set` type of method.
    If the parameter is missing from the tag, it means it’s a definition of both
    methods.
  * `subtype` - optional, used when the driver provides multiple implementations of the
    getters and setters.
    For example, the GPIO driver implements methods for getting and setting a
    single GPIO pin or a multiple pins (`single` / `multi`).
  * `interface` - numerical identifier of the interface that command should be executed
    on. For example to execute command on an AP console, EC console or servo console.
    Identifiers depend on the connector/servo used to communicate with DUT.
    More details in the [Interface](#interface) paragraph.
  * `drv` - name of the driver. Its implementation should be in file
    `servo/drv/<drv>.py`
    * `content` - not specified in this example, can provide additional constant
      parameters to the driver. More details in the
      [Writing control that uses macro driver](#writing-control-that-uses-macro-driver)
      paragraph.
  * `init` - optional, contains value set to the control at the initialization of the
    servod. Used to restore device to known state at the initialization, for example
    may disable write-protect to allow out-of-the-box experience for users.  
    Supports the same values as allowed by `dut-control`, both numerical and
    mapped strings.  
    Since these values provide stable, well-known environment, it may be useful to be
    able to restore the device to this state after modifying controls manually. This
    can be done by using `dut-control` with `--hwinit` parameter:  
    ```console
    $ dut-control -- --hwinit
    ```  
    It sets all controls with defined `init` state to the predefined values.

#### Params Content

The `content` tag within `params` of `control` allows the control to provide additional
constant parameters to the driver. This allows the driver to be more elastic and
configurable.  
The usage of items in the content tag is implementation specific for different drivers
and doesn't have any specific meaning. To understand how it should be used, it's
advised to read documentation in the python file that implements the driver.
A good example of its usage is the `macro` driver which takes provided parameters and
executes them in order, allowing to define more complex logic behind one simple
control.  
Usage of macro driver is available in [further](#writing-control-that-uses-macro-driver)
paragraph.

### How to write new controls

---
**NOTE**

The XML file should contain the `root` tag as the main tag. All mappings and controls
definitions must be within the `root` tag. For clarity, this tag is skipped in the
examples, as they show only definitions of `map` and `control` tags.

---

#### Controlling the GPIO

As an example of writing new control, we will try to control the LED on the servo_v4p1
device.
The name of the GPIO (connected by the IO expander) of the LED is
`TCA_GPIO_DBG_LED_K_ODL`.
We can try controlling it manually by using servo's console:

```console
$ dut-control -- servo_v4p1_uart_pty
servo_v4p1_uart_pty:/dev/pts/6
$ minicom -D /dev/pts/6
> ioexset TCA_GPIO_DBG_LED_K_ODL 0
```

As we can see, while setting the pin to 0, the LED is lit.
Let's start by writing the boilerplate for the control with name and documentation:

```xml
<control>
  <name>led_gpio</name>
  <doc>LED on servo (using ioexget and ioexset command)</doc>
  <params />
</control>
```

Now we need to fill the params tag to define how this control should be controlled.
We will start by looking at the interface identifier we have to use.
We can see all available interfaces in the file
[`servo/servo_interfaces.py`](../servo/servo_interfaces.py) for different devices.
We are using servo_v4p1 (which has same interfaces as servo_v4) and we want to execute
commands in its console. So we are searching for `servo v4 console`. It's defined as:
```
"name": "ec3po_uart",  # 26: servo v4 console
```

The number after the hash sign is the identifier.
It's the index in the array of available interfaces.
So now, out params tag looks like this:
`<params interface="26" />`

There are different drivers available in servod, but the one that we want to
use is `ec3po_gpio`. It's defined in
[`servo/drv/ec3po_gpio.py`](../servo/drv/ec3po_gpio.py) file.
It allows to modify GPIOs on the servo, both native and through IO expanders.
For available parameters of this driver, we may need to check the source code of
`_drv_init` function (and its documentation).  
We see that the required parameters are `subtype`, `name`, and `ioex`.
* `subtype` specifies if we want to modify single pin or multiple ones.
* `name` is the name of the GPIO we want to modify
* `ioex` defines if the pin is native GPIO or if it is connected by IO expander.
  That selects either `gpioget/gpioset` or `ioexget/ioexset` function.

We want to modify single pin named `TCA_GPIO_DBG_LED_K_ODL` that is connected by IO
expander. So our parameters will now look like this:  
`<params interface="26" drv="ec3po_gpio" subtype="single" name="TCA_GPIO_DBG_LED_K_ODL" ioex="true"/>`

And whole control definition is now:

```xml
<control>
  <name>led_gpio</name>
  <doc>LED on servo (using ioexget and ioexset command)</doc>
  <params interface="26" drv="ec3po_gpio" subtype="single" name="TCA_GPIO_DBG_LED_K_ODL" ioex="true"/>
</control>
```

We can verify if it's working by building the servod and running local instance:
```console
$ build-servod
...
$ start-servod -c local
```

And to modify the control by using `dut-control` we can execute:
```
$ dut-control -- led_gpio:1
$ dut-control -- led_gpio:0
```

This LED is blinking periodically, but we may see that our control still changes it.

Now to make it more meaningful, we may create a mapping of human-readable values.
To make this, we will create a mapping of string values to integers.
Remember to define the mappings before the controls.
It's more clear when we define mappings together and then the controls together.

```xml
<map>
  <name>servo_led_i</name>
  <doc>Inverted logic for LED on servo</doc>
  <params lit="0" dim="1"></params>
</map>
```

The name contains some meaningful string and suffix `_i` which is a standard naming for
controls that uses inverted logic.
As params, we specify the human-readable string and assign to it any value that it
represents.
The values may be in decimal, hexadecimal, binary or float notations.
As for servo, we define that the LED will be lit when `0` is assigned, and will be dim
when `1` is assigned.

After creating the mapping, now we have to assign the mapping to the control we created
before.  
We need to add `map="servo_led_i"` attribute to the `params` tag we already created.

So the final definition of the control will look like:
```xml
<control>
  <name>led_gpio</name>
  <doc>LED on servo (by gpio command)</doc>
  <params interface="26" drv="ec3po_gpio" subtype="single" name="TCA_GPIO_DBG_LED_K_ODL" ioex="true" map="servo_led_i"/>
</control>
```

And now we can execute `dut-control` using either mapped values or numerical ones:

```console
$ dut-control -- led_gpio:dim
$ dut-control -- led_gpio:lit
$ dut-control -- led_gpio:0
$ dut-control -- led_gpio:1
```

We can verify the controls work by opening the servo_v4p1 console using minicom as
described before and we will see commands executed by `dut-control`:
```
> ioexset TCA_GPIO_DBG_LED_K_ODL 1
>
> ioexset TCA_GPIO_DBG_LED_K_ODL 0
>
> ioexset TCA_GPIO_DBG_LED_K_ODL 0
>
> ioexset TCA_GPIO_DBG_LED_K_ODL 1
```

#### Issuing I2C transfers

As another example, we will try to achieve the same as in previous
example - control the servo's LED - but this time by executing the I2C transfers directly
to the IO expander.

---
**NOTE**

For details about addresses, offsets (registers) and values, we can take a look at the
[TCA6424 IO expander specification](https://www.ti.com/lit/gpn/TCA6424).

---

As previously, we start by writing boilerplate for the control. 
Now we will add the `_i2c` suffix to make it different from previous control.
```xml
<control>
  <name>led_i2c</name>
  <doc>LED on servo (by i2c command)</doc>
  <params cmd="get"/>
  <params cmd="set"/>
</control>
```

This time we will use the `ec_i2c_pin` driver, which allows to read and write values
using I2C interface.

Looking at the documentation of the IO expander, we will have to access different
registers to read and to write pin value, so now we will have two `params` tag within
our control. One for `set` and other for `get` command.

The definition of the LED pin can be checked in the EC repository at
`board/servo_v4p1/gpio.inc` and is as stated:
`IOEX(TCA_GPIO_DBG_LED_K_ODL, 	EXPIN(1, 2, 7), GPIO_OUT_LOW)`

It means that the pin is on second (`0, 1`) IO expander, which is on the I2C bus `1`, on
the third (`0, 1, 2`) port and on 8th (`1 << 7`) pin.  
From IO expander specification, we may know that the third input port will be
(a register) at offset `0x02` and output port at `0x06`.  
The mask allow to change multiple bits at once, but since we want to change
only one pin, our mask selects only 8th (`1 << 7` == `0x80`) bit in the byte.  
We will use the servo v4p1 console, because the servo's firmware support I2C
shell commands, so the interface is `26` as in previous example.  
Knowing these details, we may write them as parameters to the driver.  
So our definition of the control now should look like:

```xml
<control>
  <name>led_i2c</name>
  <doc>LED on servo (by i2c command)</doc>
  <params cmd="get" interface="26" bus="1" addr="0x23" offset="0x02" mask="0x80" drv="ec_i2c_pin"/>
  <params cmd="set" interface="26" bus="1" addr="0x23" offset="0x06" mask="0x80" drv="ec_i2c_pin"/>
</control>
```

And we can also add the mapping from previous example:
```xml
<map>
  <name>servo_led_i</name>
  <doc>Inverted logic for LED on servo</doc>
  <params lit="0" dim="1"></params>
</map>
...
<control>
  <name>led_i2c</name>
  <doc>LED on servo (by i2c command)</doc>
  <params cmd="get" interface="26" bus="1" addr="0x23" offset="0x02" mask="0x80" drv="ec_i2c_pin" map="servo_led_i"/>
  <params cmd="set" interface="26" bus="1" addr="0x23" offset="0x06" mask="0x80" drv="ec_i2c_pin" map="servo_led_i"/>
</control>
```

Now we can build and run servod:
```console
$ build-servod
...
$ start-servod -c local
```

We can open servo v4p1 console in another window to verify that the commands are
executed properly:

```console
$ dut-control -- servo_v4p1_uart_pty
servo_v4p1_uart_pty:/dev/pts/9
$ minicom -D /dev/pts/9
```

And we can check and change the control value:
```console
$ dut-control -- led_i2c
led_i2c:dim
$ dut-control -- led_i2c:lit
```

And we can check the output:
```
> i2cxfer r 1 0x23 0x2
0xc2 [194]
> i2cxfer r 1 0x23 0x6
0x7f [127]
> i2cxfer w 1 0x23 0x6 0x7f
```

---
**NOTE**

The lines starting with `chan` were removed. They are executed to allow dut-control to
check the output of executed commands in the servo console.

---

#### Writing control that uses macro driver

As example on how to use the `macro` driver and use the `content` tag, we will define
a control that blinks the servo's LED for some time. It will use controls defined in the
previous paragraphs.  
Our starting point is a control definition with such parameters:

```xml
<control>
    <name>led_blink</name>
    <doc>Blink the LED on servo</doc>
    <params drv="macro" interface="servo">
    </params>
  </control>
```

We define the control named `led_blink` with params that selects the `macro` driver
and interface as servo.
Since we want to have `content` tag within the `params`, we will close the `params` tag
in the separate line, not inline within one pair of the triangle brackets.  

Macro driver let get and set values of multiple controls at once. In case of getting,
if controls have different values, there is no guarantee which value will be returned.
The different behaviors and edge-cases are described in the driver file
[`servo/drv/macro.py`](../servo/drv/macro.py).
We will describe setting (action) controls in this example.

Content tag contains one or more `item` tag with attributes that are driver specific.

```xml
<params drv="macro" interface="servo">
  <content>
    <item key="macro_map">
    </item>
  </content>
</params>
```

The `macro` driver expects item with key `macro_map` which will contain actions to be
done by the driver. Within it, we will declare more items with `key` attributes. The
value of `key` will be used as the `dut-control` parameter to declare which action
should be executed.

```xml
<content>
  <item key="macro_map">
    <item key="1">
      <item>led_i2c:1</item>
    </item>
  </item>
</content>
```

We have added new `item` with `key` equals `1`. This means that we are defining actions
to be done when we assign the `1` to the control we are defining.
Since out control name is `led_blink`, we can try out control now:

`dut-control -- led_blink:1`

It will execute the actions defined within the item with key `1`. We can use any
numerical values or strings if we have declared mapping used. Without mapping, only
numerical values apply here. They don't have to be in order, we can use any value.

At this moment, executing the `dut-control -- led_blink:1` will result in the same
action as executing `dut-control -- led_i2c:1`. The true benefit of using `macro` driver
is when defining multiple items. We use the control `sleep` which hangs dut-control
for specified amount of seconds.

`dut-control -- sleep:0.5` will hang for about half a second (not including time to
start the docker container).

We will define multiple sets to the led_i2c, alternating from `0` to `1` and sleep
in-between.

Now the `item` with `key` as `1` will look like this:

```xml
<item key="1">
  <item>led_i2c:0</item>
  <item>sleep:0.2</item>
  <item>led_i2c:1</item>
  <item>sleep:0.2</item>
  <item>led_i2c:0</item>
  <item>sleep:0.2</item>
  <item>led_i2c:1</item>
  <item>sleep:0.2</item>
  <item>led_i2c:0</item>
  <item>sleep:0.2</item>
</item>
```

This action now should take 1 second and blink the LED a few times during that time.
We can try executing this control by using

`dut-control -- led_blink:1`

Dut-control finishes the execution after all the actions happen. We should be able to
see the LED blinks faster than in normal run of servo.

Now we can define another item which will blink for a 3 seconds. To do that, we define
another item within the `item` with `macro_map` as key, next to the one with `1` as a
`key`.

Definition of our control should look similar this template:

```xml
  <control>
    <name>led_blink</name>
    <params drv="macro" interface="servo">
      <content>
        <item key="macro_map">
          <item key="1">
            ...
          </item>
          <item key="3">
            ...
          </item>
        </item>
      </content>
    </params>
  </control>
```

We can copy-paste the existing content of previous item to new one multiple times:
```xml
<item key="3">
  <item>led_i2c:0</item>
  <item>sleep:0.2</item>
  <item>led_i2c:1</item>
  <item>sleep:0.2</item>
  <item>led_i2c:0</item>
  <item>sleep:0.2</item>
  <item>led_i2c:1</item>
  <item>sleep:0.2</item>
  <item>led_i2c:0</item>
  <item>sleep:0.2</item>
  <item>led_i2c:1</item>
  <item>sleep:0.2</item>
  <item>led_i2c:0</item>
  <item>sleep:0.2</item>
  <item>led_i2c:1</item>
  <item>sleep:0.2</item>
  <item>led_i2c:0</item>
  <item>sleep:0.2</item>
  <item>led_i2c:1</item>
  <item>sleep:0.2</item>
  <item>led_i2c:0</item>
  <item>sleep:0.2</item>
  <item>led_i2c:1</item>
  <item>sleep:0.2</item>
  <item>led_i2c:0</item>
  <item>sleep:0.2</item>
  <item>led_i2c:1</item>
  <item>sleep:0.2</item>
</item>
```

Now we can execute our control in form of:  
`dut-control -- led_blink:1`  
which will blink for 1 second, and in form of:  
`dut-control -- led_blink:3`  
which will blink the LED for 3 seconds.

If we execute the control with invalid value, `dut-control` will return an error
and will print supported states:

```console
$ dut-control -- led_blink:2
Problem with ['led_blink:2'] :: Invalid state: '2'  Supported states: ['1', '3']
```

Whole final definition of the control should look like this:

```xml
  <control>
    <name>led_blink</name>
    <doc>Blink the LED on servo</doc>
    <params drv="macro" interface="servo">
      <content>
        <item key="macro_map">
          <item key="1">
            <item>led_i2c:0</item>
            <item>sleep:0.2</item>
            <item>led_i2c:1</item>
            <item>sleep:0.2</item>
            <item>led_i2c:0</item>
            <item>sleep:0.2</item>
            <item>led_i2c:1</item>
            <item>sleep:0.2</item>
            <item>led_i2c:0</item>
            <item>sleep:0.2</item>
          </item>
          <item key="3">
            <item>led_i2c:0</item>
            <item>sleep:0.2</item>
            <item>led_i2c:1</item>
            <item>sleep:0.2</item>
            <item>led_i2c:0</item>
            <item>sleep:0.2</item>
            <item>led_i2c:1</item>
            <item>sleep:0.2</item>
            <item>led_i2c:0</item>
            <item>sleep:0.2</item>
            <item>led_i2c:1</item>
            <item>sleep:0.2</item>
            <item>led_i2c:0</item>
            <item>sleep:0.2</item>
            <item>led_i2c:1</item>
            <item>sleep:0.2</item>
            <item>led_i2c:0</item>
            <item>sleep:0.2</item>
            <item>led_i2c:1</item>
            <item>sleep:0.2</item>
            <item>led_i2c:0</item>
            <item>sleep:0.2</item>
            <item>led_i2c:1</item>
            <item>sleep:0.2</item>
            <item>led_i2c:0</item>
            <item>sleep:0.2</item>
            <item>led_i2c:1</item>
            <item>sleep:0.2</item>
          </item>
        </item>
      </content>
    </params>
  </control>
```

##### Init values

As any other control, controls that uses `macro` driver can define initial value.  
We can add the `init` attribute to `params` tag of our control to provide the value:  
```xml
<params drv="macro" interface="servo" init="3">
```  

Now, if we start `servod` or restore the initial values using  `dut-control -- --hwinit`
we will see the LED blinking on the servo that we are using.

## References

References / More implementation details  
* [Servod system overview](servod.md#System-overview)
* [Servod F.A.Q.](servod_faq.md#Where-is-the-code-logic-for-the-control) - generic overview how drivers work, available interfaces and how to write new driver
* [Servod drivers](servod_drv.md) - more information about writing drivers and available parameters used while writing data XMLs
* [SystemConfig implementation](../servo/system_config.py#46) - documentation about available tags in the XML files, some examples and other implementation details (some are available as comments to other functions in the file)
* [Macro driver](../servo/drv/macro.py) - documentation about macro driver, providing usage of content tag within params of the control.
