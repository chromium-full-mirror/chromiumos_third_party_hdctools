#!/bin/bash
# Copyright 2025 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
# shellcheck disable=SC2317

# Tests the code in start_servod_dev.sh executes command in the script with the correct
# paramaters and follows the branching logic in the script correctly.

# Run tests locally:
# bash tests/shell/test_start_servod_dev.sh

set -e # Exit immediately if a command exits with a non-zero status.

# Setup
TEST_DIR=$(mktemp -d)
export TEST_DIR
MOCK_BIN_DIR="${TEST_DIR}/bin"
MOCK_SYS_ROOT="${TEST_DIR}/sys_root" # To simulate /sys and /usr/local/genesys
MOCK_SYS_DEVICES_DIR="${MOCK_SYS_ROOT}/sys/bus/usb/devices"
MOCK_FWUPDTOOL_CAB_DIR="${MOCK_SYS_ROOT}/usr/local/genesys"
MOCK_FWUPDTOOL_CAB_FILE="${MOCK_FWUPDTOOL_CAB_DIR}/GenesysLogic_Google_Servo_GL3590_64.18.cab"

mkdir -p "${MOCK_BIN_DIR}"
mkdir -p "${MOCK_SYS_DEVICES_DIR}"
mkdir -p "${MOCK_FWUPDTOOL_CAB_DIR}"
touch "${MOCK_FWUPDTOOL_CAB_FILE}" # Ensure the .cab file path exists for fwupdtool call

# Store original PATH
ORIGINAL_PATH="${PATH}"
export PATH="${MOCK_BIN_DIR}:${PATH}"

# Mock fwupdtool
cat << 'EOF' > "${MOCK_BIN_DIR}/fwupdtool"
#!/bin/bash
echo "fwupdtool_called: $*" >> "${TEST_DIR}/fwupdtool.log"
# Simulate output that gets piped to tr in the original script
echo "Mock fwupdtool update successful???"
EOF
chmod +x "${MOCK_BIN_DIR}/fwupdtool"

# Mock python3
cat << 'EOF' > "${MOCK_BIN_DIR}/python3"
#!/bin/bash
echo "python3_called: $*" >> "${TEST_DIR}/python3.log"
sleep 10
EOF
chmod +x "${MOCK_BIN_DIR}/python3"

# Mock servod
cat << 'EOF' > "${MOCK_BIN_DIR}/servod"
#!/bin/bash
echo "servod_called: $*" >> "${TEST_DIR}/servod.log"
EOF
chmod +x "${MOCK_BIN_DIR}/servod"

# Path to the script under test
TEST_SOURCE_DIR=$(dirname "${0}")
SCRIPT_UNDER_TEST_ORIGINAL="${TEST_SOURCE_DIR}/../../dockerfiles/start_servod_dev.sh"
SCRIPT_UNDER_TEST_COPY="${TEST_DIR}/start_servod_dev_test_copy.sh"

# Helper function to create mock USB device files
create_mock_device() {
    local dev_name="$1"
    local id_vendor="$2"
    local id_product="$3"
    local manufacturer="$4"
    local bcd_device="$5"
    local dev_path="${MOCK_SYS_DEVICES_DIR}/${dev_name}"

    mkdir -p "${dev_path}"
    echo "${id_vendor}" > "${dev_path}/idVendor"
    echo "${id_product}" > "${dev_path}/idProduct"
    echo "${manufacturer}" > "${dev_path}/manufacturer"
    echo "${bcd_device}" > "${dev_path}/bcdDevice"
}

# Teardown function
cleanup() {
    export PATH="${ORIGINAL_PATH}"
    # rm -rf "${TEST_DIR}"
    echo "Cleanup complete."
}
trap cleanup EXIT INT TERM

# Assertion helpers
assert_true() {
    local condition="$1"
    local message="$2"
    if ! eval "$condition"; then
        echo "Assertion FAILED: $message ($condition)"
        exit 1
    fi
    echo "Assertion PASSED: $message"
}

assert_false() {
    local condition="$1"
    local message="$2"
    if eval "$condition"; then
        echo "Assertion FAILED: $message (NOT $condition)"
        exit 1
    fi
    echo "Assertion PASSED: $message"
}

assert_file_contains() {
    local file="$1"
    local pattern="$2"
    local message="$3"
    if ! grep -q -- "${pattern}" "${file}"; then
        echo "Assertion FAILED: $message (File ${file} does not contain '${pattern}')"
        echo "File content:"
        cat "${file}"
        exit 1
    fi
    echo "Assertion PASSED: $message"
}

assert_file_not_exists_or_empty() {
    local file="$1"
    local message="$2"
    if [ -s "${file}" ]; then # -s: file exists and has a size greater than zero
        echo "Assertion FAILED: $message (File ${file} exists and is not empty)"
        echo "File content:"
        cat "${file}"
        exit 1
    fi
    echo "Assertion PASSED: $message"
}

# Prepare the script for testing by modifying hardcoded paths
prepare_script() {
    cp "${SCRIPT_UNDER_TEST_ORIGINAL}" "${SCRIPT_UNDER_TEST_COPY}"
    # Modify path to sysfs
    sed -i "s|/sys/bus/usb/devices|${MOCK_SYS_DEVICES_DIR}|g" "${SCRIPT_UNDER_TEST_COPY}"
    # Modify path to fwupdtool to use the one in PATH (our mock)
    sed -i "s|/usr/bin/fwupdtool|fwupdtool|g" "${SCRIPT_UNDER_TEST_COPY}"
    # Modify path to python3 to use the mock
    sed -i "s|/usr/bin/python3|python3|g" "${SCRIPT_UNDER_TEST_COPY}"
    # Modify path to the .cab file for fwupdtool
    sed -i "s|/usr/local/genesys/GenesysLogic_Google_Servo_GL3590_64.18.cab|${MOCK_FWUPDTOOL_CAB_FILE}|g" "${SCRIPT_UNDER_TEST_COPY}"
}

# Reset mocks and sysfs for each test
reset_mocks_and_sysfs() {
    rm -f "${TEST_DIR}/fwupdtool.log" "${TEST_DIR}/servod.log"
    # Clear previous mock devices
    if [ -d "${MOCK_SYS_DEVICES_DIR}" ]; then
        rm -rf "${MOCK_SYS_DEVICES_DIR:?}/"* # Protect against empty MOCK_SYS_DEVICES_DIR
    fi
    mkdir -p "${MOCK_SYS_DEVICES_DIR}" # Ensure base directory exists
}


# --- Test Cases ---

run_test() {
    local test_name="$1"
    echo "-----------------------------------------------------"
    echo "Running test: ${test_name}"
    reset_mocks_and_sysfs
    # Call the actual test function
    "${test_name}"
    echo "PASSED: ${test_name}"
    echo "-----------------------------------------------------"
}

test_no_updatable_device_empty_sysfs() {
    # MOCK_SYS_DEVICES_DIR is empty by reset_mocks_and_sysfs
    bash "${SCRIPT_UNDER_TEST_COPY}" "arg1 arg2" >/dev/null 2>&1

    assert_file_not_exists_or_empty "${TEST_DIR}/fwupdtool.log" "fwupdtool should not be called"
    assert_true "[ -f \"${TEST_DIR}/servod.log\" ]" "servod should be called"
    assert_file_contains "${TEST_DIR}/servod.log" "servod_called: --host 0.0.0.0 arg1 arg2" "servod called with correct args"
}

test_updatable_device_found() {
    create_mock_device "1-1.1" "05e3" "0610" "Google" "1234" # bcdDevice != 6418
    bash "${SCRIPT_UNDER_TEST_COPY}" "--board=foo --serial=test" >/dev/null 2>&1

    assert_true "[ -f \"${TEST_DIR}/fwupdtool.log\" ]" "fwupdtool should be called"
    assert_file_contains "${TEST_DIR}/fwupdtool.log" "fwupdtool_called: install --plugins genesys --filter=updatable ${MOCK_FWUPDTOOL_CAB_FILE}" "fwupdtool called with correct args"
    assert_true "[ -f \"${TEST_DIR}/servod.log\" ]" "servod should be called"
    assert_file_contains "${TEST_DIR}/servod.log" "servod_called: --host 0.0.0.0 --board=foo --serial=test" "servod called with correct args"
}

test_device_bcd_is_6418_no_update() {
    create_mock_device "2-1" "05e3" "0610" "Google" "6418" # bcdDevice == 6418
    bash "${SCRIPT_UNDER_TEST_COPY}" "arg_only" >/dev/null 2>&1

    assert_file_not_exists_or_empty "${TEST_DIR}/fwupdtool.log" "fwupdtool should not be called (bcdDevice 6418)"
    assert_true "[ -f \"${TEST_DIR}/servod.log\" ]" "servod should be called"
    assert_file_contains "${TEST_DIR}/servod.log" "servod_called: --host 0.0.0.0 arg_only" "servod called with correct args"
}

test_device_vendor_mismatch() {
    create_mock_device "3-1" "0000" "0610" "Google" "1234" # vendor mismatch
    bash "${SCRIPT_UNDER_TEST_COPY}" >/dev/null 2>&1 # No args to servod

    assert_file_not_exists_or_empty "${TEST_DIR}/fwupdtool.log" "fwupdtool should not be called (vendor mismatch)"
    assert_true "[ -f \"${TEST_DIR}/servod.log\" ]" "servod should be called"
    assert_file_contains "${TEST_DIR}/servod.log" "servod_called: --host 0.0.0.0" "servod called with no extra args"
}

test_device_product_mismatch() {
    create_mock_device "1-4" "05e3" "0000" "Google" "1234" # product mismatch
    bash "${SCRIPT_UNDER_TEST_COPY}" >/dev/null 2>&1

    assert_file_not_exists_or_empty "${TEST_DIR}/fwupdtool.log" "fwupdtool should not be called (product mismatch)"
    assert_true "[ -f \"${TEST_DIR}/servod.log\" ]" "servod should be called"
    assert_file_contains "${TEST_DIR}/servod.log" "servod_called: --host 0.0.0.0" "servod called with no extra args"
}

test_device_manufacturer_mismatch() {
    create_mock_device "1-5" "05e3" "0610" "NotGoogle" "1234" # manufacturer mismatch
    bash "${SCRIPT_UNDER_TEST_COPY}" >/dev/null 2>&1

    assert_file_not_exists_or_empty "${TEST_DIR}/fwupdtool.log" "fwupdtool should not be called (manufacturer mismatch)"
    assert_true "[ -f \"${TEST_DIR}/servod.log\" ]" "servod should be called"
    assert_file_contains "${TEST_DIR}/servod.log" "servod_called: --host 0.0.0.0" "servod called with no extra args"
}

test_multiple_devices_one_updatable() {
    create_mock_device "1-4" "0000" "0000" "Nonya" "0000"     # Non-matching
    create_mock_device "2-4" "05e3" "0610" "Google" "abcd"    # Matching
    create_mock_device "3-4" "1111" "1111" "Other" "1111"     # Non-matching
    bash -x "${SCRIPT_UNDER_TEST_COPY}" "argX" >/dev/null 2>&1

    assert_true "[ -f \"${TEST_DIR}/fwupdtool.log\" ]" "fwupdtool should be called (one updatable device)"
    assert_file_contains "${TEST_DIR}/fwupdtool.log" "fwupdtool_called: install --plugins genesys --filter=updatable ${MOCK_FWUPDTOOL_CAB_FILE}" "fwupdtool called with correct args"
    assert_true "[ -f \"${TEST_DIR}/servod.log\" ]" "servod should be called"
    assert_file_contains "${TEST_DIR}/servod.log" "servod_called: --host 0.0.0.0 argX" "servod called with correct args"
}

test_servod_args_parsing() {
    # The script uses IFS=" " read -r -a args <<< "${1}"
    # This means only the first argument to the script is used and then split by spaces.
    bash "${SCRIPT_UNDER_TEST_COPY}" "--board myboard --serial myserial --opt=\"val with space\"" >/dev/null 2>&1

    assert_file_not_exists_or_empty "${TEST_DIR}/fwupdtool.log" "fwupdtool should not be called (no matching device)"
    assert_true "[ -f \"${TEST_DIR}/servod.log\" ]" "servod should be called"
    # Note: The quotes around "val with space" will become part of the argument due to how read processes it from $1
    assert_file_contains "${TEST_DIR}/servod.log" "servod_called: --host 0.0.0.0 --board myboard --serial myserial --opt=\"val with space\"" "servod called with space-separated args from \$1"
}

# Prepare the script copy once
prepare_script

# Run all tests
run_test test_no_updatable_device_empty_sysfs
run_test test_updatable_device_found
run_test test_device_bcd_is_6418_no_update
run_test test_device_vendor_mismatch
run_test test_device_product_mismatch
run_test test_device_manufacturer_mismatch
run_test test_multiple_devices_one_updatable
run_test test_servod_args_parsing

echo ""
echo "All tests passed successfully!"

exit 0
