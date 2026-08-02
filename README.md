# EE8203 Campus Network Design and Automation Project
**Faculty of Engineering, University of Ruhuna (FoE UoR)**

An enterprise-grade, automated network infrastructure deployment built and validated within a GNS3 simulation environment. This project demonstrates a complete lifecycle implementation: from initial manual Layer 2/3 baseline provisioning and extended ACL security policy enforcement to automated Layer 2 switching fabric orchestration via Ansible and Netmiko Python scripting.

---

## Network Architecture Overview

The topology adheres to a hierarchical three-tier enterprise network design model:

* **Core Layer (`SW-CORE`, `R-CORE`):** High-speed routing and switching backbone handling inter-VLAN routing, dynamic OSPF Area 0 routing, and central access security enforcement.
* **Distribution Layer (`SW-D-DEIE`, `SW-D-DCEE`, `SW-D-DMME`):** Aggregation switches facilitating VLAN trunking, STP root bridge topology control, and department-level traffic isolation.
* **Access Layer (`SW-A-DEIE`, `SW-A-DCEE`, `SW-A-DMME`, `SW-A-DIS`):** Edge switches providing host port mapping, VLAN assignment, and out-of-band management access.
* **Edge & Security Zone (`R-EDGE`):** Provides Internet egress via NAT Overload (PAT) restricted strictly to authorized departments (DEIE & DCEE) and enforces default route distribution.
* **Management & Automation Zone (`Ubuntu_Automation`):** Dedicated Linux node residing on Management VLAN 99 (`10.99.99.0/24`) configured for automated SSH management across all network nodes.

---

## VLAN & Addressing Table

| VLAN ID | Name | Department / Purpose | Subnet | Permitted Egress |
| :---: | :---: | :---: | :---: | :---: |
| **10** | `VLAN_DEIE` | Engineering Workstations | `10.10.10.0/24` | Server Farm, Internet |
| **20** | `VLAN_DCEE` | Civil / Environmental Hosts | `10.10.20.0/24` | Server Farm (HTTP/HTTPS only), Internet |
| **30** | `VLAN_DMME` | Mechanical / Workshop Hosts | `10.10.30.0/24` | Fully Isolated (Local Only) |
| **40** | `VLAN_DIS` | Server Farm / IT Hub | `10.10.40.0/24` | DEIE Internal, Internal Server Egress |
| **99** | `MGMT` | Out-of-Band SSH Management | `10.99.99.0/24` | All Network Device SVIs |
| **100** | `NATIVE` | Trunk Link Native Traffic | N/A | Untagged Frame Isolation |

---

## 4x4 Inter-Department Reachability Matrix

Cross-department security policies enforced via Extended Named ACLs (`ACL_DEIE_IN`, `ACL_DCEE_IN`, `ACL_DMME_IN`) on `SW-CORE` and NAT policies on `R-EDGE`:

| Source Zone | DEIE (`10.10.10.x`) | DCEE (`10.10.20.x`) | DMME (`10.10.30.x`) | DIS Server (`10.10.40.x`) | Internet (`8.8.8.8`) |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **DEIE (`PC1`/`PC2`)** | **PASS** | **FAIL** (Denied) | **FAIL** (Denied) | **PASS** | **PASS** |
| **DCEE (`PC3`/`PC4`)** | **FAIL** (Denied) | **PASS** | **FAIL** (Denied) | **FAIL** (ICMP Blocked; TCP 80/443 Permitted) | **PASS** |
| **DMME (`PC5`/`PC6`)** | **FAIL** (Denied) | **FAIL** (Denied) | **PASS** | **FAIL** (Denied) | **FAIL** (Denied) |
| **DIS Server (`PC7`/`PC8`)** | **PASS** | **FAIL** (Blocked) | **FAIL** (Blocked) | **PASS** | **FAIL** (No NAT) |

---

## Repository Structure

```text
EE8203_FoE_UoR_Network_Automation/
├── ansible/                        # Ansible Automation Framework
│   ├── group_vars/                 # Global & Group Variable Definitions
│   ├── host_vars/                  # Host-specific Switch Parameters
│   └── roles/                      # Modular Ansible Roles
│       ├── access_ports/           # Edge switch access port assignments
│       │   └── tasks/
│       ├── stp/                    # Spanning-Tree Protocol configuration
│       │   └── tasks/
│       ├── trunking/               # 802.1Q Dot1q trunking & Native VLAN setup
│       │   └── tasks/
│       └── vlans/                  # VLAN Database creation tasks
│           └── tasks/
├── images/                         # Screenshot evidence for testing & report
│   ├── pc1_deie_pings.png
│   ├── pc3_dcee_pings.png
│   ├── pc5_dmme_pings.png
│   ├── pc7_dis_pings.png
│   └── topology_diagram.png
└── Manual Configurations/          # Baseline Network Code & Logs
    ├── Codes/                      # CLI Manual Command Snippets
    │   ├── Access Layer/           # Access switch configurations
    │   ├── Distribution Layer/     # Distribution switch configurations
    │   └── Routing/                # SW-CORE, R-CORE, & R-EDGE configurations
    └── Results/                    # Raw CLI outputs, ping logs & verification