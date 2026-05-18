# Demo Script

## 1. Employee Journey

1. Open the auth screen and show both **Sign in** and **Sign up**.
2. Create a new Employee account, or sign in as `employee@demo.com` with `demo123`.
3. Review the seeded goal sheet.
4. Open Smart Goal Assistant and copy a suggested goal into the draft form.
5. Add or edit goals until total weightage is exactly `100%`.
6. Submit the goal sheet for manager approval.
7. After approval, return as Employee and try editing goals to show the lock behavior.
8. If a quarter window is active, enter actual achievement and status.

## 2. Manager Journey

1. Sign in as `manager@demo.com` with `demo123`.
2. Open the approval queue.
3. Edit a target or weightage inline.
4. Approve and lock the sheet, or return it for rework with a comment.
5. Open team check-ins and save a structured check-in comment.

## 3. Admin / HR Journey

1. Sign in as `admin@demo.com` with `demo123`.
2. Review completion metrics and cycle windows.
3. Click the prominent **Open all quarters now** callout near the top of the dashboard. This temporarily unblocks every quarterly window so the next step's progress capture works on demand.
4. Scroll to **Analytics Snapshot** and walk through:
   - QoQ achievement trend (sparkline)
   - Goal distribution by UoM
   - Department completion
   - **Completion Heatmap** *(new)* — colour-coded department × quarter grid with a 0% → 100% legend. Hover for tooltips.
   - Manager effectiveness
5. Scroll to **Notification Preview** *(now upgraded)*:
   - The Email cards render as full Outlook-style messages with subject, sender, preheader, body, CTA, and footer.
   - The Teams card mirrors a real Adaptive Card layout with bot avatar, fact list, primary + secondary actions.
   - Mention that the integration seams (Microsoft Entra ID OIDC, Teams adaptive card endpoint, SMTP/Graph send) live behind the same trigger points; flipping the env vars on would publish these payloads live.
6. Show the **Escalation Monitor** so judges see the SLA enforcement story.
7. Open **Organization Hierarchy** *(new tree view)*:
   - The reporting tree renders top-level managers/admins at the root with their reports indented under collapsible nodes.
   - Click any node to expand the inline edit form (name, role, department, manager).
   - Toggle the "Flat directory" disclosure at the bottom to show the original table view side-by-side.
8. Create a shared goal and push it to employees.
9. Unlock a locked goal sheet with a reason (the confirmation modal + audit trail will be visible).
10. Export the achievement CSV and Excel reports, then show audit logs (timestamps are now formatted as readable local dates).

## Judge-Friendly Talking Points

- Goal locking and Admin unlock are enforced server-side, not just hidden in the UI.
- Self-service signup supports all three personas while seeded accounts keep the demo fast.
- Weight and max-goal validations are enforced before submission, with the live total banner on the employee view giving real-time feedback.
- Shared goals use linked records, so the same KPI can be assigned across multiple employees.
- Audit logs store actor, action, entity, before/after snapshots, reason, and timestamp.
- HR can manage org hierarchy as a real reporting tree — no database changes or developer help.
- The completion heatmap directly satisfies BRD §5.4's "heatmaps or progress charts showing completion rates across the organization."
- Notification previews are pixel-accurate mockups of the Outlook + Teams payloads the live integration would send; the trigger points already fire on every workflow event.
- Reports download as both CSV and Excel for appraisal workflows.
- Smart suggestions are offline and deterministic, so the demo does not depend on external AI credits.
- "Open all quarters now" opens cycle windows locally so quarterly capture can be shown on demand.
- Security: passwords are salted scrypt, login is rate-limited per IP, cross-origin state-changing requests are rejected, and the server refuses to start with the demo secret when bound to a public host.
- The MVP is low-cost because it can run on a small web service plus managed PostgreSQL.
