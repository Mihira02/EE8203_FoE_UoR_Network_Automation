import argparse
import json
import paramiko
import socket
import time
from datetime import datetime
from functools import wraps
from netmiko import ConnectHandler
from netmiko.exceptions import NetmikoTimeoutException, NetmikoAuthenticationException

# --- LEGACY SSH ENCRYPTION COMPATIBILITY FOR CISCO 7200 & vIOS ---
paramiko.Transport._preferred_ciphers = (
    'aes128-cbc', '3des-cbc', 'aes192-cbc', 'aes256-cbc'
) + paramiko.Transport._preferred_ciphers

paramiko.Transport._preferred_kex = (
    'diffie-hellman-group1-sha1', 'diffie-hellman-group14-sha1', 'diffie-hellman-group-exchange-sha1'
) + paramiko.Transport._preferred_kex

paramiko.Transport._preferred_pubkeys = (
    'ssh-rsa', 'ssh-dss'
) + paramiko.Transport._preferred_pubkeys
# -----------------------------------------------------------------


def retry_on_failure(max_retries=2, delay=3):
    """Decorator to retry SSH connections with exponential backoff."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            attempts = 0
            while attempts <= max_retries:
                try:
                    return func(*args, **kwargs)
                except (NetmikoTimeoutException, NetmikoAuthenticationException) as e:
                    attempts += 1
                    if attempts > max_retries:
                        raise e
                    print(f"    [RETRY {attempts}/{max_retries}] Connection failed, retrying in {delay}s...")
                    time.sleep(delay)
        return wrapper
    return decorator


def check_tcp_port(ip, port=22, timeout=3):
    """Pre-flight check to verify if the SSH port is open before attempting Netmiko connection."""
    try:
        with socket.create_connection((ip, port), timeout=timeout):
            return True
    except (socket.timeout, OSError):
        return False


def load_inventory(filename):
    """Reads and parses the JSON inventory file."""
    try:
        with open(filename, 'r') as file:
            return json.load(file)
    except FileNotFoundError:
        print(f"[ERROR] Could not locate inventory file: {filename}")
        return None
    except json.JSONDecodeError as e:
        print(f"[ERROR] Invalid JSON syntax in {filename}: {e}")
        return None


@retry_on_failure(max_retries=2, delay=3)
def execute_ssh_payload(netmiko_device, commands):
    """Handles the active SSH session, command delivery, and configuration save."""
    connection = ConnectHandler(**netmiko_device)
    connection.send_config_set(commands)
    
    # Save running configuration to NVRAM and handle GNS3 confirm prompt
    output = connection.send_command_timing("write memory")
    if "confirm" in output.lower():
        connection.send_command_timing("\n")
        
    connection.disconnect()


def push_snmp(device, log_file):
    """Configures SNMP community strings and trap destinations on a Cisco node."""
    ip = device["ip"]
    hostname = device["hostname"]
    
    # Fast pre-flight reachability check
    if not check_tcp_port(ip, port=22, timeout=3):
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_file.write(f"[{timestamp}] SKIPPED: {hostname} ({ip}) - Port 22/SSH closed or unreachable\n")
        print(f"    [SKIP] Port 22 unreachable on {hostname} ({ip}). Skipping SSH connection.")
        return "SKIPPED"

    netmiko_device = {
        "device_type": device["device_type"],
        "host": ip,
        "username": device["username"],
        "password": device["password"],
        "global_delay_factor": 2,
        "timeout": 30,
        "session_log": f"{hostname}_debug.txt"
    }
    
    # SNMP payload targeting Zabbix Monitoring Server (10.99.99.102 on VLAN 99)
    snmp_commands = [
        "no snmp-server host 10.10.40.50 version 2c UOR_SNMP",
        "snmp-server community UOR_SNMP RO",
        "snmp-server host 10.99.99.102 version 2c UOR_SNMP",
        "snmp-server enable traps"
    ]
    
    print(f" -> Connecting to {hostname} ({ip})...")
    
    try:
        execute_ssh_payload(netmiko_device, snmp_commands)
        
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_file.write(f"[{timestamp}] SUCCESS: SNMP configured on {hostname}\n")
        print(f"    [OK] SNMP configuration pushed and saved to {hostname}.")
        return "SUCCESS"

    except (NetmikoTimeoutException, NetmikoAuthenticationException) as e:
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_file.write(f"[{timestamp}] FAILED: {hostname} - Auth/Timeout Error: {str(e)}\n")
        print(f"    [ERROR] Connection or authentication failed for {hostname}.")
        return "FAILED"
    except Exception as e:
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_file.write(f"[{timestamp}] CRITICAL: {hostname} - Unexpected Error: {str(e)}\n")
        print(f"    [CRITICAL] Unexpected execution error on {hostname}.")
        return "FAILED"


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Automated Cisco SNMP Provisioning Tool")
    parser.add_argument("-i", "--inventory", default="inventory.json", help="Path to inventory JSON file")
    args = parser.parse_args()

    start_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"[{start_time}] Initiating Network Automation Sequence...\n")
    
    inventory = load_inventory(args.inventory)
    
    if inventory:
        all_devices = inventory.get('routers', []) + inventory.get('switches', [])
        log_filename = f"automation_log_{datetime.now().strftime('%Y%m%d')}.txt"
        
        stats = {"SUCCESS": 0, "FAILED": 0, "SKIPPED": 0}
        
        with open(log_filename, 'a') as log_file:
            log_file.write(f"\n--- Automation Run: {start_time} ---\n")
            
            for device in all_devices:
                status = push_snmp(device, log_file)
                stats[status] = stats.get(status, 0) + 1

        print("\n" + "=" * 45)
        print("          EXECUTION SUMMARY REPORT           ")
        print("=" * 45)
        print(f" Total Nodes Target     : {len(all_devices)}")
        print(f" Successful Configs     : {stats['SUCCESS']}")
        print(f" Skipped (Unreachable) : {stats['SKIPPED']}")
        print(f" Failed Connections     : {stats['FAILED']}")
        print("=" * 45)
        print(f"Detailed logs saved to: {log_filename}")