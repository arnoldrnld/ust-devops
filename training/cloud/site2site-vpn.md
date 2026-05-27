# AWS Site-to-Site VPN Lab: Complete Implementation Guide

## Connecting Two VPCs Across Regions Using StrongSwan as a Simulated On-Premises Router

---

## Table of Contents

1. [What Are We Building?](#what-are-we-building)
2. [Why Are We Doing This?](#why-are-we-doing-this)
3. [Architecture Overview](#architecture-overview)
4. [Prerequisites](#prerequisites)
5. [Part 1: Build the Cloud VPC in Mumbai](#part-1-build-the-cloud-vpc-in-mumbai)
6. [Part 2: Build the On-Premises VPC in Virginia](#part-2-build-the-on-premises-vpc-in-virginia)
7. [Part 3: Set Up the StrongSwan VPN Router](#part-3-set-up-the-strongswan-vpn-router)
8. [Part 4: Create the AWS VPN Infrastructure](#part-4-create-the-aws-vpn-infrastructure)
9. [Part 5: Configure StrongSwan on the Router EC2](#part-5-configure-strongswan-on-the-router-ec2)
10. [Part 6: Configure VTI Interface](#part-6-configure-vti-interface)
11. [Part 7: Fix the Routing](#part-7-fix-the-routing)
12. [Part 8: Launch Private EC2 Instances](#part-8-launch-private-ec2-instances)
13. [Part 9: Test the Connection](#part-9-test-the-connection)
14. [Troubleshooting Guide](#troubleshooting-guide)
15. [How Traffic Actually Flows](#how-traffic-actually-flows)
16. [Key Concepts Summary](#key-concepts-summary)

---

## What Are We Building?

We are building a **Site-to-Site VPN connection** between two AWS VPCs that live in completely different AWS regions.

```
Mumbai Region (ap-south-1)          Virginia Region (us-east-1)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━        ━━━━━━━━━━━━━━━━━━━━━━━━━━━
                                    
  cloud-vpc                           onprem-vpc
  10.0.0.0/16                         10.1.0.0/16
                                    
  ┌─────────────┐                     ┌─────────────────────┐
  │ cloud-server│                     │   onprem-server     │
  │ 10.0.x.x    │                     │   10.1.x.x          │
  │ (Private EC2│                     │   (Private EC2)     │
  └──────┬──────┘                     └──────────┬──────────┘
         │                                        │
         │                                        │
  ┌──────▼──────┐                     ┌──────────▼──────────┐
  │    VGW      │◄────IPSec VPN──────►│   StrongSwan Router │
  │  (AWS side) │    Public Internet  │   (vpn-router EC2)  │
  └─────────────┘                     └─────────────────────┘
```

**Goal:** Ping from `cloud-server` (Mumbai, private IP) to `onprem-server` (Virginia, private IP) and back — through an encrypted IPSec tunnel over the public internet.

---

## Why Are We Doing This?

Before touching a single AWS console, you need to understand **why** each piece exists.

### Why Two Different Regions?

In the real world, your company's physical datacenter is NOT inside AWS. It is sitting in some building, connected to the internet through a router. That router has a **public IP address**.

By placing our "on-premises" VPC in Virginia and our "cloud" VPC in Mumbai, we simulate this reality:

- There is **real internet distance** between them
- There is **real latency** between them
- Traffic must cross the **public internet** between them
- We need **encryption** because the internet is untrusted

If we used the same region, we could just use VPC peering — which is simple and completely different from what enterprises actually do for hybrid cloud.

### Why IPSec VPN?

Your on-premises datacenter has sensitive data. You cannot send it unencrypted over the internet. IPSec creates an **encrypted tunnel** — a private highway through the public internet. Everything inside that tunnel is encrypted and cannot be read by anyone in the middle.

### Why StrongSwan?

Real enterprises use physical hardware routers — Cisco ASA, Palo Alto, Fortigate. These cost thousands of dollars. StrongSwan is **open-source VPN software** that implements the exact same IPSec standards. We install it on a cheap EC2 instance and it behaves exactly like enterprise hardware from AWS's perspective.

### Why Does the Private EC2 Need a Router?

Your private EC2 (`onprem-server`) has a private IP like `10.1.2.x`. It has **no idea** how to reach `10.0.0.0/16` (Mumbai). It just knows its local network. The StrongSwan router knows how to:

1. Receive packets from `onprem-server`
2. Encrypt them
3. Send them through the IPSec tunnel to AWS
4. Receive encrypted replies from AWS
5. Decrypt them
6. Forward replies back to `onprem-server`

The private instance never knows any of this is happening. It just sends packets to its default gateway.

---

## Architecture Overview

```
                         PUBLIC INTERNET
                               │
           ┌───────────────────┼───────────────────┐
           │                   │                   │
           ▼                   │                   ▼
   ┌───────────────┐     IPSec Tunnel      ┌───────────────────┐
   │  AWS VGW      │◄════════════════════► │  StrongSwan EC2   │
   │  (Mumbai)     │    Encrypted Traffic  │  (Virginia)       │
   │               │                       │  Elastic IP       │
   └───────┬───────┘                       └────────┬──────────┘
           │                                        │
           │ VGW routes                             │ EC2 routes
           │ 10.1.0.0/16 → VGW                     │ 10.0.0.0/16 → vpn-router
           │                                        │
           ▼                                        ▼
   ┌───────────────┐                       ┌────────────────────┐
   │ cloud-server  │                       │  onprem-server     │
   │ Private EC2   │                       │  Private EC2       │
   │ 10.0.x.x      │                       │  10.1.x.x          │
   └───────────────┘                       └────────────────────┘

   Mumbai Region                           Virginia Region
   cloud-vpc: 10.0.0.0/16                 onprem-vpc: 10.1.0.0/16
```

### Component Explanation

| Component | What It Is | Why It Exists |
|---|---|---|
| **cloud-vpc** | AWS VPC in Mumbai | Represents your AWS cloud environment |
| **onprem-vpc** | AWS VPC in Virginia | Simulates your physical datacenter |
| **cloud-server** | Private EC2 in Mumbai | Simulates a cloud application server |
| **onprem-server** | Private EC2 in Virginia | Simulates an on-premises application server |
| **VGW** | Virtual Private Gateway | AWS's side of the VPN — it terminates the IPSec tunnel |
| **vpn-router** | EC2 + StrongSwan in Virginia | Simulates the on-premises router/firewall |
| **Elastic IP** | Static public IP for vpn-router | VPN endpoints must have permanent IPs |
| **Customer Gateway** | AWS object representing vpn-router | Tells AWS where the on-premises router is |

---

## Prerequisites

- AWS account with permissions to create VPCs, EC2, and VPN resources
- Basic Linux command line knowledge
- SSH client on your local machine
- Understanding that you will work in **two different regions** and must switch between them

> **Critical habit:** Always check which region you are in before creating anything. The top-right corner of AWS console shows the active region. One wrong click and you create resources in the wrong place.

---

## Part 1: Build the Cloud VPC in Mumbai

**Region: ap-south-1 (Mumbai)**

### Why Mumbai First?

We build the cloud side first because the VPN will be **anchored on the cloud side** using the Virtual Private Gateway (VGW). We need the VGW's details before we can finish setting up StrongSwan on the other side.

### Step 1.1 — Switch to Mumbai Region

Click the region dropdown in the top-right corner of the AWS console.

Select:
```
Asia Pacific (Mumbai) ap-south-1
```

### Step 1.2 — Create the Cloud VPC

**Why:** A VPC is your isolated private network inside AWS. Think of it as your own private section of the AWS datacenter where your servers will live.

Navigate to:
```
VPC → Your VPCs → Create VPC
```

Select **"VPC only"** (not VPC and more — we will create subnets manually so you understand each piece):

| Setting | Value | Why |
|---|---|---|
| Name tag | `cloud-vpc` | Identifies this as the cloud side |
| IPv4 CIDR | `10.0.0.0/16` | Gives us 65,536 private IP addresses |
| IPv6 | No | Not needed for this lab |
| Tenancy | Default | Shared hardware is fine |

Click **Create VPC**.

> **Why `10.0.0.0/16`?** We chose this range because it does not overlap with our on-premises VPC (`10.1.0.0/16`). Overlapping CIDRs would break routing — a router cannot decide if `10.0.1.5` is local or remote if both networks share the same range.

### Step 1.3 — Create Subnets

**Why two subnets?** We need a public subnet for resources that need internet access and a private subnet for servers that should only be reachable through the VPN. Our `cloud-server` will live in the private subnet — exactly like a real production server that has no direct internet exposure.

Navigate to:
```
VPC → Subnets → Create subnet
```

**Select `cloud-vpc` as the VPC first.**

Create the **public subnet**:

| Setting | Value | Why |
|---|---|---|
| Subnet name | `cloud-public-subnet` | Labels this as publicly accessible |
| Availability Zone | `ap-south-1a` | Pin to a specific AZ |
| IPv4 CIDR | `10.0.1.0/24` | 256 IPs for public resources |

Create the **private subnet**:

| Setting | Value | Why |
|---|---|---|
| Subnet name | `cloud-private-subnet` | Labels this as private |
| Availability Zone | `ap-south-1b` | Different AZ for diversity |
| IPv4 CIDR | `10.0.2.0/24` | 256 IPs for private servers |

> You can create both in the same "Create subnet" flow by clicking "Add new subnet" at the bottom.

### Step 1.4 — Create Internet Gateway

**Why:** An Internet Gateway (IGW) is the door between your VPC and the public internet. Without it, nothing in your VPC can reach the internet or be reached from it. We need internet access because the VPN traffic travels over the public internet.

Navigate to:
```
VPC → Internet Gateways → Create internet gateway
```

| Setting | Value |
|---|---|
| Name tag | `cloud-igw` |

After creating, you will see it is in **"Detached"** state.

Click **Actions → Attach to VPC** and select `cloud-vpc`.

> The IGW must be attached to become functional. Creating it is not enough.

### Step 1.5 — Configure Route Tables

**Why route tables?** Every subnet needs to know where to send traffic. A route table is like a postal routing guide — it tells packets which door to walk out of based on their destination.

AWS creates a **main route table** automatically when you create the VPC. By default it only knows about local traffic (`10.0.0.0/16 → local`).

**Create a dedicated public route table:**

Navigate to:
```
VPC → Route Tables → Create route table
```

| Setting | Value |
|---|---|
| Name | `cloud-public-rt` |
| VPC | `cloud-vpc` |

After creating, click on it, go to **Routes tab → Edit routes**:

Add:

| Destination | Target | Why |
|---|---|---|
| `0.0.0.0/0` | `cloud-igw` | All internet traffic goes through IGW |

Go to **Subnet associations tab → Edit subnet associations**:

Associate: `cloud-public-subnet`

> The private subnet stays associated with the main route table which only has the local route. This is intentional — private servers should not be able to directly reach the internet.

### Step 1.6 — Launch the Cloud Server (Private EC2)

**Why private?** In a real enterprise, your application servers, databases, and internal services have no business being directly on the internet. They are only reachable through private connections — exactly what our VPN provides.

Navigate to:
```
EC2 → Instances → Launch instances
```

| Setting | Value | Why |
|---|---|---|
| Name | `cloud-server` | Easy identification |
| AMI | Amazon Linux 2023 | Lightweight, good for testing |
| Instance type | `t2.micro` | Free tier, enough for ping tests |
| Key pair | Create new or use existing | Required for SSH access |
| VPC | `cloud-vpc` | Must be in the correct VPC |
| Subnet | `cloud-private-subnet` | Private — no direct internet |
| Auto-assign public IP | **Disable** | Private instance should have no public IP |

**Security Group — create a new one:**

| Type | Protocol | Port | Source | Why |
|---|---|---|---|---|
| SSH | TCP | 22 | `10.1.0.0/16` | Allow SSH only from on-prem network |
| ICMP | ICMP | All | `10.1.0.0/16` | Allow ping from on-prem network |

> Notice: the security group allows traffic from `10.1.0.0/16` — the on-premises network — not from the internet. This is realistic. Your cloud server only accepts connections from known private networks.

**Write down the private IP address** of this instance after launch. You will ping this IP later.

---

## Part 2: Build the On-Premises VPC in Virginia

**Region: us-east-1 (N. Virginia)**

> **Switch your region now.** Top-right corner → N. Virginia (us-east-1).

### Why Virginia?

By placing our "on-premises" network in a completely different AWS region, we create **real geographic separation**. The traffic between Mumbai and Virginia genuinely travels across the public internet, giving us realistic WAN conditions.

### Step 2.1 — Create the On-Premises VPC

Navigate to:
```
VPC → Your VPCs → Create VPC
```

| Setting | Value | Why |
|---|---|---|
| Name tag | `onprem-vpc` | Simulated datacenter |
| IPv4 CIDR | `10.1.0.0/16` | Non-overlapping with Mumbai (10.0.0.0/16) |

### Step 2.2 — Create Subnets

**Public subnet** (for the StrongSwan router — needs internet access):

| Setting | Value |
|---|---|
| Subnet name | `onprem-public-subnet` |
| Availability Zone | `us-east-1a` |
| IPv4 CIDR | `10.1.1.0/24` |

**Private subnet** (for onprem-server — our simulated internal server):

| Setting | Value |
|---|---|
| Subnet name | `onprem-private-subnet` |
| Availability Zone | `us-east-1b` |
| IPv4 CIDR | `10.1.2.0/24` |

### Step 2.3 — Create Internet Gateway

| Setting | Value |
|---|---|
| Name tag | `onprem-igw` |

Attach to `onprem-vpc`.

### Step 2.4 — Configure Route Tables

Create public route table:

| Setting | Value |
|---|---|
| Name | `onprem-public-rt` |
| VPC | `onprem-vpc` |

Add route:

| Destination | Target |
|---|---|
| `0.0.0.0/0` | `onprem-igw` |

Associate with `onprem-public-subnet`.

> The private subnet will need a special route added later — pointing `10.0.0.0/16` toward the StrongSwan router. We will add that after the router is set up.

### Step 2.5 — Allocate an Elastic IP

**This is critical and must be done before creating the VPN.**

**Why Elastic IP?** When you stop and start an EC2 instance, its public IP changes. The AWS VPN Customer Gateway is defined by a **specific IP address**. If that IP changes, your entire VPN configuration breaks. An Elastic IP is a **static public IP** that stays yours permanently until you release it.

Navigate to:
```
EC2 → Elastic IPs → Allocate Elastic IP address
```

Keep all defaults, click **Allocate**.

**Write down this IP address.** You will use it in multiple places:
- When creating the Customer Gateway in Mumbai
- In the StrongSwan configuration files

> Do NOT associate it with an instance yet. We will do that after launching the router.

---

## Part 3: Set Up the StrongSwan VPN Router

**Region: us-east-1 (N. Virginia)**

### Why a Dedicated Router EC2?

In a real datacenter, you have a physical router or firewall at the edge of your network — a Cisco ASA, Palo Alto, or Fortigate. This device:

1. Knows your internal IP ranges
2. Maintains the VPN tunnel to AWS
3. Encrypts outgoing traffic
4. Decrypts incoming traffic
5. Forwards traffic between your internal network and the tunnel

We are replacing that physical device with an Ubuntu EC2 running StrongSwan. From AWS's perspective, it looks identical to a hardware router.

### Step 3.1 — Launch the VPN Router EC2

Navigate to:
```
EC2 → Instances → Launch instances
```

| Setting | Value | Why |
|---|---|---|
| Name | `vpn-router` | Clear identification |
| AMI | **Ubuntu 22.04 LTS** | StrongSwan works best on Ubuntu for this lab |
| Instance type | `t3.micro` | Slightly more capable than t2.micro — routing needs processing |
| Key pair | Same key as before | Convenient access |
| VPC | `onprem-vpc` | Must be in the on-prem network |
| Subnet | `onprem-public-subnet` | **Must be public** — VPN needs internet access |
| Auto-assign public IP | **Disable** | We will use Elastic IP instead |

**Security Group — create `vpn-router-sg`:**

| Type | Protocol | Port/Code | Source | Why |
|---|---|---|---|---|
| SSH | TCP | 22 | Your IP | Manage the router |
| Custom UDP | UDP | 500 | `0.0.0.0/0` | IKE — VPN negotiation |
| Custom UDP | UDP | 4500 | `0.0.0.0/0` | IKE NAT traversal |
| Custom Protocol | ESP (50) | All | `0.0.0.0/0` | Encrypted VPN data |
| ICMP | ICMP | All | `10.0.0.0/16` | Allow pings from cloud |

> **Why UDP 500?** IKE (Internet Key Exchange) runs on UDP 500. This is the handshake protocol — the two sides negotiate encryption algorithms and exchange keys. Without this port, the VPN tunnel can never be established.

> **Why UDP 4500?** NAT traversal. Our router is behind AWS NAT infrastructure. When IPSec traffic passes through NAT, it gets wrapped in UDP 4500 so the NAT device can track it. Without this, ESP packets get dropped.

> **Why ESP (Protocol 50)?** ESP (Encapsulating Security Payload) is the actual encrypted data. After IKE negotiates the tunnel on UDP 500, the real data flows as ESP packets. This is not TCP or UDP — it is its own IP protocol with number 50.

### Step 3.2 — Associate the Elastic IP

After the instance is running:

Navigate to:
```
EC2 → Elastic IPs
```

Select your allocated Elastic IP → **Actions → Associate Elastic IP address**

| Setting | Value |
|---|---|
| Resource type | Instance |
| Instance | `vpn-router` |

Click **Associate**.

Verify the Elastic IP is now shown in the instance details.

### Step 3.3 — Disable Source/Destination Check

**This is one of the most important steps. Forgetting this is the most common reason the lab fails.**

Navigate to:
```
EC2 → Instances → Select vpn-router
Actions → Networking → Change source/destination check
```

**Uncheck** "Enable" and save.

> **Why?** AWS has a security feature that checks every packet flowing through an EC2 network interface. If the packet's source IP or destination IP does not match the instance's own IP, AWS drops it. This protects against IP spoofing — but it also breaks routing.
>
> Our router needs to **forward** packets. Packets from `onprem-server` (source: `10.1.2.x`) going to Mumbai (destination: `10.0.x.x`) will be dropped by AWS at the network level unless we disable this check. The router is literally a middleman — none of the packets it forwards belong to it.

### Step 3.4 — SSH Into the Router and Install StrongSwan

From your local machine:

```bash
ssh -i your-key.pem ubuntu@<elastic-ip>
```

Once connected, update and install:

```bash
sudo apt update && sudo apt upgrade -y

sudo apt install strongswan strongswan-pki libcharon-extra-plugins strongswan-starter -y
```

**Why these specific packages?**

| Package | Purpose |
|---|---|
| `strongswan` | Core VPN engine |
| `strongswan-pki` | Key and certificate utilities |
| `libcharon-extra-plugins` | Additional encryption algorithms AWS requires |
| `strongswan-starter` | Provides the `ipsec` command and service management |

> Without `strongswan-starter`, the `ipsec` command does not exist. AWS's downloaded configuration files assume this command is available.

Verify installation:

```bash
ipsec version
```

You should see StrongSwan version output.

---

## Part 4: Create the AWS VPN Infrastructure

**Switch back to Mumbai region (ap-south-1)**

This is the AWS-managed side of the VPN. We are telling AWS:

1. Here is our VPN endpoint on the AWS side (Virtual Private Gateway)
2. Here is where the on-premises router is (Customer Gateway)
3. Create an encrypted tunnel between them (Site-to-Site VPN)

### Step 4.1 — Create the Virtual Private Gateway

**Why:** The VGW is AWS's VPN termination point. It lives inside your VPC and handles:
- Accepting incoming IPSec connections from your on-premises router
- Decrypting incoming traffic
- Encrypting outgoing traffic
- Advertising routes to your VPC

Navigate to:
```
VPC → Virtual Private Gateways → Create virtual private gateway
```

| Setting | Value | Why |
|---|---|---|
| Name tag | `cloud-vgw` | Identify as cloud-side gateway |
| ASN | Amazon default ASN | Fine for this lab (no BGP) |

After creating, **attach it to the VPC**:

Select `cloud-vgw` → **Actions → Attach to VPC** → Select `cloud-vpc`

Wait until the state shows **"Attached"** before proceeding.

> Attaching takes a minute. The VGW must be in the Attached state before it can handle VPN traffic.

### Step 4.2 — Create the Customer Gateway

**Why:** The Customer Gateway (CGW) is an AWS object that represents your on-premises router. AWS does not actually connect to this device — it just needs to know its public IP address so it can configure the VPN tunnel correctly.

Navigate to:
```
VPC → Customer Gateways → Create customer gateway
```

| Setting | Value | Why |
|---|---|---|
| Name tag | `virginia-cgw` | Represents Virginia router |
| Routing | Static | No BGP in this lab — manual routes |
| IP address | **Your Elastic IP** | The VPN router's permanent public IP |
| BGP ASN | 65000 | Required field — ignored in static routing |

> **Why use the Elastic IP and not the instance's public IP?** Regular public IPs on EC2 change every time you stop and start the instance. If you restart your `vpn-router`, the Customer Gateway would be pointing at a dead IP and your VPN would never come up again. Elastic IPs are permanent.

### Step 4.3 — Create the Site-to-Site VPN Connection

Navigate to:
```
VPC → Site-to-Site VPN Connections → Create VPN connection
```

| Setting | Value | Why |
|---|---|---|
| Name tag | `cloud-to-onprem-vpn` | Clear identification |
| Target gateway type | Virtual Private Gateway | AWS side endpoint |
| Virtual private gateway | `cloud-vgw` | Our VGW |
| Customer gateway | Existing | Use the one we just created |
| Customer gateway ID | `virginia-cgw` | Our CGW |
| Routing options | Static | Manual route entries |
| Static IP prefixes | `10.1.0.0/16` | Tell AWS that on-prem owns this CIDR |

Click **Create VPN connection**.

> AWS will now provision **two VPN tunnels** (Tunnel 1 and Tunnel 2). This is automatic — AWS always creates redundant tunnels. Each tunnel gets its own public IP on the AWS side and its own pre-shared key.
>
> The VPN connection takes **3-5 minutes** to provision. The state will show "pending" then "available". Wait for "available" before downloading configuration.

### Step 4.4 — Download the VPN Configuration

**This is the most important step for configuring StrongSwan correctly.**

Once the VPN connection shows **"Available"**:

Select the VPN connection → **Download configuration**

| Setting | Value |
|---|---|
| Vendor | Generic |
| Platform | Generic |
| Software | Strongswan |
| IKE version | ikev1 |

Click **Download**.

Open the downloaded file. It contains:

```
IPSec Tunnel #1
- Outside IP Address of Virtual Private Gateway (AWS side public IP)
- Outside IP Address of Customer Gateway (your Elastic IP)  
- Inside IP Address of Virtual Private Gateway (169.254.x.x)
- Inside IP Address of Customer Gateway (169.254.x.x)
- Pre-Shared Key
- Encryption algorithms
- Lifetime values

IPSec Tunnel #2
- Same information for the second tunnel
```

> **Keep this file open** — you will need these values in the next part. Specifically:
> - The **Outside IP of VGW** (AWS tunnel endpoint) — looks like a regular public IP
> - The **Inside IP addresses** (169.254.x.x range) — these are tunnel IPs
> - The **Pre-Shared Key** — a long random string

### Step 4.5 — Enable Route Propagation on the Cloud Route Table

**Why:** AWS VGWs can automatically push learned routes into your VPC route tables. We need the cloud-private-subnet to know that `10.1.0.0/16` is reachable through the VGW.

Navigate to:
```
VPC → Route Tables
```

Find the route table associated with `cloud-private-subnet` (the main route table or a dedicated private route table).

Click on it → **Route propagation tab → Edit route propagation**

**Enable** propagation for `cloud-vgw`.

Also manually add the route to be sure:

Go to **Routes tab → Edit routes**:

| Destination | Target |
|---|---|
| `10.1.0.0/16` | `cloud-vgw` |

> Route propagation means the VGW will automatically update this route table when BGP routes change. Since we are using static routing, the manual route handles it. Adding both is safe.

---

## Part 5: Configure StrongSwan on the Router EC2

**Back in Virginia — SSH into `vpn-router`**

Now we configure StrongSwan using the values from the downloaded AWS configuration file.

### Step 5.1 — Configure ipsec.conf

This file tells StrongSwan:
- What tunnels to create
- Where to connect to
- What encryption to use
- What networks are on each side

```bash
sudo nano /etc/ipsec.conf
```

**Delete everything and replace with:**

```conf
config setup
    charondebug="all"
    uniqueids=yes

conn %default
    ikelifetime=8h
    keylife=1h
    rekeymargin=3m
    keyingtries=%forever
    authby=psk
    keyexchange=ikev1
    dpddelay=10s
    dpdtimeout=30s
    dpdaction=restart

conn Tunnel1
    auto=start
    left=%defaultroute
    leftid=<YOUR_ELASTIC_IP>
    right=<AWS_TUNNEL1_OUTSIDE_IP>
    type=tunnel
    leftauth=psk
    rightauth=psk
    ike=aes128-sha1-modp1024!
    esp=aes128-sha1-modp1024!
    leftsubnet=10.1.0.0/16
    rightsubnet=10.0.0.0/16
    mark=100
    leftupdown=/etc/ipsec-vti.sh
    installpolicy=yes
    compress=no
```

**Replace the placeholders:**

| Placeholder | Replace With | Where to Find |
|---|---|---|
| `<YOUR_ELASTIC_IP>` | Your Elastic IP | EC2 → Elastic IPs |
| `<AWS_TUNNEL1_OUTSIDE_IP>` | Outside IP of AWS tunnel 1 | Downloaded config file |

> **Why `leftid` is your Elastic IP:** StrongSwan needs to tell AWS "I am this router." It identifies itself using the IP address. Since we are behind AWS's network, it must use the public Elastic IP to match what AWS expects (the Customer Gateway IP you configured).

> **Why `mark=100`:** This is a packet marking system. When StrongSwan establishes the tunnel, it marks packets with the number 100. This mark tells the Linux kernel to route marked packets through the VTI interface we will create. Without marks, Linux would not know which packets belong to the tunnel.

> **Why `type=tunnel`?** This is tunnel mode IPSec, meaning the entire original packet (including its IP header) is encrypted and wrapped inside a new packet. The alternative is transport mode which only encrypts the payload. AWS requires tunnel mode.

> **Why `ike=aes128-sha1-modp1024!`?** The `!` at the end means "only use this algorithm." AWS VPN Gateways by default negotiate with these specific parameters. The `!` prevents StrongSwan from proposing other algorithms that AWS might not accept.

### Step 5.2 — Configure the Pre-Shared Key

```bash
sudo nano /etc/ipsec.secrets
```

Add:

```
<YOUR_ELASTIC_IP> <AWS_TUNNEL1_OUTSIDE_IP> : PSK "<PRE_SHARED_KEY_FROM_CONFIG>"
```

Replace:
- `<YOUR_ELASTIC_IP>` — your Elastic IP
- `<AWS_TUNNEL1_OUTSIDE_IP>` — AWS tunnel 1 outside IP from downloaded config
- `<PRE_SHARED_KEY_FROM_CONFIG>` — the long pre-shared key from downloaded config

> **Keep the quotes around the PSK.** Special characters in the key need to be quoted.

Set proper permissions:

```bash
sudo chmod 600 /etc/ipsec.secrets
```

> This file contains your VPN secret. If anyone can read it, they can impersonate your router. Restricting it to root only is important even in a lab.

### Step 5.3 — Enable IP Forwarding

**This is essential and cannot be skipped.**

```bash
sudo nano /etc/sysctl.conf
```

Find and uncomment (or add) these lines:

```
net.ipv4.ip_forward=1
```

Apply immediately without rebooting:

```bash
sudo sysctl -p
```

Verify:

```bash
cat /proc/sys/net/ipv4/ip_forward
```

Should output: `1`

> **Why?** By default, Linux only processes packets addressed to itself. If a packet arrives for a different IP (like `10.0.x.x`), Linux discards it. `ip_forward=1` tells Linux to act as a router — forward packets that arrive at one interface to another interface. Without this, your router EC2 drops all VPN traffic.

---

## Part 6: Configure VTI Interface

**This is the step that most guides skip and the step that causes the most failures.**

### Why VTI Exists

AWS uses **route-based VPN**. This means:

- Traffic goes into the tunnel based on **routing table entries**, not based on IPSec policies
- You create a virtual network interface that represents the tunnel
- You add a route saying "send 10.0.0.0/16 out of this virtual interface"
- IPSec automatically encrypts everything going through that interface

Without VTI, even with a working IPSec SA (security association), packets do not enter the tunnel. The IPSec SA exists in the kernel's xfrm subsystem but there is no interface for routing to use.

### Step 6.1 — Create the VTI Script

Rather than running these commands manually (they disappear after reboot), create a script that StrongSwan runs automatically when the tunnel comes up:

```bash
sudo nano /etc/ipsec-vti.sh
```

```bash
#!/bin/bash

# VTI interface configuration script
# Called by StrongSwan when tunnel comes up or goes down

# Get the connection name from environment
CONN="$PLUTO_CONNECTION"

# Tunnel 1 settings from AWS downloaded configuration
VTI_INTERFACE="vti1"
VTI_LOCALADDR="169.254.x.x/30"    # Replace with YOUR Inside IP of Customer Gateway
VTI_REMOTEADDR="169.254.x.x/30"   # Replace with YOUR Inside IP of Virtual Private Gateway
TUNNEL_LOCAL_IP="<YOUR_ELASTIC_IP>"
TUNNEL_REMOTE_IP="<AWS_TUNNEL1_OUTSIDE_IP>"
MARK="100"

case "$PLUTO_VERB" in
    up-client)
        # Create VTI interface
        sudo ip link add ${VTI_INTERFACE} type vti \
            local ${TUNNEL_LOCAL_IP} \
            remote ${TUNNEL_REMOTE_IP} \
            key ${MARK}
        
        # Assign tunnel IP addresses
        sudo ip addr add ${VTI_LOCALADDR} remote ${VTI_REMOTEADDR} dev ${VTI_INTERFACE}
        
        # Bring interface up with correct MTU
        sudo ip link set ${VTI_INTERFACE} up mtu 1419
        
        # Add route through tunnel
        sudo ip route add 10.0.0.0/16 dev ${VTI_INTERFACE} metric 100
        
        # Disable reverse path filtering on tunnel interface
        sudo sysctl -w net.ipv4.conf.${VTI_INTERFACE}.rp_filter=2
        
        # Disable IPSec policy installation on this interface
        # (we manage routing ourselves via VTI)
        sudo sysctl -w net.ipv4.conf.${VTI_INTERFACE}.disable_policy=1
        
        ;;
    
    down-client)
        # Clean up when tunnel goes down
        sudo ip route del 10.0.0.0/16 dev ${VTI_INTERFACE}
        sudo ip link del ${VTI_INTERFACE}
        ;;
esac
```

Make it executable:

```bash
sudo chmod +x /etc/ipsec-vti.sh
```

> Replace the 169.254.x.x addresses with the exact values from your downloaded AWS config file:
> - `VTI_LOCALADDR` = Inside IP Address of Customer Gateway (the /30 address)
> - `VTI_REMOTEADDR` = Inside IP Address of Virtual Private Gateway (the /30 address)

**Alternatively — if you prefer to create the VTI manually (more transparent for learning):**

### Step 6.2 — Manual VTI Creation (for understanding)

Run these commands in sequence on `vpn-router`:

```bash
# Step 1: Create the VTI interface
# This creates a virtual tunnel interface that maps to your IPSec tunnel
sudo ip link add vti1 type vti \
    local 10.1.4.x \           # Replace with private IP of vpn-router
    remote <AWS_TUNNEL1_OUTSIDE_IP> \   # AWS tunnel outside IP
    key 100                     # Must match the mark= in ipsec.conf

# Step 2: Assign tunnel IP addresses to the interface
# These 169.254.x.x IPs come from your AWS downloaded config
sudo ip addr add 169.254.x.x/30 remote 169.254.x.x/30 dev vti1
#                ^^^^^^^^^^                ^^^^^^^^^^
#    Inside IP of Customer GW    Inside IP of Virtual Private GW

# Step 3: Bring the interface up with reduced MTU
# MTU 1419 prevents fragmentation issues inside the tunnel
sudo ip link set vti1 up mtu 1419

# Step 4: Add a route for the cloud network through the tunnel
sudo ip route add 10.0.0.0/16 dev vti1 metric 100

# Step 5: Configure rp_filter for the VTI interface
# rp_filter=2 uses loose mode - required because tunnel packets
# arrive on one interface but replies may go out another
sudo sysctl -w net.ipv4.conf.vti1.rp_filter=2

# Step 6: Disable policy-based routing on VTI
# We want route-based (VTI) behavior, not policy-based
sudo sysctl -w net.ipv4.conf.vti1.disable_policy=1
```

> **Why MTU 1419?** IPSec adds overhead to every packet — ESP header, authentication data, padding. A standard Ethernet packet is 1500 bytes. After IPSec wrapping and the outer IP header for the internet, the original packet must be smaller to fit. 1419 bytes is the safe maximum to avoid fragmentation, which kills VPN performance.

> **Why 169.254.x.x addresses?** These are link-local IP addresses from the range AWS pre-assigns for VPN tunnel interfaces. They are used only within the tunnel — they are never seen on the regular internet. AWS uses these IPs to create a point-to-point link between your VTI interface and AWS's VPN endpoint.

### Step 6.3 — Configure iptables

```bash
# Prevent TCP MSS issues inside the tunnel
# This adjusts TCP's maximum segment size for tunnel packets
sudo iptables -t mangle -A FORWARD -o vti1 -p tcp --tcp-flags SYN,RST SYN \
    -j TCPMSS --clamp-mss-to-pmtu

# Mark ESP packets coming from AWS for routing
sudo iptables -t mangle -A INPUT -p esp \
    -s <AWS_TUNNEL1_OUTSIDE_IP> \
    -d <YOUR_ELASTIC_IP> \
    -j MARK --set-xmark 100

# Allow forwarding between on-prem and cloud
sudo iptables -A FORWARD -s 10.1.0.0/16 -d 10.0.0.0/16 -j ACCEPT
sudo iptables -A FORWARD -s 10.0.0.0/16 -d 10.1.0.0/16 -j ACCEPT
```

---

## Part 7: Fix the Routing

**This is the fix that made the lab work. It is the most critical and least obvious step.**

### The Problem Without This Fix

When StrongSwan establishes an IPSec SA (Security Association), it automatically installs routes into **Linux routing table 220**. Table 220 is a separate routing table that Linux uses for IPSec policy routing.

The problem: Linux's policy routing rules give table 220 **higher priority** than the main routing table where your VTI route (`10.0.0.0/16 → vti1`) lives.

So when `onprem-server` pings `10.0.x.x`:
1. Packet arrives at `vpn-router`
2. Linux consults policy routing rules
3. Rule says "check table 220 first"
4. Table 220 says "send this out via `ens5` (normal internet)" — installed by StrongSwan
5. Packet bypasses `vti1` entirely
6. Packet goes out the regular internet interface — **unencrypted and to the wrong place**
7. Ping fails

You can verify this problem with:

```bash
ip route get 10.0.1.5
```

If you see:

```
10.0.1.5 via 10.1.0.1 dev ens5 table 220
```

The packet is being routed through `ens5` (internet interface) instead of `vti1` (tunnel). This is the bug.

### The Fix

**Step 1 — Tell StrongSwan not to install its own routes:**

```bash
sudo nano /etc/strongswan.d/charon.conf
```

Find the `charon` section and add:

```conf
charon {
    install_routes = no
    
    # ... other settings may already be here ...
}
```

> This single setting prevents StrongSwan from touching the routing tables at all. You take full manual control of routing through the VTI interface.

**Step 2 — Flush the rogue routing table:**

```bash
sudo ip route flush table 220
```

Verify it is empty:

```bash
ip route show table 220
```

Should return nothing.

**Step 3 — Verify correct routing:**

```bash
ip route get 10.0.1.5
```

Now you should see:

```
10.0.1.5 dev vti1  src 169.254.x.x
```

This means packets to the cloud are going through `vti1` — the tunnel interface. ✅

### Make sysctl Settings Persistent

```bash
sudo nano /etc/sysctl.conf
```

Add:

```
net.ipv4.ip_forward=1
net.ipv4.conf.vti1.rp_filter=2
net.ipv4.conf.vti1.disable_policy=1
```

Apply:

```bash
sudo sysctl -p
```

---

## Part 8: Launch Private EC2 Instances

### Cloud Server (already created in Step 1.6)

You should already have `cloud-server` in `cloud-private-subnet`.

If not, create it now with:
- Subnet: `cloud-private-subnet`
- No public IP
- Security group allowing ICMP from `10.1.0.0/16`

### On-Premises Private Server

**Region: Virginia (us-east-1)**

Navigate to:
```
EC2 → Launch instances
```

| Setting | Value |
|---|---|
| Name | `onprem-server` |
| AMI | Amazon Linux 2023 |
| Instance type | `t2.micro` |
| VPC | `onprem-vpc` |
| Subnet | `onprem-private-subnet` |
| Auto-assign public IP | **Disable** |

**Security Group:**

| Type | Protocol | Source |
|---|---|---|
| SSH | TCP 22 | `10.1.0.0/16` |
| ICMP | All ICMP | `10.0.0.0/16` |

### Update the On-Prem Private Route Table

The `onprem-server` is in `onprem-private-subnet`. When it tries to send packets to `10.0.0.0/16` (Mumbai), it needs to know to send them to the `vpn-router`.

Navigate to:
```
VPC → Route Tables
```

Find the route table associated with `onprem-private-subnet`:

**Routes tab → Edit routes → Add route:**

| Destination | Target | Why |
|---|---|---|
| `10.0.0.0/16` | ENI of `vpn-router` | Send cloud-bound traffic to router |

> Select `Network Interface` as the target type, then select the ENI (Elastic Network Interface) of `vpn-router`. Using the ENI directly is more reliable than using the instance ID.

---

## Part 9: Test the Connection

### Step 9.1 — Start StrongSwan

On `vpn-router`:

```bash
sudo systemctl restart strongswan-starter
```

Check status:

```bash
sudo ipsec statusall
```

Look for:

```
Connections:
  Tunnel1: %any...13.x.x.x  IKEv1, dpddelay=10s
  Tunnel1: IKEv1 SPIs: ...

Security Associations (1 up, 0 connecting):
  Tunnel1[1]: ESTABLISHED XX minutes ago
  Tunnel1{1}: INSTALLED, TUNNEL, ...
  Tunnel1{1}: 10.1.0.0/16 === 10.0.0.0/16
```

**ESTABLISHED** means the IPSec tunnel is up ✅
**INSTALLED** means the SA is active and encrypting ✅

If not established:

```bash
sudo journalctl -u strongswan-starter -f
```

Watch the logs for error messages.

### Step 9.2 — Verify AWS Tunnel Status

Back in Mumbai AWS console:

```
VPC → Site-to-Site VPN Connections → Select your VPN
```

Tunnel details should show:

| Tunnel | Status |
|---|---|
| Tunnel 1 | **UP** |
| Tunnel 2 | DOWN (normal — we only configured one) |

### Step 9.3 — Verify VTI Interface

On `vpn-router`:

```bash
ip link show vti1
```

Should show:

```
vti1: <POINTOPOINT,UP,LOWER_UP> mtu 1419 ...
```

`UP` and `LOWER_UP` means the interface is active. ✅

```bash
ip route show
```

Should include:

```
10.0.0.0/16 dev vti1 metric 100
```

This confirms cloud traffic goes through the tunnel. ✅

### Step 9.4 — Ping Test

**From `onprem-server` to `cloud-server`:**

Since `onprem-server` is private (no public IP), you need to SSH through `vpn-router`:

On `vpn-router`, use the key to SSH to `onprem-server`:

```bash
ssh -i your-key.pem ec2-user@10.1.2.x    # Private IP of onprem-server
```

Once on `onprem-server`:

```bash
ping 10.0.2.x    # Private IP of cloud-server
```

**Successful output:**

```
PING 10.0.2.x (10.0.2.x) 56(84) bytes of data.
64 bytes from 10.0.2.x: icmp_seq=1 ttl=253 time=185 ms
64 bytes from 10.0.2.x: icmp_seq=2 ttl=253 time=184 ms
64 bytes from 10.0.2.x: icmp_seq=3 ttl=253 time=183 ms
```

> The ~183ms latency is **real** — this is actual Virginia to Mumbai round-trip time over the internet, through an encrypted IPSec tunnel. This is what hybrid cloud latency looks like.

**From `cloud-server` to `onprem-server`:**

```bash
ping 10.1.2.x    # Private IP of onprem-server
```

### Step 9.5 — Verify Traffic is Encrypted

On `vpn-router`, run tcpdump while pinging:

```bash
sudo tcpdump -i eth0 host <AWS_TUNNEL1_OUTSIDE_IP>
```

You will see:

```
ESP(spi=0x..., seq=0x...)
```

ESP packets — not readable ICMP. Your private ping packets are encrypted inside these ESP frames. Nobody on the internet can see the content. ✅

---

## Troubleshooting Guide

### Problem 1: Tunnel Not Establishing (DOWN state)

**Symptoms:** `ipsec statusall` shows no ESTABLISHED connection

**Check 1 — Logs:**
```bash
sudo journalctl -u strongswan-starter -f
```

Look for:
- `no proposal chosen` → encryption algorithm mismatch — check `ike=` and `esp=` values match downloaded config
- `authentication failed` → PSK mismatch — check `/etc/ipsec.secrets` carefully
- `peer not responding` → network issue — check security group allows UDP 500 and 4500

**Check 2 — Security Group:**
Confirm `vpn-router` security group allows:
- UDP 500 inbound from `0.0.0.0/0`
- UDP 4500 inbound from `0.0.0.0/0`

**Check 3 — Elastic IP:**
Confirm the Elastic IP is associated with `vpn-router` and matches what is in:
- `/etc/ipsec.conf` (`leftid=`)
- `/etc/ipsec.secrets`
- Customer Gateway IP in AWS console

### Problem 2: Tunnel UP But Ping Fails

**Symptoms:** ESTABLISHED in ipsec statusall, but ping times out

**Check 1 — Source/Destination Check:**
```
EC2 → vpn-router → Networking → Source/destination check
```
Must be **disabled**.

**Check 2 — Routing Table 220 Issue:**
```bash
ip route get 10.0.1.5
```
If it shows `table 220` or `dev ens5`, the routing conflict is present.

Fix:
```bash
sudo nano /etc/strongswan.d/charon.conf
# Add: install_routes = no

sudo systemctl restart strongswan-starter
sudo ip route flush table 220
```

**Check 3 — VTI Interface:**
```bash
ip link show vti1
ip route show | grep vti1
```
If vti1 doesn't exist or has no route, re-run the VTI creation commands.

**Check 4 — On-Prem Route Table:**
In Virginia, the route table for `onprem-private-subnet` must have:
```
10.0.0.0/16 → vpn-router ENI
```

**Check 5 — Cloud Route Table:**
In Mumbai, the route table for `cloud-private-subnet` must have:
```
10.1.0.0/16 → cloud-vgw
```

**Check 6 — IP Forwarding:**
```bash
cat /proc/sys/net/ipv4/ip_forward
```
Must be `1`. If `0`, run: `sudo sysctl -w net.ipv4.ip_forward=1`

**Check 7 — Security Groups on Private Instances:**
`cloud-server` SG must allow ICMP from `10.1.0.0/16`
`onprem-server` SG must allow ICMP from `10.0.0.0/16`

### Problem 3: Request Reaches Cloud But No Reply

**Symptoms:** tcpdump on vti1 shows ICMP request but no ICMP reply

```bash
sudo tcpdump -i vti1
```

**Diagnosis:** The request is going through the tunnel but the reply is not coming back.

**Check 1 — cloud-server knows the return path:**
In Mumbai, verify route propagation is enabled on the VGW, and the private route table has `10.1.0.0/16 → cloud-vgw`.

**Check 2 — VGW is attached:**
In Mumbai:
```
VPC → Virtual Private Gateways
```
Confirm VGW shows "Attached" to `cloud-vpc`.

**Check 3 — Check if replies arrive on vpn-router from AWS:**
```bash
sudo tcpdump -i eth0 esp
```
You should see ESP packets arriving from the AWS tunnel IP when the cloud server tries to reply.

### Problem 4: ipsec Command Not Found

```bash
sudo apt install strongswan-starter -y
```

### Problem 5: Tunnel Goes Down Frequently

This can happen with Dead Peer Detection (DPD). Verify these settings in `ipsec.conf`:

```conf
dpddelay=10s
dpdtimeout=30s
dpdaction=restart
keyingtries=%forever
```

`keyingtries=%forever` tells StrongSwan to keep retrying indefinitely instead of giving up.

### Quick Diagnostic Commands

```bash
# Check tunnel status
sudo ipsec statusall

# Check VTI interface
ip link show vti1
ip addr show vti1

# Check routing
ip route show
ip route show table 220
ip route get 10.0.1.5

# Check forwarding
cat /proc/sys/net/ipv4/ip_forward
cat /proc/sys/net/ipv4/conf/vti1/rp_filter

# Watch tunnel packets
sudo tcpdump -i vti1
sudo tcpdump -i eth0 esp

# Watch logs live
sudo journalctl -u strongswan-starter -f

# Restart VPN
sudo ipsec restart
sudo ipsec up Tunnel1
```

---

## How Traffic Actually Flows

Understanding the exact path of a ping packet makes troubleshooting much easier.

### Ping from onprem-server to cloud-server

```
Step 1: onprem-server (10.1.2.5) sends ICMP to 10.0.2.8
        onprem-server checks its routing table:
        - 10.0.0.0/16 → 10.1.2.1 (subnet gateway)
        - subnet gateway forwards to route table entry
        - Route table: 10.0.0.0/16 → vpn-router ENI
        Packet arrives at vpn-router

Step 2: vpn-router receives packet
        Source: 10.1.2.5
        Destination: 10.0.2.8
        vpn-router checks its routing table:
        - 10.0.0.0/16 → vti1  ← the VTI interface
        Packet is sent to the vti1 interface

Step 3: vti1 interface (IPSec tunnel)
        The VTI interface is configured with mark=100
        Linux kernel's xfrm subsystem picks up the packet
        xfrm finds the IPSec SA matching mark 100
        xfrm encrypts the packet using AES-128
        xfrm wraps it in ESP format
        xfrm sends it out eth0 toward AWS tunnel IP

Step 4: Physical journey
        Encrypted ESP packet leaves vpn-router (Elastic IP)
        Travels across public internet
        Arrives at AWS VPN Gateway public IP (Mumbai)

Step 5: AWS VGW receives encrypted packet
        VGW decrypts using the shared PSK
        Unwraps the original packet: src 10.1.2.5, dst 10.0.2.8
        VGW consults cloud-vpc routing table
        Route: 10.0.2.0/24 → local (cloud-private-subnet)
        Packet delivered to cloud-server

Step 6: cloud-server receives ping request
        Sends ICMP reply: src 10.0.2.8, dst 10.1.2.5

Step 7: Return journey
        cloud-server route table: 10.1.0.0/16 → cloud-vgw
        Packet arrives at VGW
        VGW encrypts it
        Sends to Customer Gateway IP (Elastic IP of vpn-router)

Step 8: vpn-router receives encrypted return packet
        IPSec decrypts it
        Routing: 10.1.2.5 is in 10.1.0.0/16 (local network)
        Forwards to onprem-server

Step 9: onprem-server receives ping reply
        Output: 64 bytes from 10.0.2.8 ✅
```

---

## Key Concepts Summary

| Concept | Simple Explanation | Why It Matters |
|---|---|---|
| **VGW** | AWS's VPN door on the cloud side | Without it, AWS has nowhere to terminate the VPN |
| **CGW** | AWS's record of your on-prem router IP | AWS must know where to connect to |
| **IPSec** | Encryption protocol for VPN tunnels | Protects traffic crossing the public internet |
| **IKE** | How two VPN endpoints negotiate keys | Automatic — but must use matching algorithms |
| **PSK** | Shared secret password for authentication | Both sides must have the identical PSK |
| **VTI** | Virtual network interface for the tunnel | Allows route-based VPN — AWS requires this model |
| **mark=100** | Tag on packets for tunnel routing | Links StrongSwan's SA to the VTI interface |
| **Source/Dest Check** | AWS packet verification | Must be disabled or router drops all forwarded packets |
| **Table 220** | StrongSwan's hidden routing table | Conflicts with VTI — disable with install_routes=no |
| **rp_filter=2** | Reverse path filtering mode | Loose mode required for tunnel interfaces |
| **MTU 1419** | Reduced packet size for tunnel | Prevents fragmentation caused by IPSec overhead |
| **Elastic IP** | Permanent public IP | VPN must have a stable endpoint IP |
| **ip_forward** | Linux kernel routing toggle | Must be enabled or packets are dropped, not forwarded |

---

## Final Verification Checklist

Use this before debugging to ensure nothing was missed:

```
MUMBAI (CLOUD SIDE)
[ ] cloud-vpc created with CIDR 10.0.0.0/16
[ ] cloud-public-subnet and cloud-private-subnet created
[ ] cloud-igw created and attached
[ ] Public route table has 0.0.0.0/0 → IGW
[ ] Virtual Private Gateway created and ATTACHED to cloud-vpc
[ ] Route propagation enabled on private route table
[ ] Private route table has 10.1.0.0/16 → VGW
[ ] Customer Gateway created with correct Elastic IP
[ ] Site-to-Site VPN created and shows AVAILABLE
[ ] cloud-server is in private subnet with no public IP
[ ] cloud-server security group allows ICMP from 10.1.0.0/16

VIRGINIA (ON-PREM SIDE)
[ ] onprem-vpc created with CIDR 10.1.0.0/16
[ ] onprem-public-subnet and onprem-private-subnet created
[ ] onprem-igw created and attached
[ ] Elastic IP allocated and associated with vpn-router
[ ] vpn-router is in public subnet
[ ] vpn-router Source/Destination Check is DISABLED
[ ] vpn-router security group allows UDP 500, 4500, ESP (50)
[ ] StrongSwan installed with all required packages
[ ] /etc/ipsec.conf configured with correct IPs and PSK
[ ] /etc/ipsec.secrets configured with correct IPs and PSK
[ ] ip_forward = 1 in sysctl
[ ] install_routes = no in charon.conf
[ ] VTI interface (vti1) created and UP
[ ] Route: 10.0.0.0/16 → vti1 exists
[ ] table 220 is empty (ip route show table 220)
[ ] onprem-private route table has 10.0.0.0/16 → vpn-router ENI
[ ] onprem-server is in private subnet with no public IP
[ ] onprem-server security group allows ICMP from 10.0.0.0/16
```

---

*This lab demonstrates real enterprise hybrid cloud networking. The same principles apply whether you are connecting a physical Cisco router or a StrongSwan EC2 instance — IPSec is IPSec, and AWS does not know the difference.*
