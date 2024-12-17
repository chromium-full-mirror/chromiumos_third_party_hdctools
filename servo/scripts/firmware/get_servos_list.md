# Servo Selection Script Guide

This script facilitates querying the `chrome_fleet_analytics.cros_fleet.latest_dut_info` to obtain a list of Device Under Test (DUT) hostnames based on specific filter criteria. The output is generated in a CSV file and should be used as an input to fleet_rollout.py script.

In future we plan to improve options for general servo queries, **for now script is focused on "--stage" logic**

## Prerequisites

* **f1-sql:** This command-line tool is essential for interacting with the database. Ensure it's installed and correctly configured.

## How to Use

1. **Command-Line Arguments**

   The script uses the following command-line arguments:

   * `--servo-type` (required): Specify one or more servo types to filter by.
     * Supported values: `servo_v4`, `servo_v4p1`, `c2d2`, `servo_micro` .

   * `--stage` (required): Choose a predefined stage for DUT selection.
     * `tests`: Selects DUTs from the `servo_verification` pool.
     * `first`: Selects approximately 10% of DUTs from each model in the `DUT_POOL_QUOTA` pool that have `STABLE` firmware and are in the `WORKING` servo stat & `READY` DUT state.
     * `second`: Increases the selection to about 33% of DUTs from `DUT_POOL_QUOTA` and includes 100% DUTs from `faft-test`, `wificell`, and `chameleon_audio` pools with `STABLE` firmware to test more specialized uses of servo.
     * `first-ocd`: Selects approximately 10% of DUTs from each model with servo_micro across all pools (and ~50% of C2D2) and are in the `WORKING` servo stat & `READY` DUT state.
     * `second-ocd`: Increases the selection to about 33% of DUTs with servo_micro across all pools
     * `all-stable`: Selects all DUTs with `STABLE` firmware.
     * `all-alpha`: Selects all DUTs with `ALPHA` firmware.
     * `all-dev`: Selects all DUTs with `DEV` firmware.
     * `manual`: Enables manual filtering using the following optional arguments:

   * `--fw-channel` (optional): Filter by firmware channel(s).
     * Supported values: `STABLE`, `ALPHA`.
     * Only applicable in `manual` stage.

   * `--pool` (optional): Filter by device pool(s).
     * Supported values: `DUT_POOL_QUOTA`, `servo_verification`, `faft-test`,`wificell`, `chameleon_audio`.
     * Only applicable in `manual` stage.

   * `--servo-state` (optional): Filter by servo state(s).
     * Supported values: `WORKING`.
     * Only applicable in `manual` stage.

   * `--dut-state` (optional): Filter by DUT state(s).
     * Supported values: `ready`.
     * Only applicable in `manual` stage.

2. **Running the Script - Example**

   Execute the script from your terminal:

   ```bash
   ./get_servos_list.py --servo-type servo_v4 --stage first
   ```

3. **Output**

    This will generate two CSV files ({stage}_list.csv and {stage}_list_debug.csv) containing a list of servo_v4pX DUTs suitable for the {stage} stage of a rollout.



# Notes
- Review the generated CSV files before proceeding with the update.
- The manual stage/filtering is not yet fully implemented.
- For more advanced usage, refer to the script's source code and comments.


# Disclaimer
- This script is provided as-is and may require modifications to fit your specific use case.
- Always exercise caution when performing firmware updates on production devices.
- Ensure you understand what you are doing and have recovery plan in place.
