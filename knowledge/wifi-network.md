---
document_id: kb-wifi-network
title: Office Wi-Fi and Network Access
category: network
department: Network
version: 1.1
access_level: EMPLOYEE
effective_date: 2025-09-18
source: knowledge/wifi-network.md
---

# Office Wi-Fi and network access

## Corporate SSID

Connect to **AetherTech-Corp**. Use your AetherTech email and password. The network uses WPA2-Enterprise. There is no shared PSK.

If Windows asks for a server certificate, accept only the certificate issued to `radius.aethertech.example`. Decline any other name.

## Guest network

**AetherTech-Guest** is for visitors and personal phones. It cannot reach file shares, printers, or the intranet. Employees must not do daily work on the guest SSID.

## After you join the wrong network

Forget AetherTech-Guest, join AetherTech-Corp, then lock and unlock the laptop so Group Policy reapplies. Mapped drives will not appear while you are still on guest Wi-Fi.

## Wired desks

Docking stations in HQ and the Bengaluru office provide wired 1 Gbps. Plug the dock USB-C cable in before you open the lid. If the dock has no link light, raise a Network ticket; do not swap docks between floors without the asset tag being updated.

## Home network

Home Wi-Fi is fine for email and VPN. IT does not support changing your home router. If only VPN fails from home but websites load, follow the VPN setup and client-update articles rather than this one.
