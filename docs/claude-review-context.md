# Claude Review Context

Use this document to cross-verify the AtomQuest Goal Management Portal implementation and suggest improvements before the final GitHub/Render submission.

## Project Summary

This is a local hackathon MVP for the AtomQuest 1.0 problem statement: an in-house Employee Goal Setting and Tracking Portal for companies. It supports the required personas and lifecycle:

- Employee creates goals, validates weightage, submits for approval, and updates quarterly achievement.
- Manager reviews submitted goals, edits target/weightage inline, approves/locks, returns for rework, and records quarterly check-ins.
- Admin/HR manages cycles, organization hierarchy, shared goals, unlock exceptions, escalation monitoring, audit logs, and reports.

The app is intentionally dependency-light so it can run locally and deploy cheaply:

- Backend: Python standard-library HTTP server plus SQLite persistence.
- Frontend: static HTML/CSS/JS served by the backend.
- Storage: SQLite demo DB with relational schema, intended to be PostgreSQL-portable later.
- Tests: Python `unittest`.

## How To Run

From the repo root:

```powershell
python app/server.py --seed-only
python app/server.py --port 8000
```

Open:

```text
http://127.0.0.1:8000/
```

Run tests:

```powershell
npm run test
node --check public/app.js
python -m py_compile app/auth.py app/business.py app/storage.py app/server.py
```

## Demo Credentials

```text
Employee: employee@demo.com / demo123
Manager:  manager@demo.com / demo123
Admin:    admin@demo.com / demo123
```

The auth screen also supports self-service signup for Employee, Manager, and Admin/HR.

## Main Files

- `app/server.py`: HTTP server, routing, auth-protected API endpoints, static file serving.
- `app/storage.py`: SQLite schema, seed data, workflow operations, report exports, dashboard data.
- `app/business.py`: domain rules, validation, progress scoring formulas.
- `app/auth.py`: simple JWT-style token creation/verification.
- `public/app.js`: single-page frontend behavior and role dashboards.
- `public/styles.css`: app styling and responsive UI.
- `tests/test_business.py`: validation and scoring tests.
- `tests/test_storage.py`: workflow, signup, shared-goal, report, and admin tests.

## Features Implemented

- Role-based sign in and signup for Employee, Manager, Admin/HR.
- Employee goal sheet creation.
- UoM support: Numeric, Percentage, Timeline, Zero-based.
- Weightage rules:
  - Total goal weightage must equal 100%.
  - Minimum individual goal weightage is 10%.
  - Maximum 8 goals per employee.
- Manager approval workflow:
  - Submitted goal queue.
  - Inline manager edit for target/weightage.
  - Approve and lock.
  - Return for rework with comment.
- Locking and Admin unlock:
  - Approved goals lock.
  - Admin unlock requires reason and writes audit log.
- Shared goals:
  - Admin creates shared departmental KPI.
  - Recipients can only adjust weightage.
  - Primary owner progress syncs to linked goal rows.
- Quarterly achievement tracking:
  - Employee enters actual achievement, status, notes.
  - System computes score.
  - Manager sees planned vs actual and saves check-in comments.
- Admin/HR:
  - Cycle window management.
  - Demo-mode window opener for live judging.
  - Organization hierarchy editing.
  - Shared goal creation and shared goal library.
  - Escalation monitor.
  - Audit logs.
- Reporting:
  - CSV achievement export.
  - XLSX achievement export.
  - Report Center UI.
- Analytics:
  - Completion metrics.
  - Goal distribution by UoM.
  - Department completion.
  - QoQ achievement trend.
  - Manager check-in effectiveness.
- Bonus-style polish:
  - Smart Goal Assistant with local deterministic suggestions.
  - Email/Teams notification preview cards.
  - Role switcher for faster demo flow.
  - Deployment config: `render.yaml` and `Procfile`.

## Important API Endpoints

Auth:

- `POST /api/auth/login`
- `POST /api/auth/signup`
- `GET /api/me`
- `GET /api/app-state`

Employee:

- `GET /api/goals/suggestions`
- `POST /api/goals`
- `PATCH /api/goals/{id}`
- `DELETE /api/goals/{id}`
- `POST /api/goal-sheet/submit`
- `POST /api/goals/{id}/progress`

Manager:

- `PATCH /api/manager/goals/{id}`
- `POST /api/manager/sheets/{id}/approve`
- `POST /api/manager/sheets/{id}/return`
- `POST /api/manager/sheets/{id}/checkins`

Admin:

- `POST /api/admin/shared-goals`
- `POST /api/admin/demo-mode`
- `PATCH /api/admin/users/{id}`
- `POST /api/admin/sheets/{id}/unlock`
- `PATCH /api/admin/windows/{phase}`

Reports:

- `GET /api/reports/achievement.csv`
- `GET /api/reports/achievement.xlsx`

## Things To Cross-Verify

Please review the code and UI for:

- Whether every must-have requirement from the problem statement is represented.
- Any workflow bugs in goal creation, submission, approval, locking, unlocking, and progress capture.
- Any missing server-side permission checks or role access leaks.
- Whether shared goal restrictions are strong enough.
- Whether date-window enforcement works correctly and is demo-friendly.
- Whether XLSX export is valid enough for Excel/Google Sheets.
- Whether audit logs capture important state changes.
- Whether the UI feels polished, enterprise-grade, and understandable for non-technical judges.
- Whether any app copy, labels, or forms can be made clearer.
- Whether there are hidden edge cases around role changes, manager reassignment, duplicate users, or locked sheets.

## Known Tradeoffs / Limitations

- The backend currently uses Python standard library + SQLite to avoid dependency installation and reduce demo friction. For a production-grade version, migrate to FastAPI + PostgreSQL + Alembic.
- Password hashing is SHA-256 for demo simplicity. Use bcrypt/argon2 in production.
- Tokens are simple HMAC JWT-style tokens. Use a tested JWT library in production.
- Teams/Email and Microsoft Entra ID are represented as bonus-ready surfaces/docs, not live integrations.
- Browser visual tests were not automated because Playwright is not installed in this local environment.
- The generated XLSX is minimal but valid OOXML for a single-sheet report.

## Suggested Improvements If Time Remains

- Add screenshots to README after final UI review.
- Add a proper architecture PNG/PDF for submission.
- Add an API smoke-test file that starts the server and tests auth/report endpoints end to end.
- Improve responsive mobile table handling for very narrow screens.
- Add a persistent notification/escalation rule editor instead of seeded rules only.
- Add a simple “demo checklist” side panel in the app.
- Convert backend to FastAPI/PostgreSQL if deployment time allows, otherwise keep current low-friction server for hackathon reliability.

## Pasteable Claude Prompt

```text
I am building a hackathon project called AtomQuest Goal Management Portal. It is a web-based employee goal setting and tracking portal with Employee, Manager, and Admin/HR roles.

Please review the implementation as a senior full-stack engineer and hackathon judge. Focus on requirement coverage, workflow correctness, role-based access, UI/UX quality, bugs, demo risks, and high-impact improvements before final GitHub + Render deployment.

Repo structure:
- app/server.py: Python HTTP API and static serving
- app/storage.py: SQLite schema, seed data, workflows, reports
- app/business.py: validation and scoring rules
- app/auth.py: token auth
- public/app.js: frontend SPA
- public/styles.css: UI styling
- tests/: unittest coverage
- docs/: architecture, demo script, deployment notes

Implemented features include signup/signin, role dashboards, goal creation, weightage validation, manager approval and locking, admin unlock, shared goals, quarterly progress, check-ins, audit logs, org hierarchy management, CSV/XLSX reports, analytics, escalation monitor, smart goal suggestions, and deployment config.

Please produce:
1. Top bugs or risks, ordered by severity.
2. Missing problem-statement requirements, if any.
3. UI/UX improvements that would impress judges.
4. Backend/security improvements that are worth doing before submission.
5. A short final-priority checklist.
```

