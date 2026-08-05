#!/usr/bin/env python3
"""
get_running_configs.py

Connects to every router/switch in inventory.json, disables paging
(terminal length 0) so `show running-config` returns in full without
"--More--" truncation, and writes each device's configuration into a
separate text file uniquely named for that device.

Usage:
    python3 get_running_configs.py --inventory inventory.json

Requires the same environment your router_automation.py /
verify_project.py scripts already run in (netmiko + paramiko
installed). No new packages needed.
"""

import argparse
import json
import socket
import time
from datetime import datetime

import paramiko
from netmiko import ConnectHandler
from netmiko.exceptions import NetmikoTimeoutException, NetmikoAuthenticationException


# ---------------------------------------------------------------------------
# Legacy crypto compatibility patch
# ---------------------------------------------------------------------------
paramiko.Transport._preferred_kex = (
    "diffie-hellman-group14-sha1",
    "diffie-hellman-group-exchange-sha1",
) + paramiko.Transport._preferred_kex

paramiko.Transport._preferred_keys = (
    "ssh-rsa",
) + paramiko.Transport._preferred_keys

paramiko.Transport._preferred_ciphers = (
    "aes128-cbc",
    "aes192-cbc",
    "aes256-cbc",
) + paramiko.Transport._preferred_ciphers


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def check_tcp_port(ip, port=22, timeout=3):
    """Quick raw TCP check before attempting a full SSH handshake."""
    try:
        with socket.create_connection((ip, port), timeout=timeout):
            return True
    except (socket.timeout, ConnectionRefusedError, OSError):
        return False


def load_inventory(path):
    with open(path, "r") as f:
        return json.load(f)


def get_running_config(device, index, total, timestamp):
    """SSH to one device, disable paging, pull the full running-config, and save to its own file."""
    hostname = device.get("hostname", "unknown")
    ip = device.get("ip")

    if not check_tcp_port(ip, port=22, timeout=3):
        print(f"    [{index}/{total}] [SKIPPED] {hostname} ({ip}) - port 22/SSH unreachable. Is GNS3 running and device booted?")
        return "SKIPPED"

    netmiko_device = {
        "device_type": device.get("device_type", "cisco_ios"),
        "host": ip,
        "username": device["username"],
        "password": device["password"],
        "global_delay_factor": 2,
        "timeout": 30,
        "session_log": f"{hostname}_debug.txt",
    }

    try:
        connection = ConnectHandler(**netmiko_device)
        connection.send_command("terminal length 0")

        print(f"    [{index}/{total}] [{hostname}] pulling running-config...")
        config = connection.send_command(
            "show running-config",
            read_timeout=60,
        )
        connection.disconnect()

        # Generate a unique filename for this specific device
        filename = f"{hostname}_running_config_{timestamp}.txt"
        
        # Write the output directly to the new file
        with open(filename, "w") as f:
            f.write(config.strip() + "\n")

        print(f"    [OK] {hostname} - config saved to {filename} ({len(config.splitlines())} lines).")
        return "SUCCESS"

    except (NetmikoTimeoutException, NetmikoAuthenticationException) as e:
        print(f"    [{index}/{total}] [FAILED] {hostname} ({ip}) - connection error: {e}")
        return "FAILED"
    except Exception as e:
        print(f"    [{index}/{total}] [FAILED] {hostname} ({ip}) - unexpected error: {e}")
        return "FAILED"


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(
        description="Pull full running-config from every device and save to separate files."
    )
    parser.add_argument("--inventory", default="inventory.json", help="Path to inventory.json (default: inventory.json)")
    args = parser.parse_args()

    # Generate one timestamp at the start to keep filenames consistent across the whole run
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    inventory = load_inventory(args.inventory)
    all_devices = inventory.get("routers", []) + inventory.get("switches", [])
    total = len(all_devices)

    stats = {"SUCCESS": 0, "FAILED": 0, "SKIPPED": 0}

    print(f"Pulling running-configs from {total} devices and saving to separate files...\n")

    for i, device in enumerate(all_devices, start=1):
        status = get_running_config(device, i, total, timestamp)
        stats[status] = stats.get(status, 0) + 1
        time.sleep(1)  # small pause between devices

    # Print final summary to the console
    print(f"\n{'#' * 50}")
    print(f"# SUMMARY")
    print(f"{'#' * 50}")
    print(f"SUCCESS: {stats['SUCCESS']}   FAILED: {stats['FAILED']}   SKIPPED: {stats['SKIPPED']}")
    print(f"Complete! Check the current directory for the new configuration files.")


if __name__ == "__main__":
    main()