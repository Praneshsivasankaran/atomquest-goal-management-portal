# Submission Checklist

Everything you need to paste / link in the submission form, in order.

## 1. Source code repository

**URL**: <https://github.com/Praneshsivasankaran/atomquest-goal-management-portal>

Branch: `main`. Latest commit at submission time will be visible from the GitHub homepage.

## 2. Live hosted demo URL

**URL**: <https://atomquest-goal-management-portal.onrender.com>

Free-tier Render service — first hit after idle may take ~30 sec to spin up. Subsequent hits are instant.

## 3. Architecture diagram

In the repo: <https://github.com/Praneshsivasankaran/atomquest-goal-management-portal/blob/main/docs/architecture.png>

Diagram source: `docs/architecture.md` (Mermaid). PNG was exported via mermaid.live.

## 4. Login credentials (paste verbatim)

```
Employee : employee@demo.com / demo123
Manager  : manager@demo.com  / demo123
Admin/HR : admin@demo.com    / demo123
```

You can also use **Sign up** on the auth screen to create a fresh Employee, Manager, or Admin account.

## 5. Demo script (5-minute walkthrough)

See [`docs/demo-script.md`](demo-script.md). The full script covers one complete journey per role and calls out every bonus screen.

## 6. Features to mention in the submission write-up

### BRD Phase 1 (must-have)
- Goal creation with UoM (Numeric / % / Timeline / Zero-based)
- Weight rules: total = 100%, min 10%, max 8 — server-side `Decimal` validation
- Manager L1 approval with inline edits and "send back for changes"
- Goal lock after approval
- Admin unlock with required audit reason
- Shared goals (recipients edit weight only; primary owner's progress syncs)

### BRD Phase 2 (must-have)
- Quarterly progress capture (Q1–Q4), gated by cycle windows
- System-computed scores for Min / Max / Timeline / Zero UoM
- Manager check-in comments per quarter

### BRD Reporting / Governance
- Achievement export — CSV and valid OOXML Excel
- Completion dashboard with KPIs
- Audit trail (actor, action, entity, before/after snapshot, reason, timestamp)

### BRD §5 Bonus tracks
- **Microsoft Entra ID** — auth seam SSO-ready, OIDC integration documented in upgrade path
- **Email + Teams notifications** — pixel-accurate Outlook email + Microsoft Teams Adaptive Card mockups; integration seams (Entra ID, Teams bot, SMTP/Graph) are env-var-flippable
- **Escalation module** — rule-based escalation events visible to HR
- **Analytics** — QoQ achievement trend, department completion, UoM distribution, department × quarter completion **heatmap**, manager effectiveness

### Polish that goes beyond the BRD
- Salted scrypt password hashing with legacy SHA-256 migration on login
- Per-IP rate limit on `/api/auth/*`
- Origin-based CSRF guard on state-changing endpoints
- `APP_SECRET` startup validation (server refuses to start with demo default on public host)
- IDOR-proof manager endpoints (`assert_manager_owns_sheet` / `assert_manager_owns_goal`)
- Circular and self-manager assignment prevented in org hierarchy
- Timezone-aware cycle windows (Asia/Kolkata) — no off-by-tz boundary bugs on UTC hosts
- Live weight banner with red / yellow / green progress
- Confirmation modals on destructive actions
- Org hierarchy rendered as an expandable reporting tree
- 35 unit tests covering business rules, security, workflows, frontend assertions

## 7. Run locally

```powershell
python app/server.py --port 8000
```

Open <http://localhost:8000>. No dependencies to install — Python standard library only. The demo DB seeds itself on first run.

```powershell
# Reset demo data
python app/server.py --seed-only

# Run tests
python -m unittest discover -s tests
```

## 8. Quick "did everything ship" gate

- [x] All BRD must-haves implemented
- [x] All BRD §5 bonus tracks implemented at varying depths
- [x] GitHub repo public
- [x] Architecture diagram in repo as PNG
- [x] Live URL deployed on Render free tier
- [x] README has demo creds + run instructions
- [x] 35 / 35 tests pass
- [x] CSV + valid OOXML Excel reports
- [x] Audit trail captures workflow actions
