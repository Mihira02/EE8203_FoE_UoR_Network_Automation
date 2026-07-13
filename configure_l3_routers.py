import json
import paramiko
from datetime import datetime
from netmiko import ConnectHandler
from netmiko.exceptions import NetmikoTimeoutException, NetmikoAuthenticationException

# --- THE FULL LEGACY CRYPTO FIX FOR CISCO 7200 ---
paramiko.Transport._preferred_ciphers = (
    'aes128-cbc', '3des-cbc', 'aes192-cbc', 'aes256-cbc'
) + paramiko.Transport._preferred_ciphers

paramiko.Transport._preferred_kex = (
    'diffie-hellman-group1-sha1', 'diffie-hellman-group14-sha1', 'diffie-hellman-group-exchange-sha1'
) + paramiko.Transport._preferred_kex

paramiko.Transport._preferred_pubkeys = (
    'ssh-rsa', 'ssh-dss'
) + paramiko.Transport._preferred_pubkeys
# -------------------------------------------------

def load_inventory(filename):
    try:
        with open(filename, 'r') as file:
            return json.load(file)
    except FileNotFoundError:
        print(f"Error: Could not find {filename}.")
        return None

def push_l3_features(device, log_file):
    """Connects to a router and pushes Layer 3 features with idempotency checks."""
    
    netmiko_device = {
        "device_type": device["device_type"],
        "host": device["ip"],
        "username": device["username"],
        "password": device["password"],
        "global_delay_factor": 2,
        "timeout": 60
    }
    
    print(f" -> Connecting to {device['hostname']} ({device['ip']})...")
    
    try:
        connection = ConnectHandler(**netmiko_device)
        
        # --- R-EDGE CONFIGURATION ---
        if device['hostname'] == "R-EDGE":
            commands = [
                "interface GigabitEthernet1/0",
                "description LINK-TO-NAT-INTERNET",
                "ip address dhcp",
                "ip nat outside",
                "no shutdown",
                "interface GigabitEthernet2/0",
                "description LINK-TO-R-CORE",
                "ip address 10.255.255.6 255.255.255.252",
                "ip nat inside",
                "no shutdown",
                "router ospf 1",
                "network 10.99.99.51 0.0.0.0 area 0",
                "network 10.255.255.4 0.0.0.3 area 0",
                "default-information originate always",
                "ip nat inside source list NAT_ALLOWED interface GigabitEthernet1/0 overload",
                "ip route 0.0.0.0 0.0.0.0 192.168.122.1 254"
            ]
            
            # Idempotency Check: Read existing ACLs
            acl_output = connection.send_command("show ip access-lists")
            
            if "NAT_ALLOWED" not in acl_output:
                commands.extend([
                    "ip access-list standard NAT_ALLOWED",
                    "permit 10.10.10.0 0.0.0.255",
                    "permit 10.10.20.0 0.0.0.255"
                ])
            else:
                print("    [IDEMPOTENT] NAT_ALLOWED ACL already exists. Skipping duplicate.")
                
            if "ACL_MGMT_SSH" not in acl_output:
                commands.extend([
                    "ip access-list extended ACL_MGMT_SSH",
                    "permit tcp 10.99.99.0 0.0.0.255 any eq 22",
                    "deny ip any any",
                    "line vty 0 4",
                    "access-class ACL_MGMT_SSH in"
                ])
            else:
                print("    [IDEMPOTENT] ACL_MGMT_SSH already exists. Skipping duplicate.")

            # Push the compiled list of commands
            connection.send_config_set(commands)

        # --- R-CORE CONFIGURATION ---
        elif device['hostname'] == "R-CORE":
            commands = [
                "interface GigabitEthernet1/0",
                "description LINK-TO-R-EDGE",
                "ip address 10.255.255.5 255.255.255.252",
                "no shutdown",
                "interface GigabitEthernet2/0",
                "description LINK-TO-SW-CORE",
                "ip address 10.255.255.2 255.255.255.252",
                "no shutdown",
                "router ospf 1",
                "network 10.99.99.50 0.0.0.0 area 0",
                "network 10.255.255.0 0.0.0.3 area 0",
                "network 10.255.255.4 0.0.0.3 area 0"
            ]
            
            # Idempotency Check: Read existing ACLs
            acl_output = connection.send_command("show ip access-lists")
            
            if "ACL_MGMT_SSH" not in acl_output:
                commands.extend([
                    "ip access-list extended ACL_MGMT_SSH",
                    "permit tcp 10.99.99.0 0.0.0.255 any eq 22",
                    "deny ip any any",
                    "line vty 0 4",
                    "access-class ACL_MGMT_SSH in"
                ])
            else:
                print("    [IDEMPOTENT] ACL_MGMT_SSH already exists. Skipping duplicate.")

            # Push the compiled list of commands
            connection.send_config_set(commands)

        # Custom Save function to handle NVRAM warning
        output = connection.send_command_timing("write memory")
        if "confirm" in output.lower():
            connection.send_command_timing("\n")
            
        connection.disconnect()
        
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_file.write(f"[{timestamp}] SUCCESS: Layer 3 configured on {device['hostname']}\n")
        print(f"    [OK] Layer 3 configuration saved.")
        
    except (NetmikoTimeoutException, NetmikoAuthenticationException) as e:
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_file.write(f"[{timestamp}] FAILED: {device['hostname']} - Error: {str(e)}\n")
        print(f"    [ERROR] Failed to connect. Logged to file.")

if __name__ == "__main__":
    start_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"[{start_time}] Starting Layer 3 Router Automation...\n")
    
    inventory = load_inventory("inventory.json")
    
    if inventory:
        # Notice we are ONLY loading the routers here, completely ignoring the switches!
        target_routers = inventory['routers']
        
        log_filename = f"l3_automation_log_{datetime.now().strftime('%Y%m%d')}.txt"
        
        with open(log_filename, 'a') as log_file:
            log_file.write(f"\n--- L3 Automation Run: {start_time} ---\n")
            
            for router in target_routers:
                push_l3_features(router, log_file)
                
        print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Script Complete.")