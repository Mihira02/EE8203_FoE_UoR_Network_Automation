#!/usr/bin/env python3
"""
get_running_configs.py

Connects to every router/switch in inventory.json, disables paging
(terminal length 0) so `show running-config` returns in full without
"--More--" truncation, and writes ALL configs into ONE single,
clearly-separated, numbered file for easy reading and submission.

Usage (same style as your other scripts):
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
# Same fix as your `cssh` alias
#   ssh -o KexAlgorithms=+diffie-hellman-group14-sha1 -o HostKeyAlgorithms=+ssh-rsa -o Ciphers=+aes128-cbc
# done inside Python instead of the terminal. The Cisco IOS images used in
# GNS3 are old enough that they only offer key-exchange / host-key /
# cipher algorithms that modern OpenSSH and Paramiko disable by default.
# Without this, ConnectHandler() will fail the SSH handshake against every
# device, even though the device and credentials are fine.
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


def get_running_config(device, index, total, output_blocks):
    """SSH to one device, disable paging, pull the full running-config."""
    hostname = device.get("hostname", "unknown")
    ip = device.get("ip")

    header = (
        f"\n{'#' * 78}\n"
        f"# [{index}/{total}] DEVICE: {hostname}   ({ip})\n"
        f"{'#' * 78}\n"
    )

    if not check_tcp_port(ip, port=22, timeout=3):
        msg = f"[SKIPPED] {hostname} ({ip}) - port 22/SSH unreachable. Is GNS3 running and device booted?"
        print(f"    {msg}")
        output_blocks.append(header + msg + "\n")
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

        # Netmiko normally disables paging automatically on connect for
        # cisco_ios, but we set it explicitly too - belt and braces, and
        # matches exactly what you'd type by hand ("terminal length 0")
        # before "show running-config" over a real SSH session.
        connection.send_command("terminal length 0")

        print(f"    [{hostname}] pulling running-config...")
        config = connection.send_command(
            "show running-config",
            read_timeout=60,
        )
        connection.disconnect()

        block = (
            header
            + f"\n{'*' * 78}\n"
            + f"* RUNNING-CONFIG: {hostname}\n"
            + f"{'*' * 78}\n\n"
            + config.strip()
            + "\n"
        )
        output_blocks.append(block)
        print(f"    [OK] {hostname} - running-config captured ({len(config.splitlines())} lines).")
        return "SUCCESS"

    except (NetmikoTimeoutException, NetmikoAuthenticationException) as e:
        msg = f"[FAILED] {hostname} ({ip}) - connection error: {e}"
        print(f"    {msg}")
        output_blocks.append(header + msg + "\n")
        return "FAILED"
    except Exception as e:
        msg = f"[FAILED] {hostname} ({ip}) - unexpected error: {e}"
        print(f"    {msg}")
        output_blocks.append(header + msg + "\n")
        return "FAILED"


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(
        description="Pull full running-config from every device and save to one readable file."
    )
    parser.add_argument("--inventory", default="inventory.json", help="Path to inventory.json (default: inventory.json)")
    parser.add_argument(
        "--output",
        default=None,
        help="Output filename (default: ALL_Running_Configurations_of_Devices_<timestamp>.txt)",
    )
    args = parser.parse_args()

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = args.output or f"ALL_Running_Configurations_of_Devices_{timestamp}.txt"

    inventory = load_inventory(args.inventory)
    all_devices = inventory.get("routers", []) + inventory.get("switches", [])
    total = len(all_devices)

    output_blocks = [
        "ALL RUNNING CONFIGURATIONS OF DEVICES\n"
        f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        f"Total devices in inventory: {total}\n"
    ]

    stats = {"SUCCESS": 0, "FAILED": 0, "SKIPPED": 0}

    print(f"Pulling running-config from {total} devices...\n")

    for i, device in enumerate(all_devices, start=1):
        status = get_running_config(device, i, total, output_blocks)
        stats[status] = stats.get(status, 0) + 1
        time.sleep(1)  # small pause between devices, same spirit as your other scripts

    summary = (
        f"\n{'#' * 78}\n"
        f"# SUMMARY\n"
        f"{'#' * 78}\n"
        f"SUCCESS: {stats['SUCCESS']}   FAILED: {stats['FAILED']}   SKIPPED: {stats['SKIPPED']}\n"
    )
    output_blocks.append(summary)

    with open(output_file, "w") as f:
        f.write("\n".join(output_blocks))

    print(f"\nDone. SUCCESS={stats['SUCCESS']} FAILED={stats['FAILED']} SKIPPED={stats['SKIPPED']}")
    print(f"Full report written to: {output_file}")
    print("This single file has every device's running-config, numbered and separated.")


if __name__ == "__main__":
    main()
