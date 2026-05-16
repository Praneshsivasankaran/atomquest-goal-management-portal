# AtomQuest Goal Management Portal

A full-stack hackathon MVP for an in-house employee goal setting and tracking portal.

The app covers the core problem statement:

- Employee goal creation with UoM, targets, and weightage validation.
- Manager approval, return-for-rework, inline edits, and lock workflow.
- Admin/HR controls for cycle windows, shared goals, unlocks, reports, and audit logs.
- Quarterly achievement tracking with system-computed progress scores.
- Role-based dashboards for Employee, Manager, and Admin journeys.

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
```

The Python server uses only the standard library so the demo can run without dependency installs. It stores demo data in SQLite locally and keeps the schema portable for PostgreSQL migration.

