---
document_id: kb-vpn-setup-windows
title: Corporate VPN Setup for Windows
category: network
department: IT
version: 1.3
access_level: EMPLOYEE
effective_date: 2026-01-15
source: knowledge/vpn-setup-windows.md
---

# Corporate VPN setup process (Windows)

This is the official AetherTech VPN setup process for Windows laptops. Use this document when an employee asks how to install or configure the corporate VPN.

## Who this applies to

Every employee with a company Windows laptop. Contractors use the same process after their account is marked ACTIVE.

## What you need before you start

- A company laptop enrolled in Intune
- Your AetherTech email and current password
- MFA registered on your phone (Microsoft Authenticator)
- Cisco Secure Client (AnyConnect) version 5.1 or later

Do not use a personal laptop for the corporate VPN. Split-tunneling or third-party VPN apps are not supported.

## Install the VPN client

1. Open Company Portal and search for **Cisco Secure Client**.
2. Install the package named **Cisco Secure Client 5.1**.
3. If Company Portal does not list it, raise an IT ticket. Do not download the client from cisco.com.
4. After install, restart the laptop once.

AnyConnect 4.10 and earlier are unsupported. They fail modern MFA and will drop every few minutes. Update through Company Portal before troubleshooting further.

## Configure the connection

1. Open **Cisco Secure Client**.
2. In the connection box enter exactly: `vpn.aethertech.example`.
3. Click **Connect**.
4. Sign in with your AetherTech email (not the employee code).
5. Approve the MFA prompt on your phone.
6. When the client shows **Connected**, the VPN is ready.

There is only one production gateway. Do not use older names such as `vpn-old.aethertech.example` or IP addresses.

## First-time checks

- You must be on the internet first (office Wi-Fi, home Wi-Fi, or phone hotspot). The VPN does not replace your local internet.
- Office network users still connect through the same gateway when they need datacenter resources from a guest VLAN.
- After connecting, open https://intranet.aethertech.example. If that page loads, the VPN tunnel is working.

## Common setup mistakes

- Typing `vpn.aethertech.com` instead of `vpn.aethertech.example`
- Using a personal Gmail or Microsoft account on the MFA prompt
- Leaving an old AnyConnect 4.x install beside 5.1 — uninstall 4.x first
- Connecting from a public computer

## If setup still fails

1. Confirm Cisco Secure Client is 5.1 or later (Help → About).
2. Forget and re-add `vpn.aethertech.example`.
3. If the client says the service is unreachable, check the IT status page or ask the support agent to check VPN service health. Do not keep reconnecting during a declared outage.
4. If setup is complete and the tunnel still drops, follow the VPN troubleshooting guidance or raise a Network ticket.
