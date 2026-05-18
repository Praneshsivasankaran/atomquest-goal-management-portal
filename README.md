# AtomQuest Goal Management Portal

An in-house employee goal setting and tracking portal for the full appraisal lifecycle: goal creation, manager approval, quarterly check-ins, shared KPIs, escalations, analytics, and audit-ready governance.

Built for the AtomQuest 1.0 BRD. Phase 1 (goal creation and approval) and Phase 2 (quarterly check-ins) are end-to-end functional, with every Section 5 bonus track delivered: analytics with completion heatmap, escalation monitor, Microsoft Teams + Outlook notification mockups, Entra-ready auth seam, shared goals, and a complete audit trail.

## Live Demo

| Role | Email | Password |
| --- | --- | --- |
| Employee | `employee@demo.com` | `demo123` |
| Manager | `manager@demo.com` | `demo123` |
| Admin / HR | `admin@demo.com` | `demo123` |

You can also use **Sign up** to create a new Employee, Manager, or Admin account.

## Run Locally

```powershell
python app/server.py --port 8000
```

Open <http://localhost:8000>. No dependencies to install — the backend uses the Python standard library and SQLite. The DB seeds itself on first run.

To reset demo data:

```powershell
python app/server.py --seed-only
```

## Tests

```powershell
python -m unittest discover -s tests
```

35 tests cover workflow correctness, weight rules, manager IDOR guards, scrypt password storage + legacy migration, auth rate limiting, demo seed health, and frontend static assertions.

## BRD Coverage

| Requirement | Status |
| --- | --- |
| Self-service signup for Employee, Manager, Admin | ✅ |
| Employee goal sheet creation | ✅ |
| UoM support (Numeric, %, Timeline, Zero-based) | ✅ |
| Weight rules (total 100%, min 10%, max 8) | ✅ enforced server-side with `Decimal` |
| Manager approval, inline edits, send back for changes | ✅ revalidates after edits |
| Goal locking after approval | ✅ |
| Admin unlock with audit reason | ✅ |
| Shared departmental goals (recipients only edit weight) | ✅ |
| Quarterly achievement capture (Q1–Q4) | ✅ window-gated |
| Manager check-ins (planned vs actual + comment) | ✅ |
| CSV and Excel achievement reports | ✅ valid OOXML XLSX |
| Audit trail (actor, action, entity, before/after, reason) | ✅ |
| Completion dashboard | ✅ |
| Org hierarchy management | ✅ tree view with inline edit |
| Cycle window management + demo mode | ✅ |
| **Bonus** Microsoft Entra ID SSO | 🟡 auth seam SSO-ready, integration stubbed |
| **Bonus** Email + Teams notifications | 🟡 pixel-accurate Outlook + Adaptive Card mockups, env-var-flippable |
| **Bonus** Escalation module | ✅ rules + events monitor |
| **Bonus** Analytics (QoQ trend, heatmap, distribution, manager effectiveness) | ✅ |

## Architecture

See [docs/architecture.md](docs/architecture.md) for the Mermaid diagram and production upgrade path.

**Stack**: Python stdlib HTTP server + SQLite for the demo (PostgreSQL-portable schema). Vanilla JS SPA frontend, no build step. Salted **scrypt** password hashing, per-IP auth rate limiting, Origin-based CSRF guard, tz-aware cycle windows (`Asia/Kolkata`).

## Deployment

`render.yaml` and `Procfile` are pre-configured. Recommended path:

1. Push the repo to public GitHub.
2. **Render → New Web Service** from the repo (zero build, free plan).
3. Render auto-generates `APP_SECRET`. After the first deploy, set `APP_ORIGIN` in the Render env vars to your live URL (e.g. `https://atomquest-goal-management-portal.onrender.com`) — this is required so browser POSTs aren't blocked by the CSRF guard.
4. Use the generated `.onrender.com` URL in the submission form.

Detailed steps in [docs/deployment.md](docs/deployment.md).

## Demo Script

See [docs/demo-script.md](docs/demo-script.md) — Employee → Manager → Admin walkthrough with all bonus features called out. ~5 minutes end-to-end.

## Submission Checklist

See [docs/submission-checklist.md](docs/submission-checklist.md) for the full pre-submission sweep.

## Project Layout

```
app/
  server.py     HTTP server, routing, auth, CSRF + rate limiting
  storage.py    SQLite schema, seed data, workflow + reports
  business.py   Validation rules, scoring formulas, tz helpers
  auth.py       Scrypt password hashing + JWT-style tokens
public/
  index.html    SPA shell
  app.js        Frontend behaviour for all three role dashboards
  styles.css    Design system
tests/
  test_business.py     Validation, scoring, security
  test_storage.py      Workflows, seed health, migrations
  test_server.py       Manager IDOR guards, tz helpers
  test_frontend_static.py  Static frontend assertions
docs/
  architecture.md
  architecture.png
  demo-script.md
  deployment.md
  submission-checklist.md
render.yaml
Procfile
requirements.txt
runtime.txt
.env.example
```
