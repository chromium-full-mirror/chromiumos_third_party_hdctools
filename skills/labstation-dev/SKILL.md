---
name: labstation-dev
description: Use this skill for developing, building, flashing, and debugging servod and labstation components on ChromeOS. It provides workflows for multi-process architecture, concurrency locks, upstart services, and USB stability issues, as well as instructions on filing bugs via the CLI.
---

# Labstation Development and Debugging

This skill provides procedural knowledge for working with labstations, `servod`, and their underlying architecture.

## 1. Building and Flashing

### Building the Test Image
To build the labstation test image (e.g., `fizz-labstation`), use the standard `cros` build commands. Agents can write their own wrapper script to automate these steps if desired.
```bash
./chromite/bin/setup_board --board=fizz-labstation
./chromite/bin/cros build-packages --board=fizz-labstation --accept-licenses=@CHROMEOS
./chromite/bin/cros build-image --board=fizz-labstation test
```

### Flashing the Image
Once the build completes, the test image is located in the `src/build/images/<board>/<version>/` directory. Flash it to the DUT using:
```bash
cros flash ${DUT_IP} src/build/images/fizz-labstation/latest/chromiumos_test_image.bin
```
**Note:** The device must be accessible over the network, and you cannot flash a base image in this mode (use a test or dev image).

## 2. Servod Architecture and Upstart

Labstations run `servod` using a multi-process architecture where the main `servod` process acts as a router that spawns `servod_core` and `servod_data` sub-processes. This architectural split is complete and on the main branch. When debugging issues, it can be useful to compare behavior against the `hdctools_legacy_main` branch to see if a regression was introduced by the multi-process split, but otherwise this architecture is the standard.

*   **Location:** Upstart scripts are located in `src/platform/labstation/os-dependent/chromeos/upstart-scripts`.
*   **Argument Propagation:** When modifying the main `servod.conf` to add new flags (e.g., `REC_MODE`), ensure that the arguments are explicitly passed down to `servod_core` and `servod_data`. If they are not passed, the sub-processes will fall back to cached config files and drop transient arguments.
*   **Upstart Dependencies:** Both core and data jobs declare `instance $PORT`. Upstart uses subset matching for events, so extra parameters on the `start` command do not sever the `stop on stopping servod_core PORT=$PORT` dependency.

## 3. Concurrency and Locks

When handling multiple concurrent deployments (e.g., Swarming tasks), you must prevent initialization storms.

*   **Execution Wrappers:** Scripts like `labstation_ready_for_deploy` use `flock` to acquire a slot. The script *must* be an execution wrapper (running the deployment command as a child process while holding the file descriptor open). Simply acquiring the lock and exiting `0` is an ephemeral lock and provides no protection.

## 4. Hardware Quirks and Edge Cases

*   **USB Stability Quirks:** Be careful when globally disabling USB LPM (Link Power Management) via kernel command-line quirks (e.g., `usbcore.quirks=05e3:0625:k` in `build_kernel_image.sh`). While it may stabilize some hubs (Genesys S2), it can prevent downstream devices from correctly enumerating their sysfs attributes (like `serial`), causing `HierarchyError` during `servod` initialization.
*   **Recovery Mode and Empty Interfaces:** In recovery mode or when dealing with bare servos, some UART interfaces (like GSC/Cr50) instantiate as `Empty` stubs. These stubs do not implement methods like `set_capture_active`. Always use `hasattr` checks (or explicitly raise handled exceptions like `ptyDriverError`) before toggling capture to prevent `AttributeError` crashes in `pty_driver.py`.
*   **Fatal Error Logging:** Ensure that any unhandled exceptions during early startup (e.g., in `ServodStarter`) are caught with a broad `Exception` handler and logged using the `logging` module. Otherwise, they bypass `latest.DEBUG` and dump directly to `sys.stderr`, disappearing from standard log collections.

## 5. Filing Bugs

To file bugs from the command line, use the Go-based Issues CLI (do not use `bugged`):

```bash
/google/bin/releases/issues-cli/issues create \
  --title "Your concise bug title here" \
  --description "Detailed description of the issue, steps to reproduce, and links to CLs." \
  --component_id <id> \
  --assignee "username@google.com" \
  --priority P2 \
  --severity S2 \
  --type BUG
```
*Tip:* You can use `issues help` or `issues helpfull` for a list of subcommands.
