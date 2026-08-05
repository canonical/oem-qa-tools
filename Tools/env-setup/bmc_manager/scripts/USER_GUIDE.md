# BMC Manager User Guide

## Overview

BMC Manager is a Python script that provides a unified interface for managing
Baseboard Management Controllers (BMC) using two protocols:

- **IPMI** (via ipmitool)
- **Redfish** (via REST API)

This tool allows you to list users, discover available power actions, and
execute power management commands on remote servers.

## Requirements

### System Requirements

- Python 3.10 or higher
- Linux/Unix system (for IPMI support)
- `uv` package manager (recommended) or `pip`

### Dependencies

### Python Packages

Install required Python packages using `uv`:

```bash
cd bmc_manager/scripts
uv sync
```

Or using `pip`:

```bash
pip install requests urllib3
```

### External Tools (for IPMI)

For IPMI protocol support, you need `ipmitool` installed:

```bash
# Ubuntu/Debian
sudo apt-get install ipmitool

# RHEL/CentOS
sudo yum install ipmitool

# macOS
brew install ipmitool
```

## Installation

1. Ensure Python 3.10+ is installed:

   ```bash
   python3 --version
   ```

2. Install Python dependencies using `uv`:

   ```bash
   cd bmc_manager/scripts
   uv sync
   ```

   Or using `pip`:

   ```bash
   pip install requests urllib3
   ```

3. Install ipmitool (if using IPMI protocol):

   ```bash
   # See dependencies section above for your OS
   ```

4. Make the script executable (optional):

   ```bash
   chmod +x bmc_manager/scripts/bmc_manager.py
   ```

## Usage

### Basic Syntax

Using `uv`:

```bash
cd bmc_manager/scripts
uv run python bmc_manager.py <IP> <USER> <PASSWORD> <PROTOCOL> [OPTIONS]
```

Or directly with Python:

```bash
python3 bmc_manager/scripts/bmc_manager.py <IP> <USER> <PASSWORD> <PROTOCOL> [OPTIONS]
```

### Arguments

- `IP`: BMC IP address (required)
- `USER`: BMC username (required)
- `PASSWORD`: BMC password (required)
- `PROTOCOL`: Protocol to use - either `redfish` or `ipmitool` (required)

### Options (choose one)

- `--list-users`: List all users configured on the BMC
- `--list-actions`: List available power/reset actions
- `--power-state`: Get current chassis power state
- `--action <ACTION>`: Execute a power action

## Examples

### List Users

Using Redfish:

```bash
cd bmc_manager/scripts
uv run python bmc_manager.py 192.168.1.100 admin password redfish --list-users
```

Using IPMI:

```bash
cd bmc_manager/scripts
uv run python bmc_manager.py 192.168.1.100 admin password ipmitool --list-users
```

Output Example:

```output
[Redfish] Validating connection to 192.168.1.100...
[+] Connection Verified (Redfish)

--- Redfish User List ---
ID         Name                 Role            Enabled
------------------------------------------------------------
1          admin                Administrator   True
2          operator             Operator        True
3          readonly             ReadOnly        False
```

### List Available Actions

Using Redfish:

```bash
cd bmc_manager/scripts
uv run python bmc_manager.py 192.168.1.100 admin password redfish --list-actions
```

Using IPMI:

```bash
cd bmc_manager/scripts
uv run python bmc_manager.py 192.168.1.100 admin password ipmitool --list-actions
```

Output Example (Redfish):

```output
[Redfish] Validating connection to 192.168.1.100...
[+] Connection Verified (Redfish)

--- Redfish Actions for /Systems/System.Embedded.1 ---
Action Endpoint: #ComputerSystem.Reset
Target: /redfish/v1/Systems/System.Embedded.1/Actions/ComputerSystem.Reset
Supported Commands:
  - On
  - ForceOff
  - GracefulRestart
  - GracefulShutdown
  - PowerCycle
```

Output Example (IPMI):

```output
[IPMI] Validating connection to 192.168.1.100...
[+] Connection Verified (IPMI v2.0)

--- IPMI Supported Actions (Standard) ---
IPMI actions are standardized. Available commands via this script:
 - status
 - on
 - off
 - cycle
 - reset
 - soft (graceful shutdown)
```

### Check Power State

Get the current chassis power state. Redfish returns values such as `On`,
`Off`, `PoweringOn`, `PoweringOff`, or `Paused`. IPMI returns `on` or `off`.

Using Redfish:

```bash
cd bmc_manager/scripts
uv run python bmc_manager.py 192.168.1.100 admin password redfish --power-state
```

Using IPMI:

```bash
cd bmc_manager/scripts
uv run python bmc_manager.py 192.168.1.100 admin password ipmitool --power-state
```

Output Example (Redfish, with `--json`):

```json
{
  "success": true,
  "power_state": "On"
}
```

Output Example (IPMI, with `--txt`):

```output
[IPMI] Chassis power status
Chassis Power is on
```

Use `--txt` for plain-text output only, or `--json` (default) for JSON only.

### Execute Power Actions

### Power On

```bash
cd bmc_manager/scripts
uv run python bmc_manager.py 192.168.1.100 admin password redfish --action on
```

### Power Off

```bash
cd bmc_manager/scripts
uv run python bmc_manager.py 192.168.1.100 admin password redfish --action off
```

### Power Cycle

```bash
cd bmc_manager/scripts
uv run python bmc_manager.py 192.168.1.100 admin password redfish --action cycle
```

### Graceful Shutdown (Soft)

```bash
cd bmc_manager/scripts
uv run python bmc_manager.py 192.168.1.100 admin password redfish --action soft
```

### Reset

```bash
cd bmc_manager/scripts
uv run python bmc_manager.py 192.168.1.100 admin password redfish --action reset
```

### Check Power Status (IPMI chassis status)

You can also use `--action status` (IPMI) for chassis status, or use
`--power-state` for a dedicated power-state check (see Check Power State
above). Example with IPMI action:

```bash
cd bmc_manager/scripts
uv run python bmc_manager.py 192.168.1.100 admin password ipmitool --action status
```

Output Example:

```output
[IPMI] Validating connection to 192.168.1.100...
[+] Connection Verified (IPMI v2.0)

[IPMI] Executing Action: status
[+] Success: System Power         : on
```

## Protocol Differences

### IPMI (ipmitool)

Advantages:

- Standardized commands across all BMCs
- Works on older hardware
- Lightweight protocol (UDP)

Limitations:

- Requires ipmitool to be installed
- Limited to standard IPMI commands
- Uses UDP port 623

Supported Actions:

- `status`: Chassis status (or use `--power-state` for power state only)
- `on`: Power on
- `off`: Power off (hard)
- `cycle`: Power cycle
- `reset`: Reset
- `soft`: Graceful shutdown

### Redfish

Advantages:

- Modern REST API
- More detailed information
- Vendor-specific actions supported
- Uses HTTPS (port 443)

Limitations:

- Requires HTTPS support
- May have vendor-specific implementations
- Some older BMCs may not support it

Supported Actions:

- Actions are discovered dynamically from the BMC
- Common actions include: `On`, `ForceOff`, `GracefulShutdown`,
  `GracefulRestart`, `PowerCycle`, etc.
- The script maps generic aliases (`on`, `off`, `reset`, `soft`, `cycle`)
  to vendor-specific commands automatically

## Troubleshooting

### Connection Issues

### "Connection Timeout" (IPMI)

- Verify the BMC IP address is correct
- Check if UDP port 623 is accessible:

  ```bash
  nc -u -v <BMC_IP> 623
  ```

- Ensure firewall allows UDP port 623
- Try changing the cipher suite (modify code if needed)

### "Connection Timeout" (Redfish)

- Verify the BMC IP address is correct
- Check if HTTPS port 443 is accessible:

  ```bash
  curl -k https://<BMC_IP>/redfish/v1
  ```

- Ensure firewall allows TCP port 443

### "Connection Error"

- Verify network connectivity to BMC
- Check if BMC is powered on and accessible
- Verify IP address is correct

### Authentication Issues

### "Authentication Failed: Invalid Username or Password"

- Double-check username and password
- Ensure credentials are correct for the BMC
- Some BMCs are case-sensitive

### "Authentication Failed: HTTP 401/403 Unauthorized" (Redfish)

- Verify credentials are correct
- Check if user account is enabled
- Ensure user has appropriate permissions

### Protocol-Specific Issues

### IPMI: "Protocol Error: Cipher Suite mismatch"

- The default cipher suite is 17
- Some older BMCs may require a different cipher suite
- You may need to modify the code to change the cipher suite value

### IPMI: "ipmitool is not installed"

- Install ipmitool (see Requirements section)
- Ensure ipmitool is in your PATH

### Redfish: "No Systems found in Redfish collection"

- The BMC may not expose systems via Redfish
- Try using IPMI protocol instead
- Verify Redfish service is enabled on the BMC

### Redfish: "No power actions discovered"

- The BMC may not support power actions via Redfish
- Try using IPMI protocol instead
- Check BMC firmware version (may need update)

### Action Execution Issues

### "Action not supported by this system"

- Use `--list-actions` to see available actions
- Try using the exact action name from the list
- Some actions may require specific permissions

### "Command Accepted" but nothing happens

- Some actions take time to execute
- Check BMC logs for errors
- Verify user has sufficient permissions

## Security Notes

1. **Credentials**: Never hardcode credentials in scripts
2. **SSL Warnings**: The script disables SSL verification for self-signed
   certificates. In production, consider proper certificate validation
3. **Network**: Ensure BMC network is properly secured
4. **Permissions**: Use least-privilege accounts when possible

## Advanced Usage

### Using with Scripts

You can integrate BMC Manager into shell scripts:

```bash
#!/bin/bash
BMC_IP="192.168.1.100"
BMC_USER="admin"
BMC_PASS="password"
SCRIPT_DIR="bmc_manager/scripts"

# Check if server is on
STATUS=$(cd $SCRIPT_DIR && uv run python bmc_manager.py $BMC_IP \
    $BMC_USER $BMC_PASS ipmitool --action status 2>&1 | grep -i "on")

if [ -z "$STATUS" ]; then
    echo "Server is off, powering on..."
    cd $SCRIPT_DIR && uv run python bmc_manager.py $BMC_IP \
        $BMC_USER $BMC_PASS ipmitool --action on
fi
```

### Environment Variables

For better security, you can use environment variables:

```bash
export BMC_IP="192.168.1.100"
export BMC_USER="admin"
export BMC_PASS="password"

cd bmc_manager/scripts
uv run python bmc_manager.py $BMC_IP $BMC_USER $BMC_PASS redfish --list-users
```

## Support

For issues or questions:

1. Check the troubleshooting section above
2. Verify your BMC firmware version supports the protocol
3. Test with both IPMI and Redfish to isolate protocol-specific issues
4. Review BMC logs for detailed error messages

## Code Formatting

This project uses Black formatting with a line length of 79 characters:

```bash
cd bmc_manager/scripts
uv run black --line-length 79 bmc_manager.py
```

## Version Compatibility

- **Python**: 3.10+
- **IPMI**: IPMI 2.0 compatible BMCs
- **Redfish**: Redfish 1.0+ compatible BMCs
