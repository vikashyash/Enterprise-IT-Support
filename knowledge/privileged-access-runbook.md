---
document_id: kb-privileged-access-runbook
title: Privileged Access and Admin Password Reset Runbook
category: access
department: IdentityAccess
version: 1.0
access_level: IT_ADMIN
effective_date: 2026-01-30
source: knowledge/privileged-access-runbook.md
---

# Privileged access and admin password reset runbook

Restricted to IT_ADMIN. Do not share these steps with employees in chat.

## When this runbook applies

Use it only after a verified identity check: the employee is on a recorded service-desk call, or a manager has confirmed the request in the approval queue. A chat message alone is not enough.

## Admin password reset

1. Open the Identity console, find the employee by employee code, not by display name.
2. Trigger **Temporary Access Pass** valid for 15 minutes, one use.
3. Read the pass to the employee on the phone. Do not paste it into the support chat, email, or a ticket comment that the employee can forward.
4. Force MFA re-registration on next sign-in if the reason is a lost phone.
5. Write the ticket number into the admin audit note.

## Local admin exception on a laptop

Local admin is granted for a maximum of 8 hours through the PAM tool, never as a permanent Active Directory group. Record the change ticket. Remove the grant the same day.

## Break-glass accounts

Break-glass usernames are stored in the offline safe. They are not listed in this knowledge base on purpose. If you need one, open the sealed envelope procedure with a second IT_ADMIN present.
