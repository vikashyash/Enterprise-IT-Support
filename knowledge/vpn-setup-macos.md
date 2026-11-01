---
document_id: kb-vpn-setup-macos
title: Corporate VPN Setup for macOS
category: network
department: IT
version: 1.1
access_level: EMPLOYEE
effective_date: 2026-02-03
source: knowledge/vpn-setup-macos.md
---

# Corporate VPN setup process (macOS)

Use this guide to install and connect the AetherTech VPN on a company Mac.

## Requirements

- Company Mac enrolled in Jamf
- macOS 13 or later
- Cisco Secure Client 5.1 from Self Service, not from the App Store
- Working MFA in Microsoft Authenticator

## Install

1. Open **Self Service**.
2. Install **Cisco Secure Client 5.1**.
3. If macOS asks to allow a system extension, open System Settings → Privacy & Security and allow **Cisco AnyConnect Socket Filter**.
4. Restart once after the extension is allowed.

## Connect

1. Open Cisco Secure Client from Applications.
2. Enter `vpn.aethertech.example` and click Connect.
3. Sign in with your AetherTech email and approve MFA.
4. The menu-bar icon turns locked when the tunnel is up.

## macOS-specific notes

- iCloud Private Relay and third-party DNS apps (AdGuard, NextDNS) must be off while on VPN. They break internal name resolution.
- If Safari cannot open intranet sites but the client says Connected, flush DNS: open Terminal and run `sudo dscacheutil -flushcache; sudo killall -HUP mDNSResponder`.
- Personal Macs are not supported, including Macs that were never enrolled in Jamf.

## When to stop and raise a ticket

If the system extension is blocked by a firmware password you do not have, raise an EndUserSupport ticket. IT must unlock that setting; employees must not disable SIP.
