import json
import paramiko
from datetime import datetime
from netmiko import ConnectHandler
from netmiko.exceptions import NetmikoTimeoutException, NetmikoAuthenticationException

# --- THE FULL LEGACY CRYPTO FIX FOR CISCO 7200 ---
# 1. Force legacy Ciphers
paramiko.Transport._preferred_ciphers = (
    'aes128-cbc', '3des-cbc', 'aes192-cbc', 'aes256-cbc'
) + paramiko.Transport._preferred_ciphers

# 2. Force legacy Key Exchanges (KEX)
paramiko.Transport._preferred_kex = (
    'diffie-hellman-group1-sha1', 'diffie-hellman-group14-sha1', 'diffie-hellman-group-exchange-sha1'
) + paramiko.Transport._preferred_kex

# 3. Force legacy Public Keys
paramiko.Transport._preferred_pubkeys = (
    'ssh-rsa', 'ssh-dss'
) + paramiko.Transport._preferred_pubkeys
# -------------------------------------------------


def load_inventory(filename):
    """Reads the JSON inventory file and returns the data structure."""
    try:
        with open(filename, 'r') as file:
            return json.load(file)
    except FileNotFoundError:
        print(f"Error: Could not find {filename}.")
        return None

def push_snmp(device, log_file):
    """Connects to a single device and configures SNMP."""
    
    # Map our JSON keys to the keys Netmiko expects
    netmiko_device = {
        "device_type": device["device_type"],
        "host": device["ip"],
        "username": device["username"],
        "password": device["password"],
        "global_delay_factor": 2,  # Tells Python to double the wait time
        "timeout": 60,             # Gives the router 60 seconds to finish the SSH math
        "session_log": f"{device['hostname']}_debug.txt"  # Creates an x-ray text file
    }
    
    # The Cisco commands we want to push
    # Note: Assuming Zabbix will be placed on VLAN 40 (10.10.40.50)
    snmp_commands = [
        "snmp-server community UOR_SNMP RO",
        "snmp-server host 10.10.40.50 version 2c UOR_SNMP",
        "snmp-server enable traps"
    ]
    
    print(f" -> Connecting to {device['hostname']} ({device['ip']})...")
    
    try:
        # Establish SSH Connection
        connection = ConnectHandler(**netmiko_device)
        
        # Push the commands
        connection.send_config_set(snmp_commands)
        
        # Save the configuration and handle the GNS3 NVRAM warning
        output = connection.send_command_timing("write memory")
        if "confirm" in output.lower():
            connection.send_command_timing("\n")
        
        # Disconnect cleanly
        connection.disconnect()
        
        # Log success
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_file.write(f"[{timestamp}] SUCCESS: SNMP configured on {device['hostname']}\n")
        print(f"    [OK] Configured and saved.")
        
    except (NetmikoTimeoutException, NetmikoAuthenticationException) as e:
        # If the device is off or password is wrong, catch the error so the script doesn't crash!
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_file.write(f"[{timestamp}] FAILED: {device['hostname']} - Error: {str(e)}\n")
        print(f"    [ERROR] Failed to connect. Logged to file.")


if __name__ == "__main__":
    start_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"[{start_time}] Starting EE8203 Automation Script...\n")
    
    inventory = load_inventory("inventory.json")
    
    if inventory:
        # Combine routers and switches into one big list
        all_devices = inventory['routers'] + inventory['switches']
        
        # Create/Open our timestamped log file
        log_filename = f"automation_log_{datetime.now().strftime('%Y%m%d')}.txt"
        
        with open(log_filename, 'a') as log_file:
            log_file.write(f"\n--- Automation Run: {start_time} ---\n")
            
            # Loop through every device and run the SNMP function
            for device in all_devices:
                push_snmp(device, log_file)
                
        print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Script Complete. Check {log_filename} for details.")