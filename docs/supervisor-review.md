# AtomQuest — Supervisor Review

A prioritized review of the current implementation against the AtomQuest 1.0 problem statement. Use it as a worklist to hand to Codex one slice at a time. Severity tags: **Crit** (fix or judges will see it fail) · **High** (likely to bite during demo) · **Med** (polish that meaningfully shifts judging) · **Low** (nice to have).

---

## 0. Verdict

You're in good shape. The feature checklist is broad: Phase 1, Phase 2, audit logs, shared goals, CSV/XLSX export, analytics, escalation monitor, signup, role-switching demo — all present. Where you can lose points is:

1. A handful of **real bugs** that will only surface under judge probing (manager IDOR, weightage off-by-one, approve-after-edit, demo-mode date hardcode).
2. **Demo-day fragility** (timezones, empty queues, hidden "Open Demo Windows" button).
3. **Visible polish** (empty states, jargon, no confirmations, accessibility cues, no loading states) — every judge will notice.
4. **BRD deliverables** you haven't produced yet (architecture diagram, hosted URL, screenshots).

The fixes are mostly small. If you spend the rest of the time on this list and don't introduce regressions, you should be competitive.

---

## 1. Demo-day blockers — do these first

These are the things most likely to embarrass you in front of judges. Fix in this order.

### 1.1 [Crit] `MAX_GOALS` off-by-one inconsistency
Two places enforce max-8 with different operators:
- `app/storage.py:580` uses `if len(goals) >= 8`
- `app/business.py:77` uses `if len(goals) > 8`

So the create-goal path blocks at 8, but submission validation accepts 8. Inconsistent — and if a judge has exactly 8 goals, the behavior depends on which path runs first.

**Fix**: pull the constant out: `MAX_GOALS_PER_EMPLOYEE = 8` in `business.py`, use `len(goals) >= MAX_GOALS_PER_EMPLOYEE` in both spots, single error message.

### 1.2 [Crit] Manager IDOR — can edit any employee's goals
`app/server.py:168-171` — the `/api/manager/goals/{id}` PATCH only checks `require_role("manager")`. It never confirms the goal belongs to one of *this* manager's reports. Any manager who knows another team's goal IDs can edit them.

**Fix**: in server.py before calling `update_goal`, look up the goal → sheet → employee and assert `employee.manager_id == user["id"]`. Add a test for it. Audit `add_checkin`, `approve_sheet`, `return_sheet`, `manager/sheets/{id}/*` for the same hole.

### 1.3 [Crit] Demo-date hardcoded to `2026-05-18`
`app/server.py:194` — `activate_demo_windows(user["id"], self.read_json().get("today", "2026-05-18"))`. Today is 2026-05-18, so it currently works. The day after submission, the default date is in the past and your "Open Demo Windows" button silently produces a stale window.

**Fix**: default to `date.today().isoformat()` (or pull a helper from `business.py` already used elsewhere). Same call also needs to honour your declared cycle timezone (Asia/Kolkata) — use `zoneinfo.ZoneInfo("Asia/Kolkata")`.

### 1.4 [Crit] Approve sheet doesn't revalidate weightage after manager inline edits
`app/storage.py:664-685` — manager can inline-edit a goal's weightage (e.g. push one from 20 → 35), then approve. Revalidation runs against the goals as loaded earlier, not the post-edit state, so a sheet can lock at 105% total.

**Fix**: in `approve_sheet`, re-fetch goals immediately before validation and lock. Add `tests/test_storage.py` case covering "inline edit breaks total → approve raises DomainError."

### 1.5 [Crit] Weightage rounding can pass invalid totals
`app/business.py:87-88` — `if round(total, 2) != 100` lets `33.33 + 33.33 + 33.34 = 100.00` through, but other float sequences may round to `99.99` or `100.01` and fail unpredictably.

**Fix**: parse each weightage with `Decimal(str(value))` and compare `total == Decimal('100')`. Also enforce integer/whole-percent only at the form layer so the issue can't arise (problem statement implies integer weightage).

### 1.6 [Crit] "Open Demo Windows" button is hidden among export buttons
`public/app.js:946` — the single button judges need to click to enter Phase 2 of the demo lives in the admin hero action row next to two export buttons. Its label is also too internal.

**Fix**: Promote it to its own callout card on the admin dashboard with a label like **"Open all quarters for live demo"** plus one line: *"Temporarily opens Q1–Q4 windows so you can capture progress now."* Use primary button styling. Optional: only show it when no quarter window is currently open.

### 1.7 [Crit] Empty admin dashboard looks broken
If seed data ever fails or anyone resets without re-seeding, all admin tiles show zero / empty rows. Judges will read this as "the app is broken."

**Fix**: in `seed_if_empty`, assert that after running, you have at least one cycle, one admin, one manager, one employee, and at least one demo goal sheet in each state (draft, submitted, locked). Crash loudly on startup if not. Also add a friendly fallback in `app.js` empty-state copy ("Demo data isn't loaded — run `python app/server.py --seed-only`.").

### 1.8 [High] Pending-queue empty state reads as failure
`public/app.js:832` — manager with zero pending reviews sees a plain "No submitted sheets waiting for review." Judges who don't know the workflow will think the feature is broken.

**Fix**: warmer copy + icon: "✅ All caught up. New goal sheets will appear here when employees submit." Then point them at next step: "Head to **Check-ins** to log Q1 feedback." Apply the same treatment to all 8 empty states in `app.js` (around lines 277, 345, 1042, 1147, 1174, 1216).

---

## 2. Bugs & correctness (Phase 1 / Phase 2 workflow)

| # | Severity | File:Line | Issue | Fix |
|---|---|---|---|---|
| 2.1 | High | `app/business.py:125-128` | `direction="max"` scoring uses `target/actual`, so beating a "max" target *lowers* the score. Naming/semantics are inverted vs. typical English ("max throughput" should reward exceeding target). | Either rename to `direction="lower_better"` / `"higher_better"` (clearer), or flip the formula. Update tests and ensure UoM labels in UI match the new semantics. |
| 2.2 | High | `app/storage.py:871-882` | Admin `unlock_sheet` does not re-validate weightage. A previously valid sheet edited via direct DB or future endpoints could unlock in an invalid state. | Revalidate with `validate_goal_sheet(goals)` before completing the unlock. |
| 2.3 | High | `app/storage.py:792-798` | `add_checkin` validates quarter name but not that the quarter's window is open. | Call `ensure_window_open(self.quarter_window(quarter))` before insert. |
| 2.4 | High | `app/business.py:150-160` | `ensure_window_open` uses `date.today()` (local server time) but cycles are stamped `Asia/Kolkata`. A Render server in UTC will be off by 5.5h around boundaries. | Use `datetime.now(ZoneInfo("Asia/Kolkata")).date()`. Surface the cycle TZ in the API response so the frontend can render it. |
| 2.5 | High | `app/storage.py:454-499` | `update_user` allows circular manager assignment (A reports to B, then B reports to A). | Walk the chain before saving; raise `DomainError("Would create reporting cycle")`. |
| 2.6 | High | `app/storage.py:478-487` | User can be set as their own manager (`manager_id == user_id`). | Reject explicitly with a clear message. |
| 2.7 | Med | `app/storage.py:754-755` | Shared-goal `sync_shared_progress` is not transactional under multi-recipient concurrent updates. | Wrap the sync in a `BEGIN IMMEDIATE` … `COMMIT` block; rollback on exception. |
| 2.8 | Med | `app/storage.py:1050-1061` | `activate_demo_windows` updates all windows for the active cycle but doesn't disambiguate when more than one active cycle exists. | Assert single active cycle, or accept `cycle_id` param. |
| 2.9 | Med | `app/storage.py:651-662` | Submit-sheet validates server-side only; if user's clock differs from server's, the "submit" button is enabled when it shouldn't be. | Return window timestamps in `/api/app-state` and gate the button on the client too. |
| 2.10 | Med | `public/app.js:1267-1283` | `formPayload` deletes empty strings before sending, so manager-edits that *clear* a description send nothing — backend treats as "no change." | Distinguish null (no change) from `""` (clear). For now, mark the description field so it always sends a value. |
| 2.11 | Med | `public/app.js:905-912` | `latestProgress(goal)` may return `undefined`; some downstream accesses (e.g. manager check-in render around line 672) assume an object. | Make `latestProgress` always return `{actual_value: null, score: null, status: null}` if no rows. |
| 2.12 | Low | `app/storage.py:558-574` | `audit()` accepts a `reason` parameter, but most call sites omit it. Audit log entries from unlocks include reason; entries from edits don't. | Either make reason required or document what "no reason" means. |
| 2.13 | Low | `app/storage.py:960-961` | Goal-suggestion weightage hint can suggest a value that pushes total over 100 if the user already has 9×10%. | Recompute `remaining = max(0, 100 - used_weight)`, return `null` if no room. |

---

## 3. Security (judges may not probe, but worth doing for cost/architecture marks)

| # | Severity | File:Line | Issue | Fix |
|---|---|---|---|---|
| 3.1 | Crit | `app/auth.py:14` | `SECRET = os.getenv("APP_SECRET", "atomquest-local-demo-secret")` — if env var isn't set on Render, you sign tokens with a public string. | Fail fast at startup if `APP_SECRET` is missing OR equals the demo default *and* the host isn't localhost. |
| 3.2 | High | `app/storage.py:34-35` | Plain SHA-256 password hash, no salt. | Switch to `hashlib.scrypt` (stdlib, no dependency) with per-user salt, or `bcrypt` if you're willing to add a dependency. Migrate existing demo users on next login. |
| 3.3 | High | `app/server.py:95-102` | No rate limiting on `/api/auth/login` or `/api/auth/signup`. | Simple per-IP token bucket in memory (5 attempts / minute). Acceptable for hackathon scale. |
| 3.4 | Med | `app/server.py:54-56` | Generic exception handler returns `str(exc)` to the client (`"detail": str(exc)"`). Leaks tracebacks/IDs. | Log full exception server-side, return `{"error": "Something went wrong"}` only. |
| 3.5 | Med | `app/server.py:45-57` | No CSRF/Origin check on state-changing endpoints. | Check `Origin` header against an allowlist (the configured app URL) for POST/PATCH/DELETE. |
| 3.6 | Med | `app/storage.py:410-427` | No length caps on signup fields. | Cap name/email/title/department/password at sane lengths (255/254/100/100/128). |
| 3.7 | Low | `app/server.py:197-201` | Admin can update *any* admin including themselves — possible to lock yourself out of admin role. | Block self-role-change to a non-admin. |
| 3.8 | Low | `app/server.py:229-241` | Static-file path normalization is OK but consider appending `os.sep` when comparing roots to avoid prefix-overlap bypasses on Windows. | Cosmetic hardening. |

---

## 4. UX polish (highest visibility per minute of effort)

### 4.1 [High] Add confirmations before destructive actions
- Delete goal (`public/app.js:1383-1387`) fires immediately with no prompt.
- Admin "Unlock sheet" already requires a reason — keep that.
- Manager "Return for rework" should show the comment box inline before submitting.

**Fix**: a tiny in-app confirm modal (no `window.confirm`) that takes a goal title and an "Are you sure?" body.

### 4.2 [High] Validation feedback should be inline, not just toasts
Right now invalid weightage fires a single toast at submit time. Add:
- Live total banner above the goal list: **"Total weight: 87% — needs 100%"**, red until 100%, green at 100%.
- Each goal card gets a red border + helper text when its weightage is < 10%.

This is the single biggest UX win for the goal-creation flow — it's the path every employee judge will try.

### 4.3 [High] Replace jargon
- "Weightage" → "Weight %" (global rename in JS strings + table headers).
- "Thrust Area" → "Focus Area" (or keep, but add a tooltip explaining it).
- "Return for Rework" → "Send back for changes."
- "Demo Readiness" (visible in analytics) → move to admin-only or hide outside demo mode.

### 4.4 [High] Accessibility quick wins
- Add `aria-label` to the role-switcher select (`public/app.js:235`) and every `[data-action]` button.
- Add a visible focus ring rule: `.btn:focus-visible, [data-action]:focus-visible { outline: 2px solid var(--brand); outline-offset: 2px; }` in `styles.css`.
- Add a status icon (✅ ⏳ 🔒 ⚠️ ↩️) alongside each status badge so color-blind users can tell them apart.
- Form `<label>`s should be paired to inputs with `for=`/`id=`.

### 4.5 [Med] Loading states for async sections
Every PATCH/POST should disable its button and show a spinner. Analytics panel should show 4 shimmer cards before data loads. Without this, the app feels frozen on slow networks.

### 4.6 [Med] Format audit log timestamps
`public/app.js:1254` renders raw ISO strings. Pipe through `new Date(...).toLocaleString("en-IN", { dateStyle: "medium", timeStyle: "short" })`. Same for any other time displays.

### 4.7 [Med] Manager approval table responsiveness
`public/styles.css:563, 876-882` — table min-width is 760px and only `.org-header` is hidden on mobile. On a smaller projector or 1024px laptop the table scrolls horizontally and the **Approve** button hides off-screen.

**Fix**: on `max-width: 900px`, stack approval cards (one row per goal becomes one card) instead of a table.

### 4.8 [Med] Role switcher should not appear for self-signed-up users
`public/app.js:235-238` — anyone who signs up (not just demo accounts) sees the role switcher; switching tries `password=demo123` and fails. Hide the switcher unless the logged-in email is one of the demo accounts.

### 4.9 [Med] "Smart Goal Assistant" needs an explainer
If suggestions endpoint returns an empty list, the section is just an empty box. Even when it returns data, the user doesn't know it's *deterministic local* and won't think to read the docs.

**Fix**: above the suggestions panel, a one-liner: *"Curated goal templates for your role, generated offline — no AI API needed."*

### 4.10 [Low] Section nav is anchor-links only
`public/app.js:477-482` — clicking nav doesn't smooth-scroll. Add `scroll-behavior: smooth;` to `body`.

---

## 5. BRD coverage check (cross-referenced with problem statement)

Going through the must-haves explicitly:

| BRD requirement | Status | Note |
|---|---|---|
| Employee creates Goal Sheet w/ Thrust Area, Title, Description | ✅ | Confirmed in `public/app.js` form. |
| UoM Numeric/%/Timeline/Zero-based | ✅ | Schema + business rules. Verify Timeline (date) input is wired (#2.10). |
| Total weight = 100%, min 10%/goal, max 8 goals | ⚠️ | Has the off-by-one + rounding bugs (#1.1, #1.5). |
| Manager edit/return/approve workflow | ✅ | But IDOR + post-edit revalidation bugs (#1.2, #1.4). |
| Approval locks goals | ✅ | Lock present; unlock requires admin reason. |
| Shared Goals — admin push, recipients adjust weight only, primary owner syncs achievement | ✅ | Plus a race (#2.7). |
| Quarterly check-in (Q1/Q2/Q3/Q4) | ✅ | Window not enforced on save (#2.3). |
| Manager check-in comment | ✅ | |
| Score formulas (Min/Max/Timeline/Zero) | ⚠️ | Max semantics inverted vs naming (#2.1). |
| Quarterly windows (May / July / Oct / Jan / Mar-Apr) | ⚠️ | Timezone bug (#2.4). |
| Achievement report (CSV/Excel) | ✅ | XLSX is hand-rolled OOXML; works but minimal (#7). |
| Completion dashboard | ✅ | |
| Audit trail of all post-lock changes | ✅ | Indexes missing for scale (#6). |

**Bonus features tracked (judges award extra for these):**

| Bonus | Status |
|---|---|
| Microsoft Entra ID SSO | ❌ Code structure is SSO-ready but no actual integration. Document this explicitly and add a stubbed `/api/auth/sso` 501 endpoint to make the seam visible. |
| Email / Teams notifications | ⚠️ "Preview cards" only. See §7.3 for how to make them look real. |
| Escalation rules (configurable) | ⚠️ Seeded rules only — no admin UI to edit them. |
| Analytics (QoQ trends, heatmap, distribution, manager effectiveness) | ⚠️ Mostly bar charts. Heatmap missing. See §7.4. |

---

## 6. Data & performance

Not judge-visible but cheap insurance:

- Add SQLite indexes (`app/storage.py` schema): `idx_goals_sheet_id`, `idx_goals_shared_goal_id`, `idx_progress_goal_id`, `idx_goal_sheets_user_id`, `idx_checkins_sheet_id`, `idx_audit_entity`, `idx_audit_created_desc`. Otherwise admin dashboards do full table scans.
- Pagination for `/api/admin/...` lists once you exceed a few hundred users.
- Audit log retention — `cleanup_old_escalation_events` task or just a docstring noting the table grows unbounded.

---

## 7. Impressive moves — punch above the weight

These are the things that will make a judge say "wow." Rough cost/impact in parens.

### 7.1 [Huge ROI] Architecture diagram (REQUIRED per BRD §8) — *45 min*
You're missing a deliverable. Make a clean PNG showing: browser → Render web service → SQLite. Annotate the prod upgrade path: PostgreSQL, Entra ID OIDC, background worker for escalations. Use Excalidraw or draw.io.

### 7.2 [Huge ROI] Hosted demo URL (REQUIRED per BRD §8) — *30 min*
Render free-tier with `render.yaml`. If you've not deployed yet, do it now — judges who can't open a URL deduct heavily. Include credentials in the README so judges don't have to email you.

### 7.3 [High ROI] Make the Teams/Email previews look real — *1 h*
Right now the "notification preview" is a card. Upgrade it:
- Email preview: render it as an actual email (From line, Subject, signature, branded header), one CSS block.
- Teams adaptive card: copy the official Adaptive Card design (rounded card, action buttons, "Open in portal" link). Adaptive Cards JSON spec is online; you don't need real Teams, just visual fidelity.

This makes the bonus "Teams/Email integration" land as 80% credible instead of 30%.

### 7.4 [High ROI] Add the heatmap the BRD asks for — *45 min*
BRD §5.4 lists "Heatmaps or progress charts showing completion rates across the organization." You have bar charts. Heatmap = department × quarter grid, colored by completion %. Pure CSS grid with `background: hsl(120, X%, 50%)` based on score. Cheap, looks ML-grade.

### 7.5 [High ROI] First-run product tour — *45 min*
Three small popovers that walk a brand-new user through: 1) goal sheet, 2) submit button, 3) status badge. Use `localStorage.first_run_complete`. Judges who sign up via the signup form get this — and it's the single best signal of "thoughtful product."

### 7.6 [High ROI] Org chart visualization — *45 min*
You have org hierarchy editing but you render it as a flat table. Add a small tree view (nested `<ul>` with CSS connectors — no library needed). This sells the "HR can manage hierarchy" story instantly.

### 7.7 [Med ROI] Presentation mode / projection mode — *30 min*
Toggle that bumps font size, hides side nav, increases contrast. Judges who project on a screen will love it. One CSS class on `<body>` toggled by a button.

### 7.8 [Med ROI] Dark mode — *30 min*
You already have a `prefers-color-scheme` hint in CSS. Add a toggle in the topbar that flips a `data-theme="dark"` attribute and overrides the CSS vars. Demonstrates polish.

### 7.9 [Med ROI] "Reset demo" button — *20 min*
Admin-only button that calls a new `POST /api/admin/reset-demo` endpoint to re-seed. Lets you re-run the demo cleanly between judging sessions. Pair with a confirmation modal.

### 7.10 [Med ROI] Audit log filtering — *30 min*
The audit panel is one long list. Add filter chips (Actor, Entity type, Action). Cheap win, looks enterprise.

### 7.11 [Med ROI] Print-friendly goal sheet — *15 min*
`@media print` block: hides nav, expands content, prints user's goal sheet as a one-pager. HR judges love a printable artifact.

### 7.12 [Low ROI but cute] Keyboard shortcuts — *15 min*
`?` opens a "Keyboard shortcuts" modal. `g s` → goals, `g a` → analytics, `g r` → reports. Adds a power-user vibe.

### 7.13 [Low ROI] PWA installable — *20 min*
Add a `manifest.json` and a tiny service worker. Makes the app installable from Chrome. Judges who install it will remember you.

---

## 8. Tests to add (in priority order)

1. `test_manager_cannot_edit_other_teams_goals` — covers §1.2.
2. `test_max_goals_consistent_between_storage_and_business` — covers §1.1.
3. `test_approve_sheet_revalidates_after_manager_edits` — covers §1.4.
4. `test_weightage_decimal_precision_edge_cases` — covers §1.5.
5. `test_circular_manager_assignment_rejected` — covers §2.5.
6. `test_window_open_on_boundary_dates_with_tz` — covers §2.4.
7. `test_admin_unlock_revalidates` — covers §2.2.
8. `test_xlsx_export_opens_in_zipfile_without_corruption` — covers §7-XLSX validity.

---

## 9. XLSX export — make sure Excel opens it

`app/storage.py:1169-1227` rolls OOXML by hand. The test only checks the bytes start with `PK`. That's not enough. Specific concerns:

- `xl/_rels/workbook.xml.rels` relationship `Type` URI should be the full `http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet` (verify it is).
- Cells should have explicit `t="n"` / `t="str"` attributes (Excel infers; Google Sheets sometimes doesn't).
- Sanitize floats — `NaN` and `Inf` will produce invalid XML and a silent file-open failure.
- Add a header `<dimension ref="A1:Ln"/>` element.

Quickest validation: open the generated file in both Excel and Google Sheets *once*, capture screenshots for the README, and you're done.

---

## 10. Ready-to-paste prompts for Codex

Pick the slice you want and paste this exact text. Each prompt is scoped to be one Codex turn.

### Prompt A — Fix the critical bugs in §1
```
Look at docs/supervisor-review.md sections 1.1 through 1.7. Implement the fixes exactly as described. After each fix, add or update a unittest in tests/ that locks the behaviour in. Run `python -m unittest discover tests` and `python -m py_compile app/auth.py app/business.py app/storage.py app/server.py` before reporting done. Do not refactor anything outside the scope of these seven items.
```

### Prompt B — Fix the manager IDOR + add server-side authorization helpers
```
Implement supervisor-review.md §1.2 and §3.7. Add a helper in app/server.py called `require_manages_employee(manager_id, employee_id)` and `require_owns_sheet(user_id, sheet_id)`. Use them at every manager/* and employee-scoped endpoint that takes an ID. Add tests in tests/test_storage.py that prove a different manager and a different employee both get 403. Do NOT touch UI or styles.
```

### Prompt C — UX polish wave (§4)
```
Apply supervisor-review.md §4.1, §4.2, §4.3, §4.4, §4.6, §4.8 to public/app.js and public/styles.css only. Do not change any backend code. Keep all existing IDs and data-action attributes. After each change, manually verify the relevant flow by running the server and opening the page.
```

### Prompt D — Demo-friendliness pass (§1.6, §1.7, §1.8)
```
Implement supervisor-review.md §1.6, §1.7, §1.8 and §4.5 (loading states). Goal: a judge who opens the app for the first time and switches between Employee, Manager, Admin never sees a confusing empty page. Verify by signing into each demo account and walking through docs/demo-script.md.
```

### Prompt E — Bonus features (§7) — pick three
```
Implement these three items from supervisor-review.md §7:
- §7.3 (real-looking Teams + Email previews)
- §7.4 (department × quarter heatmap on admin analytics)
- §7.6 (org chart tree view replacing the flat table)

Each should be self-contained. Do not break existing analytics. Update docs/demo-script.md to call out the new screens.
```

### Prompt F — Security hardening (§3)
```
Implement supervisor-review.md §3.1, §3.2, §3.3, §3.4, §3.5. The password migration in §3.2 must keep existing demo users working — on next login, if a SHA-256 hash matches, upgrade it to scrypt and rewrite the column. Add tests covering: APP_SECRET missing on startup raises RuntimeError; login fails after 5 attempts/min from the same IP.
```

---

## 11. Submission checklist (cross-check before zipping)

- [ ] All §1 critical bugs fixed and tested
- [ ] Hosted URL live and pingable from a fresh browser
- [ ] GitHub repo public, README has demo creds + screenshots
- [ ] `docs/architecture.png` exists (or `.pdf`)
- [ ] `docs/demo-script.md` walked through end-to-end on the hosted URL
- [ ] `python -m unittest discover tests` passes
- [ ] XLSX export opens in Excel AND Google Sheets without warnings
- [ ] APP_SECRET configured in Render env vars (not the default)
- [ ] Three demo accounts signed in successfully on the hosted URL
- [ ] Demo windows are open OR the "Open Demo Windows" button works on the live site
- [ ] At least 2 bonus features from §7 implemented and visible in the demo

---

*Generated 2026-05-18 by Claude as supervisor over the Codex implementation.*
