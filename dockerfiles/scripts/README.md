# Servo XML Configuration Pre-processing Tools

This directory contains a suite of tools for processing, analyzing, and flattening the Servo XML configuration files located in the `servo/data/` directory. These tools are extremely useful for both manual inspection and automated validation of configuration changes.

## Available Tools

### 1. `preprocess_xml.py`

This tool resolves `<include>` directives and processes `<map>` and `<control>` attributes (including the complex `clobber_ok` resolution logic) within an XML configuration file. It produces a single, "flattened" output file that represents the final state of the configuration as `servod` sees it.

**Usage:**
```bash
python3 servo/dockerfiles/scripts/preprocess_xml.py <input_file> <output_file>
```

**Example:**
```bash
python3 servo/dockerfiles/scripts/preprocess_xml.py servo/data/servo_micro.xml flattened_servo_micro.xml
```

### 2. `analyze_xml_impact.py`

This tool identifies changes made to the XML files (e.g., in a git commit) and evaluates their downstream impact across the entire configuration hierarchy. It evaluates the before and after states of the flattened XML files and generates HTML visual diffs. This is heavily used in CI checks to ensure XML modifications don't unintentionally break derived configurations.

**Usage:**
```bash
python3 servo/dockerfiles/scripts/analyze_xml_impact.py [--commit COMMIT] [--output_dir DIR] [--output_report FILE]
```

**Example:**
```bash
# Analyze impact of changes in the current branch relative to HEAD
python3 servo/dockerfiles/scripts/analyze_xml_impact.py --commit HEAD --output_dir ./html_diffs --output_report report.md
```

## Running the Tools Locally

All of these tools can be run manually in your local checkout of the repository. Make sure you invoke them using `python3` from the root of the `hdctools` repository to ensure the Python paths resolve correctly.

```bash
# Navigate to the hdctools root directory
cd ~/chromiumos/src/third_party/hdctools

# Run the tools as needed
python3 servo/dockerfiles/scripts/preprocess_xml.py servo/data/servo_micro.xml flattened_servo_micro.xml
```

## Extracting Live XML Configs via `servod`

If you are running `servod` and wish to dump the exact parsed configuration (matching the output of the preprocessor logic but generated live), you can start `servod` with the `--dump-xml` argument:

```bash
sudo servod -b hatch -m kohaku --dump-xml /tmp/servod_dump.xml
```

If multiple devices are managed by `servod` (e.g., a main servo and a root device), it will create multiple files prefixed by the device type (like `/tmp/servod_dump_main.xml`).
