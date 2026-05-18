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
3. Click **Open Demo Windows** if the demo needs progress capture now.
4. Show QoQ trends, manager effectiveness, notification previews, and escalation monitor.
5. Update a user in Organization Hierarchy to show HR control over departments and reporting lines.
6. Create a shared goal and push it to employees.
7. Unlock a locked goal sheet with a reason.
8. Export the achievement CSV and Excel reports, then show audit logs.

## Judge-Friendly Talking Points

- Goal locking and Admin unlock are enforced server-side, not just hidden in the UI.
- Self-service signup supports all three personas while seeded accounts keep the demo fast.
- Weightage and max-goal validations are enforced before submission.
- Shared goals use linked records, so the same KPI can be assigned across multiple employees.
- Audit logs store actor, action, entity, before/after snapshots, reason, and timestamp.
- HR can manage org hierarchy without database changes or developer help.
- Reports download as both CSV and Excel for appraisal workflows.
- Smart suggestions are offline and deterministic, so the demo does not depend on external AI credits.
- Demo mode opens cycle windows locally so quarterly capture can be shown on demand.
- The MVP is low-cost because it can run on a small web service plus managed PostgreSQL.
