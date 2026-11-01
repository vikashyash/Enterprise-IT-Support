---
document_id: kb-vpn-client-update
title: VPN Client Update Policy
category: network
department: IT
version: 1.0
access_level: EMPLOYEE
effective_date: 2026-03-01
source: knowledge/vpn-client-update.md
---

# VPN client update policy

AetherTech only supports Cisco Secure Client 5.1 and later on company devices. This policy explains how to update and what happens if you stay on an old build.

## Supported versions

| Version | Status | Action |
|---|---|---|
| Cisco Secure Client 5.1 or later | Supported | Keep automatic updates on |
| AnyConnect 4.10 | Unsupported since 1 March 2026 | Update immediately |
| AnyConnect 4.9 or earlier | Blocked | Gateway will reject the session |

## Why old clients fail

AnyConnect 4.10 cannot complete the current MFA handshake. Typical symptoms are a connect attempt that sits on "Contacting vpn.aethertech.example", a drop after 30–90 seconds, or a loop back to the login page. These are client problems, not a VPN outage.

## How to update on Windows

1. Open Company Portal.
2. Find **Cisco Secure Client 5.1** and click Install. This upgrades 4.10 in place.
3. If Install is greyed out, uninstall AnyConnect 4.10 from Settings → Apps, then install 5.1.
4. Reboot and connect to `vpn.aethertech.example`.

## How to update on macOS

Install **Cisco Secure Client 5.1** from Self Service, then allow the socket-filter extension again if macOS asks.

## What IT will not do

IT will not downgrade you to 4.10, and will not whitelist an old client for a single user. If Company Portal cannot install 5.1, raise a Software ticket. Do not download an installer from the internet.
