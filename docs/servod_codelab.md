# Servod Configuration and Driver Development Codelab

Welcome to the `servod` team! This codelab provides an exhaustive, step-by-step
onboarding guide for hardware engineers and developers.  
You will learn the exact workflows for defining XML overlays, mapping control values,
authoring custom Python drivers, and validating your implementations on physical
hardware setups.

---

## Prerequisites

Before starting this codelab, ensure you have:
1. A configured ChromeOS development environment with access to the `hdctools`
   source tree (`third_party/hdctools`).
2. Installed and running docker as [described here](servod_outside_chroot.md).
3. Familiarity with running shell scripts and basic Python object-oriented design.
4. Reviewed repository rules regarding commit formats (`BUG=`, `TEST=`) and pre-commit
   linting.

---

## Module 1: Understanding Servod Architecture

`servod` (Servo Daemon) acts as the central hardware abstraction layer.  
Clients do not talk to debug hardware directly; they send requests to `servod`, which
translates logical commands into hardware-specific protocol executions.

### Core Control Flow

```
+------------------------------------+
|      Client CLI: dut-control       |
+-----------------+------------------+
                  |
                  | Requests: dut-control -- led_status
                  v
+-----------------+------------------+
|          Servod Daemon             |
+-----------------+------------------+
                  |
                  | Looks up control in
                  v
+-----------------+------------------+
|           XML Overlays             |
|           (data/*.xml)             |
+-----------------+------------------+
                  |
                  | Routes to specified
                  v
+-----------------+------------------+
|          Python Driver             |
|           (drv/*.py)               |
+-----------------+------------------+
                  |
                  | Extracts XML params & executes
                  v
+-----------------+------------------+
|       Hardware Interface           |
|           (FTDI/PTY)               |
+-----------------+------------------+
                  |
                  | Physical signaling
                  v
+-----------------+------------------+
|         Hardware Target            |
|              (DUT)                 |
+-----------------+------------------+
```


### Verification & Execution Basics

> **Hardware Connection Requirement**: Prior to launching `servod`, you **must** verify
that the physical debug hardware (Servo V4.1, Servo Micro, or SuzyQ cable) is properly
connected to both the host machine and the target Device Under Test (DUT).  
Charger should also be connected to `DUT power` port to make sure debug communication
will be properly detected and enabled.  
`servod` validates interface connectivity during bringup and will fail initialization
if the target controllers are missing.

Whenever you modify configurations or drivers, you must rebuild the containerized
`servod` environment and relaunch the daemon to verify changes:

```bash
# 1. Rebuild the local servod Docker image
./scripts/build-servod

# 2. Start the daemon in the background (replace <board> with your target)
# Note: If model is omitted, the --nomodel flag must be provided explicitly
./scripts/start-servod -b <board> --nomodel

# 3. Query controls from another terminal passing arguments after the double-dash
# wrapper separator
dut-control -- serialname
```

---

## Module 2: Basic XML Overlays

To support a new hardware target, you create a declarative XML overlay.
`servod` loads base configurations (e.g., standard interfaces) and applies your specific
overlay definitions on top.

### Structural Elements of Servod XML

#### 1. `<root>`
The mandatory top-level container enclosing all definitions.
```xml
<root>
  <!-- All configs go here -->
</root>
```

#### 2. `<include>`
Inherits controls, maps, and parameters from existing base files.
```xml
<include>
  <name>common.xml</name>
</include>
```

#### 3. `<control>`
Defines a named CLI command accessible via `dut-control`.
```xml
<control>
  <name>my_simple_command</name>
  <doc>Human readable description shown in help menus.</doc>
  <params cmd="get" interface="servo" drv="echo" value="ok"/>
</control>
```

### Exhaustive Attribute Descriptions for `<params>`

Every attribute inside a `<params>` tag dictates how `servod` routes and executes
the control:

| Attribute | Purpose & Behavior | Example Values |
| :--- | :--- | :--- |
| **`cmd`** | Defines the execution direction. Use `"get"` for read-only accessand `"set"` for write-only access. If a control supports both, standard practice requires defining separate `<params>` tags for each direction if internal parameters differ. | `"get"`, `"set"` |
| **`interface`** | Identifies the communication channel index. Numeric values (`"1"`, `"2"`) map to specific FTDI/USB endpoints. Special keywords like `"servo"` indicate the command targets internal daemon logic rather than external pins. | `"1"`, `"servo"`, `"AP_CONSOLE"` |
| **`drv`** | The base name of the Python driver file responsible for execution. `servod` dynamically locates `servo/drv/<drv_name>.py` to handle the request. | `"echo"`, `"gpio"`, `"i2c_reg"` |
| **`value`** | A custom argument passed directly into the driver's initialization parameters. For the `echo` driver, this defines the exact static string returned to the user. | `"ready"`, `"static_state"` |
| **`input_type`** | Enforces strict type casting and validation on input arguments provided via the CLI before passing them to the driver. | `"str"`, `"int"`, `"float"` |
| **`clobber_ok`** | Dictates how to reconcile redefinition of an existing control. `"full"` (default when omitted for existing controls) discards all base parameters. `"patch"` merges new parameters with existing ones. `"never"` ignores the new definition. | `"full"`, `"patch"`, `"never"` |


Interface numbers are defined in a file: `servo/data/servo_interfaces.py`.  
If possible, use predefined aliases, for example `GSC_CONSOLE`, `EC_CONSOLE` instead
of numbers like `9`, `10`.

### Exercise 2.1: Authoring a Base Overlay

**Task**: Create the foundational overlay for a new board named **"Codetalker"**.

1. Create file: `servo/data/servo_codetalker_overlay.xml`.
2. Define the XML structure inheriting from `common.xml`.
3. Implement a read-only verification control named `codetalker_status`.

**File Content (`servo/data/servo_codetalker_overlay.xml`)**:
```xml
<?xml version="1.0"?>
<root>
  <!-- Pull in standard global definitions -->
  <include>
    <name>common.xml</name>
  </include>

  <!-- Define custom board verification control -->
  <control>
    <name>codetalker_status</name>
    <doc>Static status indicator for Codetalker hardware bringup.</doc>
    <params cmd="get" interface="servo" drv="echo" value="nominal" input_type="str"/>
  </control>
</root>
```

### Module 2 Verification Instructions
Execute these commands from the repository root to validate your XML syntax and logic:

```bash
# Rebuild image injecting the new XML file
./scripts/build-servod

# Launch servod targeting the new Codetalker overlay
./scripts/start-servod -b codetalker --nomodel

# Verify the control returns the expected static string
dut-control -- codetalker_status
# Expected Output: codetalker_status:nominal
```

---

## Module 3: Advanced XML and Mapping

Raw hardware registers and physical pins communicate in numeric bits (`0`, `1`).  
To create intuitive tools, we use `<map>` elements to translate human strings to
hardware logic, and override inherited defaults.

> **Simulation Routing Advantage**: Real hardware drivers like `gpio` validate physical
bus endpoints during initialization. If attached debug hardware is missing, mapping
controls targeting physical interfaces will cause `servod` to fail or reject bringup.
For these exercises, we utilize the built-in **`sflag`** (software flag) driver paired
with `interface="servo"` to simulate hardware state memory securely without crashing.

### Incremental Implementation Guide

#### Step 3.1: Define a Raw Simulated Control
First, let's expose raw binary access to a simulated debug LED memory store.
Add this to your `servo_codetalker_overlay.xml`:

```xml
  <!-- Step 1: Raw unmapped simulation access -->
  <control>
    <name>codetalker_led_raw</name>
    <doc>Simulated raw numeric access to the Codetalker debug LED state.</doc>
    <params cmd="get" interface="servo" drv="sflag"/>
    <params cmd="set" interface="servo" drv="sflag" input_type="int"/>
  </control>
```

#### Step 3.2: Create a State Map
Users shouldn't need to remember if `1` means on or off.
Define a custom map translating explicit state strings:

```xml
  <!-- Step 2: Define translation dictionary -->
  <map>
    <name>codetalker_led_states</name>
    <doc>Translates user strings to simulated binary logic levels.</doc>
    <params illuminated="1" extinguished="0"></params>
  </map>
```

#### Step 3.3: Apply Mapping to a User-Facing Control
Now, define the final control that applies the map to abstract the underlying raw
operations. Because both controls target the shared `sflag` state memory, modifying
one updates the other automatically:

```xml
  <!-- Step 3: Mapped intuitive control -->
  <control>
    <name>codetalker_led</name>
    <doc>Controls the simulated debug LED state intuitively.</doc>
    <params cmd="get" interface="servo" drv="sflag" map="codetalker_led_states"/>
    <params cmd="set" interface="servo" drv="sflag" map="codetalker_led_states" input_type="str"/>
  </control>
```

#### Step 3.4: Override an Inherited Base Control
To customize behavior defined in `common.xml` (e.g., adding board-specific
categorization tags to the `loglevel` control), re-declare the control using the
identical name.  
`servod` honors the final overlay entry:

```xml
  <!-- Step 4: Safe override of existing base controls -->
  <control>
    <name>loglevel</name>
    <doc>Overridden loglevel control injecting Codetalker telemetry tags.</doc>
    <params drv="loglevel" interface="servo" input_type="str" tag="codetalker_telemetry"/>
  </control>
```

**Control Overriding and `clobber_ok` Mechanics**:
When redefining an inherited control, understand how `servod` reconciles the new
definition with the base one.  
This is controlled by the `clobber_ok` attribute in the `<params>` tag:

* **Default Behavior (Omitted or `clobber_ok="full"`)**: `servod` performs a
  **full clobber**. *All* parameters from the base control are discarded, and only the
  newly defined parameters are kept. If you omit `clobber_ok`, you
**must re-specify all mandatory parameters** (e.g., `drv`, `interface`, `input_type`),
  otherwise initialization will fail with missing driver errors.
* **`clobber_ok="patch"`**: Merges the new parameters into the existing definition.
  Only the specified parameters are updated or added; all other inherited parameters
(like `drv`) are preserved. Use this for safe, incremental updates.
* **`clobber_ok="never"`**: The new definition is quietly ignored if the control
  already exists, keeping the base definition intact.


### Complete Updated File View
Your `servo_codetalker_overlay.xml` should now look like this:

```xml
<?xml version="1.0"?>
<root>
  <include>
    <name>common.xml</name>
  </include>

  <map>
    <name>codetalker_led_states</name>
    <doc>Translates user strings to simulated binary logic levels.</doc>
    <params illuminated="1" extinguished="0"></params>
  </map>

  <control>
    <name>codetalker_led_raw</name>
    <doc>Simulated raw numeric access to the Codetalker debug LED state.</doc>
    <params cmd="get" interface="servo" drv="sflag"/>
    <params cmd="set" interface="servo" drv="sflag" input_type="int"/>
  </control>

  <control>
    <name>codetalker_led</name>
    <doc>Controls the simulated debug LED state intuitively.</doc>
    <params cmd="get" interface="servo" drv="sflag" map="codetalker_led_states"/>
    <params cmd="set" interface="servo" drv="sflag" map="codetalker_led_states" input_type="str"/>
  </control>

  <control>
    <name>loglevel</name>
    <doc>Overridden loglevel control injecting Codetalker telemetry tags.</doc>
    <params drv="loglevel" interface="servo" input_type="str" tag="codetalker_telemetry"/>
  </control>
</root>
```

### Module 3 Verification Instructions
Validate the mapping execution and override properties:

```bash
./scripts/build-servod
./scripts/start-servod -b codetalker --nomodel

# Verify raw integer assignments
dut-control -- codetalker_led_raw:1
dut-control -- codetalker_led_raw

# Verify mapped string translations
dut-control -- codetalker_led:illuminated
dut-control -- codetalker_led

# Check metadata to confirm override tags were applied successfully
dut-control -- --info loglevel
```

---

## Module 4: Writing Custom Python Drivers

When standard drivers cannot support complex timing sequences or specialized multi-pin
logic, write a custom driver class.

### Architectural Constraints & Naming Rules
1. **Base Class Inheritance**: Must inherit from `servo.drv.hw_driver.HwDriver`.
2. **Strict Class Naming**: The Python class name **must perfectly match** the camelCase
   conversion of the XML `drv` string executed by `string_utils.snake_to_camel()`.
   - `drv="power_sequencer"` $\rightarrow$ `class powerSequencer(hw_driver.HwDriver):`
   - `drv="simple_logic"` $\rightarrow$ `class simpleLogic(hw_driver.HwDriver):`
   - Single words remain lowercase: `drv="echo"` $\rightarrow$ `class echo(...)`

### Thorough Code Mechanics Breakdown

- **`_drv_init(self)`**: Executed once during daemon initialization. Used to safely
  extract configuration parameters passed down via the XML `<params>` dictionary
  (`self._params`).
- **`_get(self)`**: Invoked on read operations. Must return the raw logical state.
  If an XML `<map>` applies, `servod` handles translating this output back to a human
  string automatically.
- **`_set(self, logical_value)`**: Invoked on write operations.
  The incoming `logical_value` has already been validated and mapped to its numeric
  equivalent by the daemon if a map was declared.
- **Exception Safety**: Never allow raw Python runtime errors or unformatted tracebacks
  to bubble up to the CLI user. Wrap hardware failures cleanly in
  `hw_driver.HwDriverError`.

### Exercise 4.1: Developing a State-Tracking Sequencer Driver

> **Advanced Routing Concept**: `servod` instantiates **separate** Python driver objects
to handle a control's `get` and `set` operations independently.
If your custom driver implements software state tracking without backing hardware
registers, storing values in simple instance variables (`self._state`) will fail because
the read instance cannot see the write instance's modifications.
To synchronize execution, declare shared tracking dictionaries at the **class level**.

**Task**: Implement a custom driver supporting initialization checks, shared state
synchronization across read/write driver instances, and secure error boundaries.

Create file: `servo/drv/codetalker_sequencer.py`.

```python
# Copyright 2026 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Custom multi-stage power sequencing driver for Codetalker hardware."""

from servo.common.exceptions import HwDriverError
from servo.drv import hw_driver


# Rule: Class name perfectly matches camelCase translation of drv="codetalker_sequencer"
class codetalkerSequencer(hw_driver.HwDriver):
    """Executes tracked state transitions for board power rails."""

    # Class-level dictionary shared across independent 'get' and 'set' driver instances
    RAIL_STATES = {}

    def _drv_init(self):
        """Constructor hook. Safely extracts XML <params> configuration."""
        super()._drv_init()
        
        # Extract custom parameters defined in the XML configuration
        self._rail_id = self._params.get("rail_id", "unknown_rail")
        self._max_stages = int(self._params.get("max_stages", 3))

        # Enforce mandatory parameters
        if "rail_id" not in self._params:
            raise HwDriverError(
                "Driver configuration error: Missing mandatory 'rail_id' parameter."
            )
            
        # Initialize shared static memory for this specific rail if not already tracked
        if self._rail_id not in self.RAIL_STATES:
            self.RAIL_STATES[self._rail_id] = 0
            
        self._logger.debug("Initialized sequencer for rail: %s", self._rail_id)

    def _get(self):
        """Processes read requests ('dut-control -- codetalker_rail_state')."""
        try:
            # Return current stage integer from shared state store
            return self.RAIL_STATES[self._rail_id]
        except Exception as e:
            # Rule: Prevent raw traceback leakage by wrapping cleanly
            raise HwDriverError(
                f"Failed to query power stage on rail {self._rail_id}: {str(e)}"
            ) from e

    def _set(self, logical_value):
        """Processes write commands ('dut-control -- codetalker_rail_state:<val>')."""
        try:
            current_stage = self.RAIL_STATES[self._rail_id]
            if logical_value == "advance":
                if current_stage < self._max_stages:
                    self.RAIL_STATES[self._rail_id] = current_stage + 1
                else:
                    self._logger.warning("Power sequence already at maximum stage.")
            elif logical_value == "reset":
                self.RAIL_STATES[self._rail_id] = 0
            else:
                # Direct stage assignment attempt
                target = int(logical_value)
                if 0 <= target <= self._max_stages:
                    self.RAIL_STATES[self._rail_id] = target
                else:
                    raise ValueError(f"Stage out of bounds (0-{self._max_stages})")
        except Exception as e:
            raise HwDriverError(
                f"Hardware sequencing failure on rail {self._rail_id}: {str(e)}"
            ) from e
```

---

## Module 5: Integrating Driver and XML

To expose your custom driver logic to users, export the class module globally and map it
inside your overlay parameters.

### Step 5.1: Global Module Registration
`servod` dynamically loads drivers imported within the primary driver package package.
Append your module to `servo/drv/__init__.py`:

```python
# Inside servo/drv/__init__.py
# ... existing driver imports ...
from servo.drv import codetalker_sequencer
# ...
```

### Step 5.2: Wire Driver Parameters in XML
Update `servo_codetalker_overlay.xml` to reference `drv="codetalker_sequencer"` and
pass down custom attributes (`rail_id`, `max_stages`):

```xml
  <!-- Append to servo_codetalker_overlay.xml -->
  <control>
    <name>codetalker_rail_state</name>
    <doc>Executes step transitions on primary Codetalker power rails.</doc>
    <params cmd="get" interface="servo" drv="codetalker_sequencer"
            rail_id="VDD_CORE" max_stages="4" input_type="str"/>
    <params cmd="set" interface="servo" drv="codetalker_sequencer"
            rail_id="VDD_CORE" max_stages="4" input_type="str"/>
  </control>
```

### Module 5 Verification Instructions
Compile source changes into the execution image and validate full integration from
mapping down to shared driver state modifications:

```bash
./scripts/build-servod
./scripts/start-servod -b codetalker --nomodel

# Verify documentation displays injected custom parameters correctly
dut-control -- --info codetalker_rail_state

# Query base state
dut-control -- codetalker_rail_state
# Expected output: codetalker_rail_state:0

# Drive custom sequencer logic steps
dut-control -- codetalker_rail_state:advance
dut-control -- codetalker_rail_state
# Expected output: codetalker_rail_state:1

dut-control -- codetalker_rail_state:reset
dut-control -- codetalker_rail_state
# Expected output: codetalker_rail_state:0
```

---

## Module 6: Real DUT Bringup (Bare-Metal Console Scraping)

Once basic communication infrastructure is established, you write controls that interact
directly with attached targets over active pseudo-terminals (PTYs). 

> **Physical Target Requirement**: Unlike simulated software controls, executing
interactive commands on live serial endpoints requires a real DUT motherboard and target
debug device securely attached to your host environment.

### Deep Dive: The `simple_ec` Driver Mechanics
The built-in **`simple_ec`** driver (`servo/drv/simple_ec.py`) acts as a highly flexible
console scraping engine. It automatically acquires terminal command locks, flushes
dangling serial line queues, transmits a requested execution string, matches return data
buffers using RE2 regular expressions, extracts targeted sub-groups, and applies
optional formatting filters—all without authoring custom Python code.

To expose functionality via `simple_ec`, you **must** declare specific attributes inside
your `<params>` element. The mandatory parameters depend on the operation
direction (`cmd`):

#### Mandatory Attributes for Read Operations (`cmd="get"`)
- **`uart_cmd`**: The literal string command transmitted down the targeted console line
  (e.g., `"version"`, `"sysinfo"`, `"powerinfo"`).
- **`regex`**: The RE2 regular expression pattern used to locate the output block within
  the console output buffer.
- **`group`**: The zero-indexed capture group integer extracted as the returned state.
  Use `"0"` to output the entire matched regex string block, or `"1"`, `"2"` to return
  target groups `(...)`.

#### Mandatory Attributes for Write Operations (`cmd="set"`)
To perform state updates or assignments over serial console interfaces, declare the
base string instruction using the **`uart_cmd`** parameter. 

##### Translation Walkthrough: From XML Declaration to Physical Line Signaling
Let's examine exactly how `servod` evaluates an assignment string dynamically during
write operations. If we declare a control designed to toggle interactive serial line
configurations:

1. **Declarative Overlay Definition**:
   ```xml
   <control>
     <name>set_interactive_power</name>
     <doc>Triggers dynamic state changes via physical serial command injections.</doc>
     <!-- Note: Declares base command prefix 'power' -->
     <params cmd="set" interface="EC_CONSOLE" drv="simple_ec" uart_cmd="power" input_type="str"/>
   </control>
   ```
2. **Client CLI Invocation**:
   A test developer executes a targeted assignment string from the shell terminal:
   ```bash
   dut-control -- set_interactive_power:on
   ```
3. **Daemon Extraction & Parsing**:
   The central `servod` process intercepts the request, splitting the argument string by
   the assignment delimiter (`:`). It extracts the targeted control name
   (`"set_interactive_power"`) and the raw incoming parameter string (`"on"`).
4. **Parameter Resolution**:
   The system configuration maps the extracted control name to its underlying
   parameters, locating `drv="simple_ec"` and `uart_cmd="power"`.
5. **Driver Payload Generation (`_set`)**:
   `servod` invokes the driver's `set()` method passing down the validated parameter
   string. Internally, the `simple_ec` driver class constructs the complete terminal
   command line by evaluating a formatted string injection:
   ```python
   full_cmd = "%s %s" % (self._uart_cmd, value)
   ```
   Substituting the resolved attributes yields `"%s %s" % ("power", "on")`, producing
   the final literal instruction string: `"power on"`.
6. **Hardware Transport Signaling**:
   The driver acquires local pseudo-terminal command locks, flushes dangling line queue
   characters, transmits `"power on"` down the physical `EC_CONSOLE` pseudo-terminal
   buffer, and monitors standard output return masks (`">"`) to verify successful
   command completion.

#### Advanced Post-Processing Filters (`formatting`)
You can specify comma-separated filtering directives to manipulate raw scraped text
before returning it to the client CLI:
- `"strip"`: Eliminates leading/trailing whitespaces and terminal return characters.
- `"splitlines"`: Splits multi-line serial responses into a structured Python list
  array.
- `"int"`: Safely casts numerical substrings into integer output types.
- `"float"`: Safely casts substrings into floating-point representations.
- `"negative"`: Multiplies signed integer values by `-1` (highly useful for
  standardizing battery discharging vs. charging telemetry polarity).

### Exercise 6.1: Scraping the EC Console Version
**Task**: Expose a user tool that polls the `version` output string natively on the
primary Embedded Controller console.

Append this definition directly to your `servo_codetalker_overlay.xml`:

```xml
  <!-- Append to servo_codetalker_overlay.xml -->
  <control>
    <name>ec_version</name>
    <doc>Retrieves the full firmware release identifier string from the EC console.</doc>
    <!-- Native routing issues 'version' command to EC PTY buffer and extracts matching subgroup -->
    <params cmd="get" interface="EC_CONSOLE" drv="simple_ec" uart_cmd="version"
            regex="RW:\s+(.*)$" group="1" formatting="strip" input_type="str"/>
  </control>
```

#### Understanding Console Interface Routing Keywords
Instead of mapping controls to rigid physical USB endpoint numbers
(like `"1"` or `"2"`), modern `servod` overlays route interactive serial communication
through global, highly resilient logical console aliases. These aliases direct execution
through active software interpreters (EC-3PO interfaces) that manage command
transmission safely without locking up background debug telemetry monitors.

The standard core console interface aliases mapped across the codebase include:
- **`EC_CONSOLE`**: Targets the primary Embedded Controller serial pseudo-terminal line.
  Standard routing endpoint for power state sequencing, thermal sensor polling, and
  matrix key press simulation.
- **`GSC_CONSOLE`** (or `CR50_CONSOLE`): Targets the Google Security Chip interactive
  console bus. Standard routing endpoint for hardware write-protection toggles, physical
  interface capability checks, and Case-Closed Debugging (CCD) status validations.
- **`AP_CONSOLE`** (or `CPU_CONSOLE`): Targets the main Application Processor OS kernel
  or bootloader console bus. Standard routing endpoint for sending early boot
  interruptions or capturing kernel panic stacktraces.
- **`FPMCU_CONSOLE`**: Targets the dedicated Fingerprint Microcontroller serial
  transport layer.
- **`RAW_AP_CONSOLE`**: Directly addresses unbuffered, uninterpreted byte access to the
  AP console logic line.

### Module 6 Verification Instructions
Execute these validation routines with physical debug endpoints attached:

```bash
./scripts/build-servod
./scripts/start-servod -b codetalker --nomodel

# Request execution scraping directly over attached target console hardware
dut-control -- ec_version
# Expected output: ec_version:cros/firmware-codetalker-12345.B-v1.0.0
```

---

## Module 7: Advanced Bare-Metal Custom Drivers (Console Interaction)

When bare-metal operations require runtime evaluation beyond basic regex matching
(e.g., comparing major/minor release numeric substrings against dynamic
target thresholds), you author a custom driver subclassing console-aware interfaces.

### Inheriting Native Console Manipulation Mechanics
By inheriting directly from **`pty_driver.PtyDriver`**, custom classes gain native
access to serial command multiplexers without needing manual locking implementations:
- **`self._issue_cmd_get_results(cmds, regex_list)`**: Transmits raw instruction arrays
down serial channels and blocks until matching console buffers are captured or timeout
bounds expire.

### Exercise 7.1: GSC Firmware Threshold Assertion Logic
**Task**: Develop a driver that executes `version` on the Google Security Chip (GSC)
console, parses numerical substrings, and compares them against a dynamic threshold
attribute provided by the XML configuration.

Create file: `servo/drv/gsc_version_checker.py`.

```python
# Copyright 2026 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Custom serial console driver evaluating GSC firmware threshold updates."""

from servo.common.exceptions import HwDriverError
from servo.drv import pty_driver


# Rule: Class perfectly matches camelCase translation of drv="gsc_version_checker"
class gscVersionChecker(pty_driver.PtyDriver):
    """Queries live GSC console versions and validates floating point boundaries."""

    def _drv_init(self):
        """Constructor hook. Extracts validation parameters from XML."""
        super()._drv_init()
        # Extract floating point numeric boundary threshold
        self._threshold = float(self._params.get("threshold", 1.5))

    def _get(self):
        """Processes read queries ('dut-control -- gsc_version_valid')."""
        # Transmit standard command down interactive security console channel
        # Sample targeted stream: "RW_A: * 1.6.22" or "RW_B: * 0.4.1"
        try:
            results = self._issue_cmd_get_results(
                "version", [r"RW_(?:A|B):\s+\*\s+(\d+)\.(\d+)\.(\d+)"]
            )
        except pty_driver.PtyError as e:
            raise HwDriverError(
                f"GSC serial communication channel unresponsive: {str(e)}"
            ) from e

        # Extract major and minor subgroup elements (skipping index 0 absolute block match)
        major_str = results[0][1]
        minor_str = results[0][2]

        try:
            # Reconstruct string into numerical float representations
            version_float = float(f"{major_str}.{minor_str}")
            self._logger.debug("Evaluated physical GSC release float: %f", version_float)

            # Evaluate dynamic threshold condition logic
            if version_float > self._threshold:
                return "true"
            return "false"
        except (ValueError, TypeError) as e:
            raise HwDriverError(
                f"Failed to parse GSC numerical console output strings: {str(e)}"
            ) from e
```

### Step 7.2: Global Module Linking & XML Wiring
Export the new validation class inside `servo/drv/__init__.py` 

```python
# Inside servo/drv/__init__.py
# ... existing driver imports ...
from servo.drv import gsc_version_checker
# ...
```

Map it targeting the `"GSC_CONSOLE"` interface inside your overlay:

```xml
  <!-- Append to servo_codetalker_overlay.xml -->
  <control>
    <name>gsc_version_valid</name>
    <doc>Status flag asserting if physical GSC version meets target thresholds.</doc>
    <params cmd="get" interface="GSC_CONSOLE" drv="gsc_version_checker"
            threshold="1.5" input_type="str"/>
  </control>
```

### Module 7 Verification Instructions
Compile logic layers and evaluate console-scraped threshold validations:

```bash
./scripts/build-servod
./scripts/start-servod -b codetalker --nomodel

# Retrieve target threshold parameters
dut-control -- --info gsc_version_valid

# Execute automated interactive scrape and numeric assertions
dut-control -- gsc_version_valid
# Expected Output: gsc_version_valid:true
```

---

## Module 8: Validation Workflows & Submission Standards

Prior to pushing commits to Gerrit, execute local validation routines to meet repository
integration standards.

### 1. Run code and style checker
Use `repo` tool to upload your changes and to verify the code style:
```bash
repo upload --cbr .
```

> **Note**: Commits must contain valid `BUG=` and `TEST=` tracking metadata lines.

### 2. Regression Testing Suite
Execute automated containerized unit tests to guarantee core logic stability:
```bash
./scripts/run-servod-tests
```

These tests may fail when ran locally. After uploading commits to gerrit, cloud bot
is automatically running these tests and posting results.

### 3. High-Density Labstation Resilience Checklist
When authoring drivers intended for shared validation labs, implement highly stable
infrastructure patterns:
- **PTY Instantiation Wait Loops**: Use multi-second poll barriers (e.g., check file
  existence every `0.1s` for up to `2s`) when waiting for OS dynamically allocated
  endpoints (`/dev/pts/*`).
- **Block Device Grace Periods**: Provide generous timeout buffers ($\ge 30s$) when
  switching USB image muxes to allow underlying kernel storage drivers to settle on
  `/dev/sdX` nodes.
- **Watchdog Tuning**: Configure internal reconnection attempts generously
  (`REINIT_ATTEMPTS >= 200`) to handle transient USB bus saturation securely without
  causing daemon teardowns.

---

## Final Review Matrix

| Verification Item | Rule Alignment Check | Status |
| :--- | :--- | :--- |
| **Parameters** | Separated double-direction parameters (`cmd="get"` vs `"set"`) explicitly? | [ ] |
| **Driver Naming** | Python class name perfectly matches `snake_to_camel()` translation? | [ ] |
| **Traceback Security**| Trapped runtime faults safely inside `HwDriverError` wrappers? | [ ] |
| **Module Linking** | Appended module reference to `servo/drv/__init__.py` exports? | [ ] |
| **Pre-Submit gates** | Verified passing results on `./scripts/run-servod-tests`? | [ ] |
