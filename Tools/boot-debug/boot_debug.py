#!/usr/bin/env python3

# This script is AI prompt generated.
# If you would like to create your own logic,
# the prompt utilied by this script is:
# A python script
# 1. Create a systemd service
# 2. Could define the service is using one of command
#    systemctl reboot (named wb) and rtcwake -m off -s 120 (named cb)
# 3. Could define the service to execute command with delay
#    and the default value is 60 seconds
# 4. Could define the max cycle for this service
#    and the default value is 5 times
# 5. Could define the extra script to be executed
#    before executing systemctl reboot or rtcwake -m off -s 120.
#    If not define, echo debug message in the syslog
# 6. While reaching max cycle and the extra script return non-zero,
#    stop and disable this service

import argparse
import os
import subprocess
import sys
import shutil

def run_command(command, check_error=True):
    """
    Helper function to execute shell commands.

    Args:
        command (str): The shell command to execute.
        check_error (bool): If True, raise an error if the command fails.

    Returns:
        bool: True if the command succeeded, False otherwise.
    """
    try:
        process = subprocess.run(command, shell=True, check=check_error, capture_output=True, text=True)
        # Print stdout/stderr only if check_error is True and there's content, or if it failed
        if check_error or process.returncode != 0:
            if process.stdout:
                print(f"Command '{command}' STDOUT:\n{process.stdout.strip()}")
            if process.stderr:
                print(f"Command '{command}' STDERR:\n{process.stderr.strip()}")
        return process.returncode == 0
    except subprocess.CalledProcessError as e:
        print(f"ERROR: Command '{command}' failed with exit code {e.returncode}.")
        if e.stdout:
            print(f"STDOUT: {e.stdout.strip()}")
        if e.stderr:
            print(f"STDERR: {e.stderr.strip()}")
        return False
    except FileNotFoundError:
        print(f"ERROR: Command '{command.split()[0]}' not found. Make sure it's in your system's PATH.")
        return False

def create_service_files(command_alias, delay, max_cycles, extra_script_path):
    """
    Generates the systemd service file and the helper shell script.

    Args:
        command_alias (str): The alias for the main command ('wb' or 'cb').
        delay (int): Delay in seconds before execution.
        max_cycles (int): Maximum number of times the service will run.
        extra_script_path (str): Absolute path to an optional script.

    Returns:
        bool: True if files were created successfully, False otherwise.
    """
    service_name = "reboot-manager.service"
    service_file_path = f"/etc/systemd/system/{service_name}"
    helper_script_path = "/usr/local/bin/reboot_manager.sh"
    counter_dir = "/var/lib/reboot_manager"

    # Map aliases to actual commands
    command_mapping = {
        "wb": "systemctl reboot",
        "cb": "rtcwake -m off -s 120"
    }

    # Validate the chosen command alias and get the actual command
    if command_alias not in command_mapping:
        print(f"ERROR: Invalid command alias '{command_alias}'. Must be one of: {', '.join(command_mapping.keys())}")
        return False
    
    actual_command = command_mapping[command_alias]

    # Validate extra script path if provided
    if extra_script_path:
        if not os.path.isabs(extra_script_path):
            print("ERROR: Extra script path must be an absolute path.")
            return False
        if not os.path.exists(extra_script_path):
            print(f"WARNING: Extra script '{extra_script_path}' does not exist. "
                  "The service will log a warning but proceed without executing it.")

    # --- Systemd Service File Content ---
    service_content = f"""
[Unit]
Description=Automated System Management Service
After=network.target multi-user.target

[Service]
Type=oneshot
ExecStart={helper_script_path}
# Environment variables are passed to the helper script
Environment="REBOOT_MANAGER_COMMAND={actual_command}"
Environment="REBOOT_MANAGER_DELAY={delay}"
Environment="REBOOT_MANAGER_MAX_CYCLES={max_cycles}"
Environment="REBOOT_MANAGER_EXTRA_SCRIPT={extra_script_path if extra_script_path else ''}"
User=root
Group=root
StandardOutput=journal # Redirect script's stdout to systemd journal
StandardError=journal  # Redirect script's stderr to systemd journal

[Install]
WantedBy=multi-user.target
"""

    # --- Helper Shell Script Content ---
    helper_script_content = f"""#!/bin/bash

# --- Configuration (passed via Environment variables from systemd) ---
COMMAND="${{REBOOT_MANAGER_COMMAND}}"
DELAY_SECONDS="${{REBOOT_MANAGER_DELAY}}"
MAX_CYCLES="${{REBOOT_MANAGER_MAX_CYCLES}}"
EXTRA_SCRIPT="${{REBOOT_MANAGER_EXTRA_SCRIPT}}" # Can be empty

# --- Internal Variables ---
SERVICE_NAME="{service_name}"
COUNTER_DIR="{counter_dir}"
COUNTER_FILE="${{COUNTER_DIR}}/cycle_count"
LOG_TAG="reboot_manager_script" # Tag for syslog messages

# --- Functions ---
log_message() {{
    # Send message to syslog via systemd-cat for structured logging
    systemd-cat -t "$LOG_TAG" "$1"
}}

stop_and_disable_service() {{
    log_message "Stopping and disabling ${{SERVICE_NAME}}..."
    # Attempt to stop and disable, ignoring errors if service isn't active
    systemctl stop "$SERVICE_NAME" &> /dev/null || true
    systemctl disable "$SERVICE_NAME" &> /dev/null || true
    rm -f "$COUNTER_FILE" # Clean up the cycle counter file
    log_message "$SERVICE_NAME stopped and disabled. Cycle counter removed."
}}

# --- Main Logic ---

log_message "Service script started."

# Ensure the directory for the cycle counter file exists
mkdir -p "$COUNTER_DIR" || {{ log_message "ERROR: Could not create counter directory ${{COUNTER_DIR}}"; exit 1; }}

# Initialize or read the current cycle count
CURRENT_CYCLE=0
if [ -f "$COUNTER_FILE" ]; then
    CURRENT_CYCLE=$(cat "$COUNTER_FILE")
    # Basic validation: ensure the content is a number
    if ! [[ "$CURRENT_CYCLE" =~ ^[0-9]+$ ]]; then
        log_message "WARNING: Corrupt cycle counter file. Resetting count to 0."
        CURRENT_CYCLE=0
    fi
else
    log_message "Cycle counter file not found. Initializing count to 0."
fi

# Increment the cycle count for the current run and save it
CURRENT_CYCLE=$((CURRENT_CYCLE + 1))
echo "$CURRENT_CYCLE" > "$COUNTER_FILE"

log_message "Current run is cycle ${{CURRENT_CYCLE}} of ${{MAX_CYCLES}}."

# --- Check for Maximum Cycles ---
# If the current cycle count exceeds the maximum, the service has completed its quota
if [ "$CURRENT_CYCLE" -gt "$MAX_CYCLES" ]; then
    log_message "Max cycles (${{MAX_CYCLES}}) exceeded. This service has completed its run quota. Stopping and disabling."
    stop_and_disable_service
    exit 0 # Exit successfully after cleanup
fi

# --- Execute Optional Extra Script ---
if [ -n "$EXTRA_SCRIPT" ]; then
    if [ -f "$EXTRA_SCRIPT" ]; then
        log_message "Executing extra script: ${{EXTRA_SCRIPT}}"
        # Execute the extra script in a subshell to isolate its environment
        ( "$EXTRA_SCRIPT" )
        EXTRA_SCRIPT_EXIT_CODE=$?
        if [ "$EXTRA_SCRIPT_EXIT_CODE" -ne 0 ]; then
            log_message "Extra script '${{EXTRA_SCRIPT}}' returned non-zero exit code (${{EXTRA_SCRIPT_EXIT_CODE}}). Stopping and disabling service as per condition."
            stop_and_disable_service
            exit 0 # Exit successfully after disabling
        else
            log_message "Extra script '${{EXTRA_SCRIPT}}' executed successfully."
        fi
    else
        log_message "WARNING: Extra script path '${{EXTRA_SCRIPT}}' was specified but the file was not found. Proceeding with the main command."
    fi
else
    log_message "No extra script defined. Proceeding with the main command."
fi

# --- Introduce Delay ---
if [ "$DELAY_SECONDS" -gt 0 ]; then
    log_message "Delaying for ${{DELAY_SECONDS}} seconds before executing the main command."
    sleep "$DELAY_SECONDS"
fi

# --- Execute Main Command ---
log_message "Executing main command: ${{COMMAND}}"
# Using 'eval' to correctly handle commands with arguments (e.g., 'rtcwake -m off -s 120')
eval "$COMMAND"

COMMAND_EXIT_CODE=$?
if [ "$COMMAND_EXIT_CODE" -ne 0 ]; then
    log_message "WARNING: Main command '$COMMAND' exited with non-zero status (${{COMMAND_EXIT_CODE}}). The service will attempt to run again on the next boot/wake if it wasn't stopped by the command itself."
else
    log_message "Main command '$COMMAND' executed successfully."
fi

exit 0 # Script finished its current cycle. It will automatically run again on the next system boot or rtcwake event if the command caused one.
"""

    try:
        # Write the systemd service file
        with open(service_file_path, "w") as f:
            f.write(service_content.strip())
        print(f"Created systemd service file: {service_file_path}")

        # Write the helper shell script and make it executable
        with open(helper_script_path, "w") as f:
            f.write(helper_script_content.strip())
        os.chmod(helper_script_path, 0o755) # Set executable permissions (rwxr-xr-x)
        print(f"Created helper script: {helper_script_path} and made it executable.")

        return True
    except IOError as e:
        print(f"ERROR: Could not write files. This script requires root permissions: {e}")
        return False

def manage_service(action, command_alias, delay, max_cycles, extra_script_path):
    """
    Manages the systemd service (create or remove).

    Args:
        action (str): 'create' or 'remove'.
        command_alias (str): The alias for the main command.
        delay (int): Delay in seconds.
        max_cycles (int): Max cycles for the service.
        extra_script_path (str): Path to the extra script.
    """
    service_name = "reboot-manager.service"
    helper_script_path = "/usr/local/bin/reboot_manager.sh"
    counter_dir = "/var/lib/reboot_manager"

    if action == "create":
        print(f"\n--- Setting up {service_name} ---")
        if not create_service_files(command_alias, delay, max_cycles, extra_script_path):
            sys.exit(1) # Exit if file creation failed

        print("Reloading systemd daemon to recognize new service...")
        if not run_command("systemctl daemon-reload"):
            print("ERROR: Failed to reload systemd daemon. Please try 'sudo systemctl daemon-reload' manually.")
            sys.exit(1)

        print(f"Enabling {service_name} to start on boot...")
        if not run_command(f"systemctl enable {service_name}"):
            print(f"ERROR: Failed to enable {service_name}. Please try 'sudo systemctl enable {service_name}' manually.")
            sys.exit(1)

        print(f"Starting {service_name} for the first time...")
        if not run_command(f"systemctl start {service_name}"):
            print(f"ERROR: Failed to start {service_name}. Please try 'sudo systemctl start {service_name}' manually.")
            sys.exit(1)

        print("\nService setup complete!")
        print(f"You can check its status with: 'systemctl status {service_name}'")
        print(f"To view logs: 'journalctl -u {service_name}'")
        print("The service will now execute its command on each system boot/resume, until max cycles or script failure.")

    elif action == "remove":
        print(f"\n--- Removing {service_name} ---")
        print(f"Stopping and disabling {service_name}...")
        # Don't check_error for stop/disable as they might already be stopped/disabled
        run_command(f"systemctl stop {service_name}", check_error=False)
        run_command(f"systemctl disable {service_name}", check_error=False)

        print("Reloading systemd daemon...")
        run_command("systemctl daemon-reload", check_error=False)

        print(f"Removing service files and counter directory...")
        if os.path.exists(f"/etc/systemd/system/{service_name}"):
            os.remove(f"/etc/systemd/system/{service_name}")
            print(f"Removed: /etc/systemd/system/{service_name}")
        if os.path.exists(helper_script_path):
            os.remove(helper_script_path)
            print(f"Removed: {helper_script_path}")
        if os.path.exists(counter_dir):
            # Remove the entire directory and its contents
            shutil.rmtree(counter_dir)
            print(f"Removed counter directory: {counter_dir}")

        print("\nService removed successfully.")
    else:
        print("Invalid action. Use 'create' or 'remove'.")
        sys.exit(1)

def main():
    parser = argparse.ArgumentParser(
        description="""
Create or remove a systemd service for automated system management (reboot/suspend) with cycle control.

This script must be run with 'sudo'.

Usage examples:
  # Create a service to reboot (wb) after 90 seconds, 3 times max:
  sudo python3 script_name.py create --command wb --delay 90 --max-cycles 3

  # Create a service to suspend and wake (cb) for 2 minutes, 5 times max, running an extra script:
  sudo python3 script_name.py create --command cb --extra-script "/path/to/my_pre_script.sh"

  # Remove the service:
  sudo python3 script_name.py remove
        """,
        formatter_class=argparse.RawTextHelpFormatter # Preserves formatting for the description
    )

    parser.add_argument("action", choices=["create", "remove"],
                        help="Action to perform: 'create' the service or 'remove' it.")
    parser.add_argument("--command", choices=["wb", "cb"],
                        help="The main command to execute. Valid options are: "
                             "'wb' (systemctl reboot) or 'cb' (rtcwake -m off -s 120). "
                             "Required for 'create' action.",
                        default="wb") # Default command for convenience
    parser.add_argument("--delay", type=int, default=60,
                        help="Delay in seconds before executing the command. Default: 60.")
    parser.add_argument("--max-cycles", type=int, default=5,
                        help="Maximum number of times the service will run across boots/wakes. "
                             "Once this limit is reached, the service stops and disables itself. Default: 5.")
    parser.add_argument("--extra-script",
                        help="Absolute path to an optional shell script to execute before the main command. "
                             "If this script returns a non-zero exit code, the systemd service will "
                             "immediately stop and disable itself, regardless of the max cycles set. "
                             "If not defined, a debug message is logged instead.")

    args = parser.parse_args()

    # Ensure the script is run as root
    if os.geteuid() != 0:
        print("ERROR: This script must be run as root. Please use 'sudo'.")
        sys.exit(1)

    # Validate --command is provided for 'create' action
    if args.action == "create" and not args.command:
        parser.error("--command is required for the 'create' action.")

    manage_service(args.action, args.command, args.delay, args.max_cycles, args.extra_script)

if __name__ == "__main__":
    main()

