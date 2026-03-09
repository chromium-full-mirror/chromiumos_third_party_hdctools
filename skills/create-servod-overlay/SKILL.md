---
name: create-servod-overlay
description: "Use this skill to autonomously create a new servod XML overlay for a new ChromeOS board or model and stage it in a Gerrit commit. This handles prompting the user via an interactive form for required hardware properties (board, model, EC chip, base includes), generating the XML structure correctly, and committing it."
---

# create-servod-overlay

This skill guides you through generating a new XML overlay for `servod`. 

**CRITICAL KNOWLEDGE:** Users often mistakenly believe they need to hardcode `c2d2` or `servo_micro` into their board overlays. **They do not.** Servod dynamically discovers and loads `c2d2.xml` or `servo_micro` config based on the physical USB hardware detected at runtime. The board overlay should ONLY define the board's internal routing, EC chip, and keyboard matrix.

## 1. Gather Requirements (Interactive Prompt)
First, ensure you know the **Board Name** and **Model Name**. If you don't know them, ask the user in standard conversation.

**CRITICAL INHERITANCE RULE:** 
*   If the user is creating a **Base Board Overlay** (Model is blank): The Architecture include should be `x86_ec_common.xml`, `arm_ec_common.xml`, or `<board>_common.xml`.
*   If the user is creating a **Model Specific Overlay** (Model is provided): The Architecture include **MUST** be `servo_<board>_overlay.xml`. A model overlay inherits from its parent board overlay and only overrides specific facets (like keyboard matrix or a different EC chip). Do not include `cr50.xml` or `x86_ec_common.xml` again if the parent board already includes them.

If you are creating a **Model Specific Overlay**, you should skip the `ask_user` questions for Architecture and GSC entirely, automatically inheriting them from the base board, and only ask the user about the EC Chip and Keyboard overrides.

If creating a **Base Board Overlay**, use the `ask_user` tool to present this structured form:
```json
{
  "questions": [
    {
      "question": "What is the base CPU architecture include for this board?",
      "header": "Architecture",
      "type": "choice",
      "multiSelect": true,
      "options": [
        {"label": "x86_ec_common.xml", "description": "Generic x86 EC definitions"},
        {"label": "arm_ec_common.xml", "description": "Generic ARM EC definitions"},
        {"label": "servo_<board>_overlay.xml", "description": "Inherit directly from the base board overlay (for models)"},
        {"label": "<board>_common.xml", "description": "Inherit from a shared board common file"}
      ]
    },
    {
      "question": "Which Google Security Chip (GSC) does this device use?",
      "header": "GSC",
      "type": "choice",
      "multiSelect": false,
      "options": [
        {"label": "None", "description": "No GSC or inherited from base"},
        {"label": "cr50.xml", "description": "CR50 Security Chip"},
        {"label": "ti50.xml", "description": "TI50 / Dauntless Security Chip"}
      ]
    },
    {
      "question": "What EC (Embedded Controller) chip does this device use?",
      "header": "EC Chip",
      "type": "choice",
      "multiSelect": false,
      "options": [
        {"label": "None", "description": "Inherit from the included base XML"},
        {"label": "npcx_uut", "description": "Nuvoton EC (Most Common)"},
        {"label": "it8xxx2", "description": "ITE 8xxx2 series"},
        {"label": "stm32", "description": "STMicroelectronics 32-bit"}
      ]
    },
    {
      "question": "Does this model require a specific Keyboard Matrix override?",
      "header": "Keyboard",
      "type": "choice",
      "multiSelect": false,
      "options": [
        {"label": "None", "description": "Inherit default keyboard handler"},
        {"label": "ChromeMatrix30", "description": "Standard 30-pin Chrome Keyboard Matrix"},
        {"label": "usb", "description": "USB Keyboard handler"}
      ]
    }
  ]
}
```

## 2. Generate the XML File
Create the file at `src/third_party/hdctools/servo/data/servo_<board>_<model>_overlay.xml` (omit `_<model>` if it's a base board).

*   Replace `<board>` in the includes with the actual board name.
*   Add `<include>` blocks for the selected Architecture and GSC (if not "None").
*   If `EC Chip` is not "None", add the `<control>` block for `ec_chip`.
*   If `Keyboard` is not "None", add the `<control>` block for `init_keyboard`.

**Template Structure:**
```xml
<root>
  <!-- Add the selected includes here -->
  <include>
    <name>YOUR_SELECTED_ARCH_INCLUDE.xml</name>
  </include>
  <include>
    <name>YOUR_SELECTED_GSC_INCLUDE.xml</name>
  </include>

  <!-- Optional EC Chip Override -->
  <control>
    <name>ec_chip</name>
    <doc>EC chip name (read-only)</doc>
    <params clobber_ok="" cmd="get" subtype="chip" interface="servo" drv="cros_chip" chip="SELECTED_EC_CHIP"/>
  </control>

  <!-- Optional Keyboard Override -->
  <control>
    <name>init_keyboard</name>
    <doc>initialize keyboard handler</doc>
    <params map="onoff" init="on" drv="kb_handler_init" interface="servo" subtype="init_default_keyboard" handler_type="SELECTED_KEYBOARD" clobber_ok="full"/>
  </control>
</root>
```

## 3. Verify the Build
Run the pre-commit checks:
```bash
gpkg pre-commit run --files src/third_party/hdctools/servo/data/servo_<board>_<model>_overlay.xml
```

## 4. Create the Commit
Stage the newly created file and create a git commit:
```bash
cd src/third_party/hdctools
git add servo/data/servo_<board>_<model>_overlay.xml
git commit -m "servo: data: Add <board>/<model> overlay

Adds the initial servod XML overlay for the <model> device
based on the <board> family.

BUG=b:<Ask user for Bug number, or None>
TEST=sudo servod -b <board> -m <model>"
```
