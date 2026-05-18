# AtomQuest Goal Management Portal

A full-stack hackathon MVP for an in-house employee goal setting and tracking portal.

The app covers the core problem statement:

- Employee goal creation with UoM, targets, and weightage validation.
- Manager approval, return-for-rework, inline edits, and lock workflow.
- Admin/HR controls for cycle windows, shared goals, unlocks, reports, and audit logs.
- Quarterly achievement tracking with system-computed progress scores.
- Role-based dashboards for Employee, Manager, and Admin journeys.

## Feature Map

| Requirement | Status |
| --- | --- |
| Employee goal sheet creation | Built |
| UoM support: Numeric, %, Timeline, Zero-based | Built |
| Weightage validation: total 100%, min 10%, max 8 goals | Built |
| Manager approval, inline edits, return for rework | Built |
| Goal locking after approval | Built |
| Admin unlock with audit reason | Built |
| Shared departmental goals | Built |
| Quarterly achievement capture | Built |
| Planned vs actual manager check-ins | Built |
| CSV achievement report | Built |
| Audit trail | Built |
| Escalation rules model | Seeded foundation |
| Microsoft Entra ID / Teams integration | Documented bonus path |

## Quick Start

```powershell
python app/server.py --port 8000
```

Then open:

```text
http://localhost:8000
```

## Demo Credentials

| Role | Email | Password |
| --- | --- | --- |
| Employee | employee@demo.com | demo123 |
| Manager | manager@demo.com | demo123 |
| Admin / HR | admin@demo.com | demo123 |

## Scripts

```powershell
python -m unittest discover -s tests
npm run dev
npm run test
python app/server.py --seed-only
```

The Python server uses only the standard library so the demo can run without dependency installs. It stores demo data in SQLite locally and keeps the schema portable for PostgreSQL migration.

## Suggested GitHub Setup

Create a new public GitHub repository named `atomquest-goal-management-portal`, then connect this local repo:

```powershell
git branch -M main
git remote add origin https://github.com/<your-username>/atomquest-goal-management-portal.git
git push -u origin main
```

## Demo Notes

- The default date-based windows follow the problem statement.
- For a live demo of quarterly progress capture, sign in as Admin and adjust the relevant quarter window to include today's date.
- The app intentionally keeps setup cheap: no paid APIs, no build step, and no dependency install required for the local demo.

## Deployment

The repo includes `render.yaml` and a `Procfile`.

Recommended hackathon path:

1. Push to a public GitHub repo.
2. Import the repo into Render.
3. Use the generated live URL in the submission form.

More detail is in `docs/deployment.md`.
