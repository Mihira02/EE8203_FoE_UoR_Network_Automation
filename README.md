# EE8203 Campus Network Design and Automation Project

An automated network infrastructure deployment for the Faculty of Engineering, University of Ruhuna (FoE UoR). This repository contains Python scripts leveraging **Netmiko** for Layer 3 provisioning and SNMP monitoring, along with **Ansible** playbooks for Layer 2 switching fabric orchestration inside a GNS3 simulation environment.

---

## Network Architecture Overview

The topology follows a hierarchical three-tier enterprise design model:

- **Core Layer:** High-speed routing and switching nodes (`R-CORE`, `SW-CORE`) handling inter-VLAN routing and campus backbone traffic.
- **Distribution Layer:** Modular switches (`SW-D-DEIE`, `SW-D-DCEE`, `SW-D-DMME`) facilitating VLAN aggregation and Spanning-Tree Protocol (STP) root election.
- **Access Layer:** End-user connectivity switches (`SW-A-DEIE`, `SW-A-DCEE`, `SW-A-DMME`, `SW-A-DIS`) providing edge security, VLAN mapping, and host connections.
- **Edge Routing & NAT:** `R-EDGE` provides outbound NAT translation and default routing toward external network interfaces.

---

## Repository Structure

```text
├── configure_l3_routers.py   # Netmiko script for OSPF, NAT Overload, and Management ACLs
├── router_automation.py      # Netmiko script for automated SNMP provisioning across nodes
├── inventory.json            # Target device inventory (hostnames, IP addresses, credentials)
├── hosts.ini                 # Ansible inventory dividing distribution and access switches
├── ansible.cfg               # Ansible connection and SSH timeout configurations
├── site.yml                  # Master Ansible playbook for Layer 2 switching fabric
├── rollback.yml              # Ansible playbook for Layer 2 configuration cleanup/rollback
├── automation_log_*.txt      # Execution logs recording node connection status and timestamps
└── README.md                 # Project documentation
```
