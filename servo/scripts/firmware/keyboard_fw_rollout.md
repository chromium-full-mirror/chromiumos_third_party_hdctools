# Keyboard Firmware Rollout Script Documentation

This script facilitates the flashing of keyboard firmware (`.hex` file) onto multiple ChromeOS setups (Keyboard emulator is part of servo but need to be flashed from DUT) in a fleet environment. **It is designed for use by specialized users who will manually review the results and address potential edge cases.** Process demands usage of DUT as a programmer, which of course introduces some limits, problems, risks. This process is not intended to be fully automatic, as some setups may require manual firmware updates or solutions to specific issues.

## Prerequisites

*   **gcert:** Ensure you have a valid `gcert` certificate before running the script. This is required for SSH access to lab resources.
*   **Passwordless SSH:** You must have passwordless SSH configured for the `root` user on all target DUTs and labstations. This means you need to have a working `~/.ssh/config` file and the `testing_rsa` (and potentially `partner_testing_rsa`) private key. See "SSH Configuration" below.
*   **Input CSV:** A CSV file containing the DUT, servo serial, labstation, and servod port information. See "CSV Input File" below.
*   **Keyboard Hex File:** The path to the `.hex` file containing the keyboard firmware.
*   **Available DUTs:** DUTs must be in a state where they can be accessed via SSH. DUTs with `needs_manual_repair` or similar states will likely fail.
* **Available Labstations (able to start servod ):** Labstation needs be accessible via ssh and allow to normally start servod for given setup

## How to Use

1.  **Prepare the Input CSV:**
    *   Use a PLX query (similar to the one provided) to generate a list of DUTs, servos, labstations and ports.
    *   Export the results to a CSV file.

    ```
        SELECT
          -- the here are some extra columns to make potential edge cases debug easier
          hostname as dut,
          servo_serial,
          servo_hostname as labstation,
          board,
          model,
          servo_type_raw,
          servo_port,
          servo_state,
          state,
        FROM
          chrome_fleet_analytics.cros_fleet.latest_dut_info
        WHERE
          -- use needed filters
          servo_type_raw LIKE "servo\\_v4\\_%"
    ```
2.  **Prepare the Keyboard Hex File:**
    *   Make sure you have the `.hex` file containing the keyboard firmware.
3.  **Run the Script:**
    ```bash
    python3 fleet_keyboard_fw_rollout_genai.py <path_to_csv> <path_to_keyboard_hex>
    ```
    *   Replace `<path_to_csv>` with the path to your CSV file.
    *   Replace `<path_to_keyboard_hex>` with the path to your `.hex` file.
4.  **Monitor the Output:**
    *   The script will print real-time progress to the console.
    *   Detailed per-DUT logs will be saved to a file named `keyboard_rollout_<timestamp>.log`.
        * Please carefully analyze, especially cases where script could not update devices
    * CSV files with successful and failed DUTs will be created.
        * You can reuse CSV with failed devices to  re-try after some time, e.g. it can help in various cases where DUT or labstations were not available for a moment
        * Keep the record of successful attempts, especially the servo FW, as we do not have any other way to verify which FW version specific servo has

## CSV Input File

The CSV file should have the following columns:

*   `dut`: The hostname of the DUT.
*   `servo_serial`: The serial number of the servo attached to the DUT.
*   `labstation`: The hostname of the labstation managing the servo.
*   `servo_port`: The port number on the labstation where the servo is connected.

Example CSV:

```csv
dut,servo_serial,labstation,servo_port
chromeos1-row1-rack1-host1,SERVOV4P1-S-XXXXXXXXX,chromeos1-row1-labstation1,9999
chromeos2-row2-rack2-host2,SERVOV4P1-S-YYYYYYYYY,chromeos2-row2-labstation2,9998
```

## SSH Configuration

You must configure passwordless SSH access to ChromeOS devices. This involves setting up your ~/.ssh/config file and using SSH keys.

See [Setup ssh to access lab DUTs](https://g3doc.corp.google.com/company/teams/chrome/ops/fleet/systems/access_lab_duts.md?cl=head) for more details.


## Important Notes

* Satlab DUTs: This script does not support Satlab devices. These must be handled manually.
* DUT Availability: The script requires DUTs to be available for the process. DUTs in a "needs_manual_repair" state (or similar) will likely cause failures.
* Logging: The script provides detailed logging to both the console and a log file.
* Parallel Processing: The script uses multithreading to process devices in parallel, speeding up the overall process. The number of workers can be configured in the script (NUM_WORKERS). Please use carefully.
* Other configurable Constants: The script has several constants that you might want to adjust depending on your environment or specific needs. These include:
   * SSH_PORT: The SSH port to use (default is 22).
   * CONNECT_TIMEOUT: The timeout for SSH connection attempts (in seconds).
   * COMMAND_TIMEOUT: The timeout for individual SSH command executions (in seconds).
   * SSH_USERNAME: The username to use for SSH connections (default is "root").
   * _BASE_LOG_FILE_NAME_FOR_UNIQUENESS: Base name of the log file.
* Timeouts: Be aware that timeouts for SSH connections and commands are configurable, and you may need to adjust them based on the speed of your network and the responsiveness of your devices.
* PLX Query: You can use similar query like provided to create input csv file. You can also use CLI like f1-sql.
* Script log: Script creates log file with details of all operations, which should be used to decide what to do with remaining devices
