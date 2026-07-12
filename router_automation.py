import json
from datetime import datetime
# Netmiko will be imported here later

def load_inventory(filename):
    """Reads the JSON inventory file and returns the data structure."""
    try:
        with open(filename, 'r') as file:
            data = json.load(file)
            return data
    except FileNotFoundError:
        print(f"Error: Could not find {filename}. Ensure it is in the same directory.")
        return None

if __name__ == "__main__":
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Starting EE8203 Automation Script...")
    
    # 1. Load the devices
    inventory = load_inventory("inventory.json")
    
    if inventory:
        print(f"Successfully loaded {len(inventory['routers'])} routers and {len(inventory['switches'])} switches from inventory.")
        # Future code: SSH loop will begin here