---
document_id: kb-outlook-sync
title: Outlook Stopped Syncing
category: email
department: Collaboration
version: 1.2
access_level: EMPLOYEE
effective_date: 2025-11-20
source: knowledge/outlook-sync.md
---

# Outlook stopped syncing

Use this article when new mail, calendar items, or Teams meeting updates stop appearing in the Outlook desktop app.

## First checks (do these in order)

1. Confirm https://outlook.office.com opens in a browser and shows current mail. If the web inbox is also stale, the mailbox or Exchange Online is the issue — ask support to check the Email service. Do not repair the desktop profile yet.
2. Confirm you are on the internet. Outlook needs either corporate Wi-Fi, VPN, or a working home connection. Cached mode will show old mail without an error.
3. Click Send/Receive → Update Folder. If it fails with 0x80040115 or 0x8004011D, continue below.

## Restart the Outlook profile pieces

1. Quit Outlook and Teams.
2. Open Task Manager and end any leftover `OUTLOOK.EXE` or `olk.exe` process.
3. Start Outlook. If it asks to activate, sign in with your AetherTech email only.
4. File → Office Account → Update Options → Update Now.

## Repair a stuck Windows profile

Only do this if the web inbox is healthy and the desktop app is more than two hours behind.

1. Close Outlook.
2. Open Control Panel → Mail (Microsoft Outlook) → Show Profiles.
3. Add a new profile named `AetherTech-Repair`, set it as default, and launch Outlook so it recreates the OST.
4. Do not delete the old profile until you have confirmed mail is flowing for a day.

## Shared mailboxes and delegates

A shared mailbox that never syncs is usually a missing Full Access grant, not a broken Outlook. Request access through the support agent. Adding the mailbox manually by email address will fail.

## What not to do

- Do not run third-party PST tools.
- Do not switch the account type from Microsoft 365 to IMAP.
- Do not delete your OST while Outlook is open.

If repair fails after a new profile, raise a Collaboration ticket and include the exact error code.
