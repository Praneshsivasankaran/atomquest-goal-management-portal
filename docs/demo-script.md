# Demo Script

## 1. Employee Journey

1. Sign in as `employee@demo.com` with `demo123`.
2. Review the seeded goal sheet.
3. Open Smart Goal Assistant and copy a suggested goal into the draft form.
4. Add or edit goals until total weightage is exactly `100%`.
5. Submit the goal sheet for manager approval.
6. After approval, return as Employee and try editing goals to show the lock behavior.
7. If a quarter window is active, enter actual achievement and status.

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
5. Create a shared goal and push it to employees.
6. Unlock a locked goal sheet with a reason.
7. Export the achievement CSV and show audit logs.

## Judge-Friendly Talking Points

- Goal locking and Admin unlock are enforced server-side, not just hidden in the UI.
- Weightage and max-goal validations are enforced before submission.
- Shared goals use linked records, so the same KPI can be assigned across multiple employees.
- Audit logs store actor, action, entity, before/after snapshots, reason, and timestamp.
- Smart suggestions are offline and deterministic, so the demo does not depend on external AI credits.
- Demo mode opens cycle windows locally so quarterly capture can be shown on demand.
- The MVP is low-cost because it can run on a small web service plus managed PostgreSQL.
