# Demo Script

A five-minute walkthrough covering one full journey per role.

## 1. Employee

1. Open the auth screen and show both **Sign in** and **Sign up**.
2. Create a new Employee account, or sign in as `employee@demo.com` with `demo123`.
3. Review the seeded goal sheet.
4. Open the Smart Goal Assistant and copy a suggested goal into the draft form.
5. Add or edit goals until total weight is exactly `100%`.
6. Submit the goal sheet for manager approval.
7. After approval, try editing a goal to demonstrate the lock behaviour.
8. If a quarter window is active, enter actual achievement and status.

## 2. Manager

1. Sign in as `manager@demo.com` with `demo123`.
2. Open the approval queue.
3. Edit a target or weight inline.
4. Approve and lock the sheet, or send it back for changes with a comment.
5. Open team check-ins and save a structured check-in comment.

## 3. Admin / HR

1. Sign in as `admin@demo.com` with `demo123`.
2. Review completion metrics and cycle windows.
3. Click the **Open all quarters now** callout near the top of the dashboard to unblock every quarterly window for live progress capture.
4. Scroll to **Analytics** and walk through:
   - QoQ achievement trend (sparkline)
   - Goal distribution by UoM
   - Department completion
   - Completion heatmap — department × quarter grid with a 0% → 100% legend
   - Manager effectiveness
5. Scroll to **Notifications** to show the Outlook-style email and Microsoft Teams Adaptive Card mockups.
6. Show the **Escalation Monitor** for SLA-driven follow-up.
7. Open **Organization Hierarchy** — the reporting tree with collapsible nodes and inline edit per person.
8. Create a shared goal and push it to employees.
9. Unlock a locked goal sheet with a reason (confirmation modal + audit trail will be visible).
10. Export the achievement CSV and Excel reports, then open the audit log.

## Talking Points

- Goal locking and Admin unlock are enforced server-side, not just hidden in the UI.
- Self-service signup supports all three personas while seeded accounts keep walkthroughs fast.
- Weight and max-goal validations are enforced before submission, with the live total banner on the employee view giving real-time feedback.
- Shared goals use linked records, so the same KPI can be assigned across multiple employees and the primary owner's progress syncs automatically.
- Audit logs store actor, action, entity, before/after snapshots, reason, and timestamp.
- Org hierarchy can be edited through the UI without database changes.
- The completion heatmap satisfies BRD §5.4 ("heatmaps or progress charts showing completion rates across the organization").
- Notification previews are pixel-accurate mockups of the Outlook and Microsoft Teams payloads the live integration would send. Integration seams (Entra ID OIDC, Teams adaptive card endpoint, SMTP / Microsoft Graph) live behind the same workflow triggers.
- Reports download as both CSV and Excel for appraisal workflows.
- Smart suggestions are offline and deterministic — no external AI dependency.
- Passwords are salted scrypt, sign-in is rate-limited per IP, cross-origin state-changing requests are rejected, and the server refuses to start with a demo secret on a public host.
- The MVP runs on free-tier infrastructure today and lifts cleanly to managed PostgreSQL.
