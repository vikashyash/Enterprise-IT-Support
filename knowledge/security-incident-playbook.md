---
document_id: kb-security-incident-playbook
title: Account Compromise Containment Playbook
category: security
department: Security
version: 2.0
access_level: SECURITY_ADMIN
effective_date: 2026-03-10
source: knowledge/security-incident-playbook.md
---

# Account compromise containment playbook

Restricted to SECURITY_ADMIN. Employees asking about a suspicious login should receive the public MFA guidance only.

## Severity

Treat an approved-but-unexpected MFA push, an unfamiliar enrolled device, or an external forwarding rule as a confirmed account-compromise candidate until cleared.

## Containment order

1. Disable the account in Identity. Do not reset the password first — that can leave tokens valid.
2. Revoke all refresh tokens and app-password entries.
3. Remove mailbox forwarding and new inbox rules created in the last 14 days.
4. Pull the sign-in log for 72 hours and attach it to the security incident.
5. Only then issue a Temporary Access Pass through IT_ADMIN and require MFA re-enrolment.

## What not to tell the employee

Do not list internal tool names, do not confirm whether a named attacker was seen, and do not share other users' sign-in rows. Tell them only that the account is locked and that Security will contact them.

## When to escalate to legal

Escalate if customer data, payroll files, or a privileged role (IT_ADMIN, SECURITY_ADMIN, finance posting) was used after the first bad sign-in.
