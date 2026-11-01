---
document_id: kb-slow-laptop
title: Slow Laptop Troubleshooting
category: hardware
department: EndUserSupport
version: 1.4
access_level: EMPLOYEE
effective_date: 2026-01-08
source: knowledge/slow-laptop.md
---

# Laptop is very slow

Follow this guide when a company laptop takes a long time to boot, open apps, or stay responsive.

## Likely causes, in the order IT sees them

1. Disk more than 90 percent full (under about 10 percent free). This is the most common cause.
2. Memory pressure on 16 GB devices when Chrome, Teams, and a local build tool run together.
3. An outdated or looping endpoint agent (Defender, Company Portal, CrowdStrike).
4. Failing SSD or thermal throttling — less common, needs a hardware ticket.

## What you can do immediately

- Empty Recycle Bin and Downloads. Move ISO files and old video recordings to OneDrive.
- You need at least 40 GB free on a 512 GB laptop. If free space is under 20 GB, stop installing software and raise a ticket after cleanup.
- In Task Manager, note the top three processes by CPU and Memory. Restart those apps before rebooting.
- Reboot once. Do not reboot repeatedly; it hides the process list IT needs.

## Startup programs

Windows: Task Manager → Startup apps. Disable anything that is not Microsoft Teams, Company Portal, CrowdStrike, or Cisco Secure Client.

macOS: System Settings → General → Login Items. Remove personal sync tools.

## When IT will replace the device

IT replaces a laptop only when diagnostics show a failing disk, 8 GB of RAM on an unsupported build, or the device is past its 4-year refresh. Slowness from a full disk is not a replacement reason.

## How the support agent will check this

The agent looks up your primary device, storage used percent, and a simulated performance snapshot. If storage is critically low, free space first. If CPU or memory stays above 85 percent after a cleanup, raise a Hardware ticket with the top processes.
