---
document_id: kb-software-installation-policy
title: Software Installation Policy
category: software
department: EndUserSupport
version: 2.0
access_level: EMPLOYEE
effective_date: 2026-02-12
source: knowledge/software-installation-policy.md
---

# Software installation policy

This is the company policy for installing software on AetherTech devices. Ask the support agent to install from the approved catalog. Do not run installers from the internet.

## Three software classes

### 1. Pre-approved, no license seat

Examples: 7-Zip, Google Chrome, Microsoft Edge add-ons already in Company Portal.

Anyone may install these from Company Portal or Self Service. No ticket and no manager approval.

### 2. License required, no extra approval

Examples: Visio, Project, Adobe Acrobat Pro.

IT checks that a license seat is free, then installs. If no seat is free, Purchasing must buy one. You will get a ticket update, not a silent install.

### 3. License required and approval required

Examples: **Docker Desktop**, Visual Studio Enterprise, Postman Team, any local Kubernetes tool.

These need all of the following before install:

1. A business reason (what you will run, which project).
2. Manager approval in the IT approval queue.
3. A free license seat if the catalog marks `license_required`.
4. An IT_ADMIN to perform the install after approval. Employees cannot self-install this class.

## Can employees install Docker?

No. Docker Desktop is approval-required and license-required. Local admin rights are not enough. The support agent will check the catalog and open an approval request. Until a manager approves it, Docker must not be sideloaded.

Running Docker in WSL from a personal installer is a policy violation. IT will remove unapproved Docker installs during the next compliance scan.

## What is never allowed

- Torrent clients, keygens, or cracked plugins
- Personal antivirus next to CrowdStrike
- Browser-downloaded copies of software that already exists in Company Portal
- Admin-right bypass tools (Unlocker, custom sudo wrappers)

## How to request an install

Tell the support agent the exact catalog name, for example "Docker Desktop" or "Visual Studio Enterprise", and the hostname of the laptop. If you only say "install the application", the agent will ask which one.
