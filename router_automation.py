import json
import paramiko
from datetime import datetime
from netmiko import ConnectHandler
from netmiko.exceptions import NetmikoTimeoutException, NetmikoAuthenticationException

# --- THE FULL LEGACY CRYPTO FIX FOR CISCO 7200 & vIOS ---
# Force legacy Ciphers to ensure compatibility with GNS3 Cisco nodes
paramiko.Transport._preferred_ciphers = (
    'aes128-cbc', '3des-cbc', 'aes192-cbc', 'aes256-cbc'
) + paramiko.Transport._preferred_ciphers

# Force legacy Key Exchanges (KEX) for legacy IOS handshakes
paramiko.Transport._preferred_kex = (
    'diffie-hellman-group1-sha1', 'diffie-hellman-group14-sha1', 'diffie-hellman-group-exchange-sha1'
) + paramiko.Transport._preferred_kex

# Force legacy Public Key algorithms
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
        print(f"Error: Could not find inventory file: {filename}")
        return None

def push_snmp(device, log_file):
    """Connects to a single device and configures SNMP monitoring settings."""
    
    # Connection parameters mapped from JSON inventory settings
    netmiko_device = {
        "device_type": device["device_type"],
        "host": device["ip"],
        "username": device["username"],
        "password": device["password"],
        "global_delay_factor": 2,  # Multiplier for command delay timing in virtual environments
        "timeout": 60,             # Maximum wait time in seconds for SSH session establishment
        "session_log": f"{device['hostname']}_debug.txt"  # Generates detailed connection log per node
    }
    
    # Cisco IOS SNMP Configuration Commands
    # Zabbix Server Target IP: 10.10.40.50 (VLAN 40)
    snmp_commands = [
        "snmp-server community UOR_SNMP RO",
        "snmp-server host 10.10.40.50 version 2c UOR_SNMP",
        "snmp-server enable traps"
    ]
    
    print(f" -> Connecting to {device['hostname']} ({device['ip']})...")
    
    try:
        # Establish active SSH connection
        connection = ConnectHandler(**netmiko_device)
        
        # Apply SNMP configuration payload
        connection.send_config_set(snmp_commands)
        
        # Persist running configuration to NVRAM and handle GNS3 write confirm prompts
        output = connection.send_command_timing("write memory")
        if "confirm" in output.lower():
            connection.send_command_timing("\n")
        
        # Close SSH session gracefully
        connection.disconnect()
        
        # Record successful operation
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_file.write(f"[{timestamp}] SUCCESS: SNMP configured on {device['hostname']}\n")
        print(f"    [OK] SNMP configuration applied and saved successfully.")
        
    except (NetmikoTimeoutException, NetmikoAuthenticationException) as e:
        # Handle unreachable hosts or invalid credentials without stopping execution
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_file.write(f"[{timestamp}] FAILED: {device['hostname']} - Error: {str(e)}\n")
        print(f"    [ERROR] Connection failed for {device['hostname']}. Recorded to log.")
    except Exception as e:
        # Catch unexpected socket/network errors
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_file.write(f"[{timestamp}] UNEXPECTED ERROR: {device['hostname']} - {str(e)}\n")
        print(f"    [CRITICAL] Unexpected error encountered on {device['hostname']}.")


if __name__ == "__main__":
    start_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"[{start_time}] Starting EE8203 SNMP Automation Tasks...\n")
    
    inventory = load_inventory("inventory.json")
    
    if inventory:
        # Aggregate all network nodes (Routers and Switches) for sequential execution
        all_devices = inventory['routers'] + inventory['switches']
        
        # Open execution log file with append mode
        log_filename = f"automation_log_{datetime.now().strftime('%Y%m%d')}.txt"
        
        with open(log_filename, 'a') as log_file:
            log_file.write(f"\n--- SNMP Automation Execution Run: {start_time} ---\n")
            
            # Iterate through the complete inventory array
            for device in all_devices:
                push_snmp(device, log_file)
                
        print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Task Complete. Results appended to {log_filename}")