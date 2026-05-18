const app = document.querySelector("#app");
const storageKey = "atomquest-token";

let token = localStorage.getItem(storageKey);
let state = null;
let authMode = "signin";

const demoUsers = [
  { role: "Employee", email: "employee@demo.com", password: "demo123" },
  { role: "Manager", email: "manager@demo.com", password: "demo123" },
  { role: "Admin / HR", email: "admin@demo.com", password: "demo123" },
];

const signupRoles = [
  {
    value: "employee",
    label: "Employee",
    title: "Create and track goals",
    copy: "Draft goals, submit for approval, and update quarterly achievements.",
  },
  {
    value: "manager",
    label: "Manager",
    title: "Approve and coach",
    copy: "Review team goals, edit targets, approve sheets, and run check-ins.",
  },
  {
    value: "admin",
    label: "Admin / HR",
    title: "Govern the cycle",
    copy: "Configure windows, unlock exceptions, view reports, and monitor audit logs.",
  },
];

function esc(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

function titleCase(value) {
  return String(value || "").replaceAll("_", " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function initials(name) {
  return String(name || "U")
    .split(" ")
    .map((part) => part[0])
    .join("")
    .slice(0, 2)
    .toUpperCase();
}

function moneyish(value) {
  if (value === null || value === undefined || value === "") return "-";
  return Number(value).toLocaleString("en-IN", { maximumFractionDigits: 2 });
}

function targetText(goal) {
  if (goal.uom_type === "timeline") return `By ${goal.target_date || "-"}`;
  if (goal.uom_type === "percentage") return `${moneyish(goal.target_value)}%`;
  if (goal.uom_type === "zero") return "Target: 0";
  return moneyish(goal.target_value);
}

function latestProgress(goal) {
  return [...(goal.progress || [])].sort((a, b) => String(b.quarter).localeCompare(String(a.quarter)))[0];
}

function showToast(message) {
  const old = document.querySelector(".toast");
  if (old) old.remove();
  const toast = document.createElement("div");
  toast.className = "toast";
  toast.textContent = message;
  document.body.appendChild(toast);
  setTimeout(() => toast.remove(), 4200);
}

async function api(path, options = {}) {
  const headers = { ...(options.headers || {}) };
  if (token) headers.Authorization = `Bearer ${token}`;
  if (options.body && !(options.body instanceof FormData)) {
    headers["Content-Type"] = "application/json";
  }

  const response = await fetch(path, { ...options, headers });
  const contentType = response.headers.get("Content-Type") || "";
  const payload = contentType.includes("application/json") ? await response.json() : await response.text();
  if (!response.ok) {
    throw new Error(payload.error || payload || "Request failed");
  }
  return payload;
}

async function refresh() {
  if (!token) {
    state = null;
    renderLogin();
    return;
  }
  try {
    state = await api("/api/app-state");
    renderApp();
  } catch (error) {
    localStorage.removeItem(storageKey);
    token = null;
    renderLogin();
    showToast(error.message);
  }
}

function renderLogin() {
  const isSignup = authMode === "signup";
  app.innerHTML = `
    <main class="login">
      <section class="login-copy">
        <div>
          <div class="brand-mark"><span class="brand-dot">A</span> AtomQuest</div>
          <h1>Goal clarity for every employee, manager, and HR team.</h1>
          <p>A polished goal management workspace for creation, approval, tracking, shared KPIs, analytics, escalations, and audit-ready governance.</p>
          <div class="auth-proof-grid">
            <div><strong>100%</strong><span>weightage validation</span></div>
            <div><strong>3</strong><span>role-based journeys</span></div>
            <div><strong>Q1-Q4</strong><span>check-in lifecycle</span></div>
          </div>
        </div>
        <p>Built as an enterprise HR-tech MVP with signup, seeded demo profiles, smart goal suggestions, and submission-ready documentation.</p>
      </section>
      <section class="login-panel">
        <div class="login-card">
          <div class="auth-card-head">
            <div>
              <span class="eyebrow">Secure workspace</span>
              <h2>${isSignup ? "Create your account" : "Welcome back"}</h2>
              <p>${isSignup ? "Choose a role and start in the right workspace immediately." : "Sign in with a demo profile or your newly created account."}</p>
            </div>
          </div>
          <div class="auth-tabs">
            <button class="${!isSignup ? "active" : ""}" data-auth-mode="signin">Sign in</button>
            <button class="${isSignup ? "active" : ""}" data-auth-mode="signup">Sign up</button>
          </div>
          ${
            isSignup
              ? `
                <form data-form="signup" class="auth-form">
                  <div class="role-picker">
                    ${signupRoles
                      .map(
                        (role, index) => `
                          <label class="role-card ${index === 0 ? "selected" : ""}">
                            <input type="radio" name="role" value="${role.value}" ${index === 0 ? "checked" : ""} />
                            <span class="role-icon">${role.label.charAt(0)}</span>
                            <strong>${esc(role.label)}</strong>
                            <em>${esc(role.title)}</em>
                            <small>${esc(role.copy)}</small>
                          </label>
                        `,
                      )
                      .join("")}
                  </div>
                  <div class="form-grid">
                    <div class="field">
                      <label>Full Name</label>
                      <input name="name" required placeholder="Aarav Mehta" autocomplete="name" />
                    </div>
                    <div class="field">
                      <label>Work Email</label>
                      <input name="email" type="email" required placeholder="aarav@company.com" autocomplete="email" />
                    </div>
                    <div class="field">
                      <label>Department</label>
                      <select name="department">
                        <option>Sales</option>
                        <option>Customer Success</option>
                        <option>Operations</option>
                        <option>Product</option>
                        <option>People Ops</option>
                      </select>
                    </div>
                    <div class="field">
                      <label>Job Title</label>
                      <input name="title" placeholder="Sales Associate" />
                    </div>
                    <div class="field wide">
                      <label>Password</label>
                      <input name="password" type="password" required minlength="6" placeholder="Minimum 6 characters" autocomplete="new-password" />
                    </div>
                  </div>
                  <button class="btn auth-submit" type="submit">Create Account</button>
                </form>
              `
              : `
                <div class="demo-grid">
                  ${demoUsers
                    .map(
                      (user) => `
                        <button class="demo-user" data-demo-email="${esc(user.email)}">
                          ${esc(user.role)}
                          <span>${esc(user.email)}</span>
                        </button>
                      `,
                    )
                    .join("")}
                </div>
                <form data-form="login" class="auth-form">
                  <div class="field">
                    <label>Email</label>
                    <input name="email" type="email" value="employee@demo.com" required autocomplete="email" />
                  </div>
                  <div class="field">
                    <label>Password</label>
                    <input name="password" type="password" value="demo123" required autocomplete="current-password" />
                  </div>
                  <button class="btn auth-submit" type="submit">Enter Portal</button>
                </form>
              `
          }
        </div>
      </section>
    </main>
  `;
}

function renderApp() {
  const user = state.user;
  app.innerHTML = `
    <div class="app-shell">
      <header class="topbar">
        <div class="topbar-inner">
          <div class="brand-mark"><span class="brand-dot">A</span> Goal Portal</div>
          <div class="actions">
            <select class="role-switch" data-role-switch title="Switch demo role">
              ${demoUsers
                .map((demo) => `<option value="${esc(demo.email)}" ${demo.email === user.email ? "selected" : ""}>${esc(demo.role)}</option>`)
                .join("")}
            </select>
            <div class="user-pill">
              <div class="avatar">${esc(initials(user.name))}</div>
              <div>
                <strong>${esc(user.name)}</strong>
                <span>${esc(titleCase(user.role))} · ${esc(user.department || "Org")}</span>
              </div>
            </div>
            <button class="btn secondary" data-action="logout">Log out</button>
          </div>
        </div>
      </header>
      <main class="workspace">
        ${renderRoleContent()}
      </main>
    </div>
  `;
}

function renderRoleContent() {
  if (state.user.role === "employee") return renderEmployee();
  if (state.user.role === "manager") return renderManager();
  return renderAdmin();
}

function renderMetrics() {
  const metrics = state.metrics || {};
  return `
    <section class="metric-grid">
      <div class="metric"><span>Total Goal Sheets</span><strong>${metrics.total_sheets || 0}</strong></div>
      <div class="metric"><span>Locked / Approved</span><strong>${metrics.locked_sheets || 0}</strong></div>
      <div class="metric"><span>Pending Approval</span><strong>${metrics.submitted_sheets || 0}</strong></div>
      <div class="metric"><span>Completion Rate</span><strong>${metrics.completion_rate || 0}%</strong></div>
    </section>
  `;
}

function renderBarRows(items, mode = "count") {
  if (!items?.length) return `<div class="empty">No analytics data yet.</div>`;
  const max = Math.max(...items.map((item) => Number(item.count || item.total || item.team_sheets || 1)));
  return `
    <div class="bar-list">
      ${items
        .map((item) => {
          const label = item.label || "Unknown";
          let value = Number(item.count || 0);
          let suffix = `${value}`;
          let percent = max ? (value / max) * 100 : 0;
          if (mode === "completion") {
            const total = Number(item.total || 0);
            const complete = Number(item.complete || 0);
            value = total ? Math.round((complete / total) * 100) : 0;
            percent = value;
            suffix = `${value}%`;
          }
          if (mode === "manager") {
            const possible = Number(item.team_sheets || 0) * 4;
            value = possible ? Math.round((Number(item.checkins || 0) / possible) * 100) : 0;
            percent = value;
            suffix = `${value}%`;
          }
          return `
            <div class="bar-row">
              <strong>${esc(titleCase(label))}</strong>
              <div class="progress-bar"><span style="width:${Math.min(percent, 100)}%"></span></div>
              <span>${esc(suffix)}</span>
            </div>
          `;
        })
        .join("")}
    </div>
  `;
}

function renderAnalyticsPanel() {
  const metrics = state.metrics || {};
  return `
    <section class="panel" style="margin-top:18px">
      <h2>Analytics Snapshot</h2>
      <p>Quick charts for the areas judges usually ask about: completion, goal mix, and manager follow-through.</p>
      <div class="grid-three">
        <div>
          <h3>QoQ Achievement Trend</h3>
          ${renderTrend(metrics.quarter_trends || [])}
        </div>
        <div>
          <h3>Goal Distribution</h3>
          ${renderBarRows(metrics.uom_distribution || [])}
        </div>
        <div>
          <h3>Department Completion</h3>
          ${renderBarRows(metrics.department_completion || [], "completion")}
        </div>
      </div>
      <div class="grid-two" style="margin-top:16px">
        <div>
          <h3>Manager Effectiveness</h3>
          ${renderBarRows(metrics.manager_effectiveness || [], "manager")}
        </div>
        ${renderDemoReadiness()}
      </div>
    </section>
  `;
}

function renderTrend(items) {
  if (!items?.length) return `<div class="empty">Quarterly scores appear after progress updates.</div>`;
  return `
    <div class="sparkline">
      ${items
        .map(
          (item) => `
            <div class="sparkline-col">
              <div class="sparkline-bar" style="height:${Math.max(6, Math.min(Number(item.score || 0), 100))}%"></div>
              <strong>${esc(String(item.score || 0))}%</strong>
              <span>${esc(String(item.label || "").toUpperCase())}</span>
            </div>
          `,
        )
        .join("")}
    </div>
  `;
}

function renderDemoReadiness() {
  const items = [
    ["Employee Journey", "Create, validate, submit, and update achievement."],
    ["Manager Journey", "Review, edit, approve, return, and check in."],
    ["Admin Journey", "Cycle windows, shared goals, unlocks, audit, export."],
    ["Bonus Story", "Analytics, escalation monitor, notifications, smart suggestions."],
  ];
  return `
    <div>
      <h3>Demo Readiness</h3>
      <div class="demo-readiness">
        ${items
          .map(
            ([title, body]) => `
              <div class="readiness-item">
                <span class="status locked">Ready</span>
                <div><strong>${esc(title)}</strong><span>${esc(body)}</span></div>
              </div>
            `,
          )
          .join("")}
      </div>
    </div>
  `;
}

function renderNotifications() {
  const notifications = state.notifications || [];
  if (!notifications.length) return "";
  return `
    <section class="panel" style="margin-top:18px">
      <h2>Notification Preview</h2>
      <p>Email and Teams-ready messages are modeled for the bonus workflow without requiring paid services in the demo.</p>
      <div class="notice-grid">
        ${notifications
          .map(
            (item) => `
              <div class="notice">
                <span class="chip">${esc(item.channel)}</span>
                <strong>${esc(item.event)}</strong>
                <span>${esc(item.copy)}</span>
              </div>
            `,
          )
          .join("")}
      </div>
    </section>
  `;
}

function renderCyclePanel() {
  const cycle = state.cycle;
  return `
    <section class="panel">
      <h2>${esc(cycle.name)}</h2>
      <p>Active cycle timezone: ${esc(cycle.timezone)}. Admin can tune windows for live demo and governance needs.</p>
      <div class="grid-three">
        ${cycle.windows
          .map(
            (window) => `
              <div class="goal-card">
                <strong>${esc(window.label)}</strong>
                <div class="goal-meta">
                  <span class="chip">${esc(window.opens_on)}</span>
                  <span class="chip">${esc(window.closes_on)}</span>
                </div>
              </div>
            `,
          )
          .join("")}
      </div>
    </section>
  `;
}

function sheetValidation(sheet) {
  const goals = sheet.goals || [];
  const total = goals.reduce((sum, goal) => sum + Number(goal.weightage || 0), 0);
  return {
    total,
    totalOk: Math.round(total * 100) / 100 === 100,
    minOk: goals.every((goal) => Number(goal.weightage || 0) >= 10),
    maxOk: goals.length <= 8,
    hasGoals: goals.length > 0,
  };
}

function renderValidation(sheet) {
  const check = sheetValidation(sheet);
  const item = (ok, text) => `<div class="validation-item ${ok ? "ok" : "bad"}"><strong>${ok ? "✓" : "!"}</strong><span>${text}</span></div>`;
  return `
    <div class="validation-list">
      ${item(check.totalOk, `Total weightage is ${check.total}%; it must be exactly 100%.`)}
      ${item(check.minOk, "Every goal has at least 10% weightage.")}
      ${item(check.maxOk, "Maximum 8 goals per employee.")}
      ${item(check.hasGoals, "At least one goal exists before submission.")}
    </div>
  `;
}

function renderEmployee() {
  const sheet = state.my_sheet;
  const editable = ["draft", "returned", "unlocked"].includes(sheet.state);
  const lockedEnough = ["locked", "unlocked"].includes(sheet.state);
  return `
    <section class="hero-row">
      <div class="panel">
        <h2>My Goal Sheet</h2>
        <p>${esc(sheet.employee_name)}, your current sheet is <span class="status ${esc(sheet.state)}">${esc(titleCase(sheet.state))}</span>.</p>
        ${sheet.manager_comment ? `<p class="section-note"><strong>Manager note:</strong> ${esc(sheet.manager_comment)}</p>` : ""}
        ${renderValidation(sheet)}
        <div class="actions" style="margin-top:16px">
          <button class="btn" data-action="submit-sheet" ${editable ? "" : "disabled"}>Submit for Approval</button>
          <span class="section-note">Goals lock after manager approval.</span>
        </div>
      </div>
      ${renderCyclePanel()}
    </section>
    ${renderMetrics()}
    ${renderAnalyticsPanel()}
    ${renderNotifications()}
    <section class="grid-two">
      <div class="panel">
        <h2>Add Goal</h2>
        <p>Use measurable targets and keep the full sheet at exactly 100% weightage.</p>
        ${editable ? renderSmartGoalAssistant() + renderGoalForm() : `<div class="empty">This sheet is locked for goal edits.</div>`}
      </div>
      <div class="panel">
        <h2>Goals</h2>
        <p>${sheet.goals.length} of 8 goals added.</p>
        ${sheet.goals.length ? sheet.goals.map((goal) => renderGoalCard(goal, editable)).join("") : `<div class="empty">No goals added yet.</div>`}
      </div>
    </section>
    <section class="panel" style="margin-top:18px">
      <h2>Quarterly Achievement Updates</h2>
      <p>Progress capture is allowed only during the configured quarterly window.</p>
      ${lockedEnough ? sheet.goals.map(renderProgressCard).join("") : `<div class="empty">Progress opens after manager approval locks the goal sheet.</div>`}
    </section>
  `;
}

function renderSmartGoalAssistant() {
  return `
    <div class="goal-card">
      <div class="goal-head">
        <div>
          <h3>Smart Goal Assistant</h3>
          <p>Offline suggestions based on your role, department, and remaining weightage.</p>
        </div>
        <button class="btn secondary" data-action="load-suggestions">Suggest Goals</button>
      </div>
      <div id="suggestions-root" class="grid-two"></div>
    </div>
  `;
}

function renderGoalForm() {
  return `
    <form data-form="create-goal">
      <div class="form-grid">
        <div class="field">
          <label>Thrust Area</label>
          <input name="thrust_area" required placeholder="Revenue Growth" />
        </div>
        <div class="field">
          <label>Goal Title</label>
          <input name="title" required placeholder="Increase enterprise sales revenue" />
        </div>
        <div class="field wide">
          <label>Description</label>
          <textarea name="description" placeholder="A short, practical note about the goal."></textarea>
        </div>
        <div class="field">
          <label>UoM</label>
          <select name="uom_type" data-uom-select>
            <option value="numeric">Numeric</option>
            <option value="percentage">Percentage</option>
            <option value="timeline">Timeline</option>
            <option value="zero">Zero-based</option>
          </select>
        </div>
        <div class="field">
          <label>Scoring Direction</label>
          <select name="direction">
            <option value="min">Higher is better</option>
            <option value="max">Lower is better</option>
            <option value="timeline">Timeline deadline</option>
            <option value="zero">Zero means success</option>
          </select>
        </div>
        <div class="field">
          <label>Target Value</label>
          <input name="target_value" type="number" step="0.01" placeholder="1000000" />
        </div>
        <div class="field">
          <label>Target Date</label>
          <input name="target_date" type="date" />
        </div>
        <div class="field">
          <label>Weightage %</label>
          <input name="weightage" type="number" min="10" max="100" step="1" required value="10" />
        </div>
      </div>
      <button class="btn" type="submit">Add Goal</button>
    </form>
  `;
}

function renderGoalCard(goal, editable) {
  const shared = Boolean(goal.shared_goal_id);
  const progress = latestProgress(goal);
  return `
    <article class="goal-card">
      <div class="goal-head">
        <div>
          <h3>${esc(goal.title)} ${shared ? `<span class="chip">Shared KPI</span>` : ""}</h3>
          <p>${esc(goal.description || "No description added.")}</p>
          <div class="goal-meta">
            <span class="chip">${esc(goal.thrust_area)}</span>
            <span class="chip">${esc(titleCase(goal.uom_type))}</span>
            <span class="chip">${esc(targetText(goal))}</span>
            <span class="chip">${Number(goal.weightage)}%</span>
          </div>
        </div>
        ${
          progress
            ? `<div style="min-width:130px"><strong>${progress.score}%</strong><div class="progress-bar"><span style="width:${Math.min(progress.score, 100)}%"></span></div></div>`
            : ""
        }
      </div>
      ${
        editable
          ? `
            <form data-form="update-goal" data-goal-id="${goal.id}">
              <div class="form-grid">
                <div class="field ${shared ? "wide" : ""}">
                  <label>Weightage %</label>
                  <input name="weightage" type="number" min="10" max="100" step="1" value="${esc(goal.weightage)}" />
                </div>
                ${
                  shared
                    ? `<div class="section-note">Shared goals keep title and target read-only. You can tune only the weightage.</div>`
                    : `
                      <div class="field">
                        <label>Target Value</label>
                        <input name="target_value" type="number" step="0.01" value="${esc(goal.target_value ?? "")}" />
                      </div>
                      <div class="field">
                        <label>Target Date</label>
                        <input name="target_date" type="date" value="${esc(goal.target_date ?? "")}" />
                      </div>
                      <div class="field wide">
                        <label>Description</label>
                        <textarea name="description">${esc(goal.description || "")}</textarea>
                      </div>
                    `
                }
              </div>
              <div class="actions">
                <button class="btn secondary" type="submit">Save</button>
                ${shared ? "" : `<button class="btn danger" type="button" data-action="delete-goal" data-goal-id="${goal.id}">Delete</button>`}
              </div>
            </form>
          `
          : ""
      }
    </article>
  `;
}

function renderProgressCard(goal) {
  const progress = goal.progress || [];
  const shared = Boolean(goal.shared_goal_id);
  return `
    <article class="goal-card">
      <div class="goal-head">
        <div>
          <h3>${esc(goal.title)}</h3>
          <p>Target: ${esc(targetText(goal))} · Weightage ${Number(goal.weightage)}%</p>
        </div>
        ${shared ? `<span class="chip">Linked progress</span>` : ""}
      </div>
      <form data-form="progress" data-goal-id="${goal.id}">
        <div class="form-grid">
          <div class="field">
            <label>Quarter</label>
            <select name="quarter">
              <option value="q1">Q1</option>
              <option value="q2">Q2</option>
              <option value="q3">Q3</option>
              <option value="q4">Q4</option>
            </select>
          </div>
          <div class="field">
            <label>Status</label>
            <select name="status">
              <option value="not_started">Not Started</option>
              <option value="on_track" selected>On Track</option>
              <option value="completed">Completed</option>
            </select>
          </div>
          <div class="field">
            <label>Actual Value</label>
            <input name="actual_value" type="number" step="0.01" placeholder="700000" />
          </div>
          <div class="field">
            <label>Completion Date</label>
            <input name="completion_date" type="date" />
          </div>
          <div class="field wide">
            <label>Notes</label>
            <textarea name="notes" placeholder="Quick progress context for manager review."></textarea>
          </div>
        </div>
        <button class="btn secondary" type="submit">Save Progress</button>
      </form>
      ${
        progress.length
          ? `
            <div class="table-wrap" style="margin-top:12px">
              <table>
                <thead><tr><th>Quarter</th><th>Actual</th><th>Status</th><th>Score</th><th>Notes</th></tr></thead>
                <tbody>
                  ${progress
                    .map(
                      (item) => `
                        <tr>
                          <td>${esc(item.quarter.toUpperCase())}</td>
                          <td>${esc(item.actual_value ?? item.completion_date ?? "-")}</td>
                          <td><span class="status ${esc(item.status)}">${esc(titleCase(item.status))}</span></td>
                          <td>${esc(item.score)}%</td>
                          <td>${esc(item.notes || "-")}</td>
                        </tr>
                      `,
                    )
                    .join("")}
                </tbody>
              </table>
            </div>
          `
          : ""
      }
    </article>
  `;
}

function renderManager() {
  const approvals = state.approvals || [];
  const team = state.team_sheets || [];
  return `
    <section class="hero-row">
      <div class="panel">
        <h2>Manager Workspace</h2>
        <p>Review submitted goals, tune targets or weightage, approve clean sheets, and document quarterly check-ins.</p>
        <div class="actions">
          <span class="status submitted">${approvals.length} Pending Approvals</span>
          <button class="btn secondary" data-action="export-report">Export Achievement CSV</button>
        </div>
      </div>
      ${renderCyclePanel()}
    </section>
    ${renderMetrics()}
    ${renderAnalyticsPanel()}
    ${renderNotifications()}
    <section class="panel">
      <h2>Approval Queue</h2>
      <p>Inline edits are available only while a sheet is submitted for review.</p>
      ${approvals.length ? approvals.map(renderApprovalSheet).join("") : `<div class="empty">No submitted sheets waiting for review.</div>`}
    </section>
    <section class="panel" style="margin-top:18px">
      <h2>Team Check-ins</h2>
      <p>Track planned vs actual and leave structured manager feedback.</p>
      ${team.length ? team.map(renderTeamSheet).join("") : `<div class="empty">No team members assigned.</div>`}
    </section>
  `;
}

function renderApprovalSheet(sheet) {
  return `
    <article class="goal-card">
      <div class="goal-head">
        <div>
          <h3>${esc(sheet.employee_name)}</h3>
          <p>${esc(sheet.department)} · ${sheet.goals.length} goals · <span class="status ${esc(sheet.state)}">${esc(titleCase(sheet.state))}</span></p>
        </div>
        <div class="actions">
          <button class="btn" data-action="approve-sheet" data-sheet-id="${sheet.id}">Approve & Lock</button>
        </div>
      </div>
      <div class="table-wrap">
        <table>
          <thead><tr><th>Goal</th><th>Target</th><th>Weightage</th><th>Manager Edit</th></tr></thead>
          <tbody>
            ${sheet.goals
              .map(
                (goal) => `
                  <tr>
                    <td><strong>${esc(goal.title)}</strong><br /><small>${esc(goal.description || "")}</small></td>
                    <td>
                      <input data-manager-goal="${goal.id}" data-field="target_value" type="number" step="0.01" value="${esc(goal.target_value ?? "")}" />
                      <input data-manager-goal="${goal.id}" data-field="target_date" type="date" value="${esc(goal.target_date ?? "")}" style="margin-top:8px" />
                    </td>
                    <td><input data-manager-goal="${goal.id}" data-field="weightage" type="number" min="10" max="100" value="${esc(goal.weightage)}" /></td>
                    <td><button class="btn secondary" data-action="manager-save-goal" data-goal-id="${goal.id}">Save Row</button></td>
                  </tr>
                `,
              )
              .join("")}
          </tbody>
        </table>
      </div>
      <form data-form="return-sheet" data-sheet-id="${sheet.id}" style="margin-top:12px">
        <div class="field">
          <label>Return for Rework Comment</label>
          <textarea name="comment" placeholder="Please rebalance the weightage and clarify target ownership."></textarea>
        </div>
        <button class="btn secondary" type="submit">Return for Rework</button>
      </form>
    </article>
  `;
}

function renderTeamSheet(sheet) {
  return `
    <article class="goal-card">
      <div class="goal-head">
        <div>
          <h3>${esc(sheet.employee_name)}</h3>
          <p>${esc(sheet.employee_email)} · <span class="status ${esc(sheet.state)}">${esc(titleCase(sheet.state))}</span></p>
        </div>
      </div>
      <div class="table-wrap">
        <table>
          <thead><tr><th>Goal</th><th>Planned</th><th>Latest Actual</th><th>Status</th><th>Score</th></tr></thead>
          <tbody>
            ${sheet.goals
              .map((goal) => {
                const progress = latestProgress(goal);
                return `
                  <tr>
                    <td>${esc(goal.title)}</td>
                    <td>${esc(targetText(goal))}</td>
                    <td>${esc(progress?.actual_value ?? progress?.completion_date ?? "-")}</td>
                    <td>${progress ? `<span class="status ${esc(progress.status)}">${esc(titleCase(progress.status))}</span>` : "-"}</td>
                    <td>${progress ? `${esc(progress.score)}%` : "-"}</td>
                  </tr>
                `;
              })
              .join("")}
          </tbody>
        </table>
      </div>
      <form data-form="checkin" data-sheet-id="${sheet.id}" style="margin-top:12px">
        <div class="form-grid">
          <div class="field">
            <label>Quarter</label>
            <select name="quarter"><option value="q1">Q1</option><option value="q2">Q2</option><option value="q3">Q3</option><option value="q4">Q4</option></select>
          </div>
          <div class="field wide">
            <label>Check-in Comment</label>
            <textarea name="comment" required placeholder="Good progress overall; next focus is delivery consistency."></textarea>
          </div>
        </div>
        <button class="btn secondary" type="submit">Save Check-in</button>
      </form>
    </article>
  `;
}

function renderAdmin() {
  return `
    <section class="hero-row">
      <div class="panel">
        <h2>Admin / HR Control Center</h2>
        <p>Configure cycles, push shared KPIs, unlock exceptions, export reports, and inspect the audit trail.</p>
        <div class="actions">
          <button class="btn" data-action="export-report">Export Achievement CSV</button>
          <button class="btn secondary" data-action="demo-mode">Open Demo Windows</button>
          <span class="status locked">${state.metrics.completion_rate}% Complete</span>
        </div>
      </div>
      ${renderCyclePanel()}
    </section>
    ${renderMetrics()}
    ${renderAnalyticsPanel()}
    ${renderNotifications()}
    <section class="grid-two">
      <div class="panel">
        <h2>Cycle Windows</h2>
        <p>Adjust windows when you need to demo quarterly capture during the hackathon.</p>
        ${state.cycle.windows.map(renderWindowForm).join("")}
      </div>
      <div class="panel">
        <h2>Create Shared Goal</h2>
        <p>Title and target stay read-only for recipients; only weightage is editable.</p>
        ${renderSharedGoalForm()}
      </div>
    </section>
    <section class="panel" style="margin-top:18px">
      <h2>Goal Sheet Exceptions</h2>
      <p>Admin unlocks are logged with reason and timestamp.</p>
      ${renderAdminSheets()}
    </section>
    <section class="panel" style="margin-top:18px">
      <h2>Escalation Monitor</h2>
      <p>Rule-based escalation events are visible to HR for follow-up.</p>
      ${renderEscalations()}
    </section>
    <section class="panel" style="margin-top:18px">
      <h2>Audit Trail</h2>
      <p>Every meaningful workflow change is stored for governance review.</p>
      ${renderAuditLog()}
    </section>
  `;
}

function renderEscalations() {
  const events = state.escalation_events || [];
  if (!events.length) return `<div class="empty">No escalation events are open.</div>`;
  return `
    <div class="table-wrap">
      <table>
        <thead><tr><th>Rule</th><th>Employee</th><th>Status</th><th>Message</th></tr></thead>
        <tbody>
          ${events
            .map(
              (event) => `
                <tr>
                  <td>${esc(event.rule_name)}</td>
                  <td>${esc(event.employee_name || "-")}</td>
                  <td><span class="status submitted">${esc(titleCase(event.status))}</span></td>
                  <td>${esc(event.message)}</td>
                </tr>
              `,
            )
            .join("")}
        </tbody>
      </table>
    </div>
  `;
}

function renderWindowForm(window) {
  return `
    <form data-form="window" data-phase="${esc(window.phase)}" class="goal-card">
      <strong>${esc(window.label)}</strong>
      <div class="form-grid" style="margin-top:12px">
        <div class="field">
          <label>Opens</label>
          <input name="opens_on" type="date" value="${esc(window.opens_on)}" />
        </div>
        <div class="field">
          <label>Closes</label>
          <input name="closes_on" type="date" value="${esc(window.closes_on)}" />
        </div>
      </div>
      <button class="btn secondary" type="submit">Update Window</button>
    </form>
  `;
}

function renderSharedGoalForm() {
  return `
    <form data-form="shared-goal">
      <div class="form-grid">
        <div class="field">
          <label>Thrust Area</label>
          <input name="thrust_area" required value="Customer Quality" />
        </div>
        <div class="field">
          <label>Goal Title</label>
          <input name="title" required value="Reduce customer complaints by 20%" />
        </div>
        <div class="field wide">
          <label>Description</label>
          <textarea name="description">Shared department KPI for improving customer experience.</textarea>
        </div>
        <div class="field">
          <label>UoM</label>
          <select name="uom_type"><option value="percentage">Percentage</option><option value="numeric">Numeric</option><option value="timeline">Timeline</option><option value="zero">Zero-based</option></select>
        </div>
        <div class="field">
          <label>Direction</label>
          <select name="direction"><option value="min">Higher is better</option><option value="max" selected>Lower is better</option><option value="timeline">Timeline</option><option value="zero">Zero means success</option></select>
        </div>
        <div class="field">
          <label>Target Value</label>
          <input name="target_value" type="number" step="0.01" value="20" />
        </div>
        <div class="field">
          <label>Default Weightage</label>
          <input name="default_weightage" type="number" min="10" value="10" />
        </div>
        <div class="field wide">
          <label>Primary Owner</label>
          <select name="primary_owner_id">
            ${state.employees.map((employee) => `<option value="${employee.id}">${esc(employee.name)}</option>`).join("")}
          </select>
        </div>
        <div class="field wide">
          <label>Recipients</label>
          <div class="grid-three">
            ${state.employees
              .map(
                (employee) => `
                  <label class="chip" style="justify-content:flex-start">
                    <input type="checkbox" name="recipient_ids" value="${employee.id}" checked style="width:auto" />
                    ${esc(employee.name)}
                  </label>
                `,
              )
              .join("")}
          </div>
        </div>
      </div>
      <button class="btn" type="submit">Push Shared Goal</button>
    </form>
  `;
}

function renderAdminSheets() {
  const sheets = state.all_sheets || [];
  if (!sheets.length) return `<div class="empty">No employee sheets yet.</div>`;
  return `
    <div class="table-wrap">
      <table>
        <thead><tr><th>Employee</th><th>State</th><th>Goals</th><th>Unlock</th></tr></thead>
        <tbody>
          ${sheets
            .map(
              (sheet) => `
                <tr>
                  <td><strong>${esc(sheet.employee_name)}</strong><br /><small>${esc(sheet.employee_email)}</small></td>
                  <td><span class="status ${esc(sheet.state)}">${esc(titleCase(sheet.state))}</span></td>
                  <td>${sheet.goals.length}</td>
                  <td>
                    <form data-form="unlock" data-sheet-id="${sheet.id}" class="actions">
                      <input name="reason" placeholder="Reason for unlock" />
                      <button class="btn secondary" type="submit">Unlock</button>
                    </form>
                  </td>
                </tr>
              `,
            )
            .join("")}
        </tbody>
      </table>
    </div>
  `;
}

function renderAuditLog() {
  const logs = state.audit_logs || [];
  if (!logs.length) return `<div class="empty">No audit events yet.</div>`;
  return logs
    .map(
      (log) => `
        <div class="audit-row">
          <div>
            <strong>${esc(log.actor_name)}</strong>
            <small>${esc(log.created_at)}</small>
          </div>
          <div>
            <strong>${esc(titleCase(log.action))}</strong>
            <small>${esc(log.entity_type)} #${esc(log.entity_id)} ${log.reason ? `· ${esc(log.reason)}` : ""}</small>
          </div>
          <div><span class="chip">${esc(log.entity_type)}</span></div>
        </div>
      `,
    )
    .join("");
}

function formPayload(form) {
  const data = new FormData(form);
  const payload = {};
  for (const [key, value] of data.entries()) {
    if (key === "recipient_ids") continue;
    payload[key] = value;
  }
  if (form.querySelectorAll('[name="recipient_ids"]').length) {
    payload.recipient_ids = [...form.querySelectorAll('[name="recipient_ids"]:checked')].map((input) => Number(input.value));
  }
  for (const key of ["weightage", "target_value", "default_weightage", "primary_owner_id", "actual_value", "manager_id"]) {
    if (payload[key] !== undefined && payload[key] !== "") payload[key] = Number(payload[key]);
  }
  for (const key of Object.keys(payload)) {
    if (payload[key] === "") delete payload[key];
  }
  return payload;
}

async function handleSubmit(event) {
  const form = event.target.closest("form");
  if (!form?.dataset.form) return;
  event.preventDefault();

  try {
    const kind = form.dataset.form;
    const payload = formPayload(form);
    if (kind === "login") {
      const result = await api("/api/auth/login", { method: "POST", body: JSON.stringify(payload) });
      token = result.token;
      localStorage.setItem(storageKey, token);
      showToast(`Welcome, ${result.user.name}`);
      return refresh();
    }
    if (kind === "signup") {
      const result = await api("/api/auth/signup", { method: "POST", body: JSON.stringify(payload) });
      token = result.token;
      localStorage.setItem(storageKey, token);
      showToast(`Account created for ${result.user.name}`);
      return refresh();
    }
    if (kind === "create-goal") {
      await api("/api/goals", { method: "POST", body: JSON.stringify(payload) });
      showToast("Goal added");
    }
    if (kind === "update-goal") {
      await api(`/api/goals/${form.dataset.goalId}`, { method: "PATCH", body: JSON.stringify(payload) });
      showToast("Goal updated");
    }
    if (kind === "progress") {
      await api(`/api/goals/${form.dataset.goalId}/progress`, { method: "POST", body: JSON.stringify(payload) });
      showToast("Progress saved");
    }
    if (kind === "return-sheet") {
      await api(`/api/manager/sheets/${form.dataset.sheetId}/return`, { method: "POST", body: JSON.stringify(payload) });
      showToast("Goal sheet returned for rework");
    }
    if (kind === "checkin") {
      await api(`/api/manager/sheets/${form.dataset.sheetId}/checkins`, { method: "POST", body: JSON.stringify(payload) });
      showToast("Check-in saved");
    }
    if (kind === "shared-goal") {
      await api("/api/admin/shared-goals", { method: "POST", body: JSON.stringify(payload) });
      showToast("Shared goal pushed to employees");
    }
    if (kind === "unlock") {
      await api(`/api/admin/sheets/${form.dataset.sheetId}/unlock`, { method: "POST", body: JSON.stringify(payload) });
      showToast("Goal sheet unlocked");
    }
    if (kind === "window") {
      await api(`/api/admin/windows/${form.dataset.phase}`, { method: "PATCH", body: JSON.stringify(payload) });
      showToast("Cycle window updated");
    }
    await refresh();
  } catch (error) {
    showToast(error.message);
  }
}

async function handleClick(event) {
  const modeButton = event.target.closest("[data-auth-mode]");
  if (modeButton) {
    authMode = modeButton.dataset.authMode;
    renderLogin();
    return;
  }

  const demo = event.target.closest("[data-demo-email]");
  if (demo) {
    const email = demo.dataset.demoEmail;
    const form = document.querySelector('[data-form="login"]');
    form.email.value = email;
    form.password.value = "demo123";
    form.requestSubmit();
    return;
  }

  const action = event.target.closest("[data-action]");
  if (!action) return;

  try {
    if (action.dataset.action === "logout") {
      localStorage.removeItem(storageKey);
      token = null;
      state = null;
      renderLogin();
    }
    if (action.dataset.action === "submit-sheet") {
      await api("/api/goal-sheet/submit", { method: "POST", body: JSON.stringify({}) });
      showToast("Goal sheet submitted to manager");
      await refresh();
    }
    if (action.dataset.action === "delete-goal") {
      await api(`/api/goals/${action.dataset.goalId}`, { method: "DELETE" });
      showToast("Goal deleted");
      await refresh();
    }
    if (action.dataset.action === "load-suggestions") {
      const result = await api("/api/goals/suggestions");
      const root = document.querySelector("#suggestions-root");
      root.innerHTML = result.suggestions
        .map(
          (goal) => `
            <div class="notice">
              <span class="chip">${esc(goal.thrust_area)}</span>
              <strong>${esc(goal.title)}</strong>
              <span>${esc(goal.fit_reason)}</span>
              <div class="goal-meta">
                <span class="chip">${esc(titleCase(goal.uom_type))}</span>
                <span class="chip">${esc(goal.target_value ?? goal.target_date ?? "0")}</span>
                <span class="chip">${esc(goal.weightage)}%</span>
              </div>
              <button class="btn secondary" style="margin-top:12px" data-action="use-suggestion" data-goal="${encodeURIComponent(JSON.stringify(goal))}">Use This</button>
            </div>
          `,
        )
        .join("");
      showToast("Smart suggestions loaded");
    }
    if (action.dataset.action === "use-suggestion") {
      const goal = JSON.parse(decodeURIComponent(action.dataset.goal));
      const form = document.querySelector('[data-form="create-goal"]');
      for (const [key, value] of Object.entries(goal)) {
        if (form.elements[key]) form.elements[key].value = value ?? "";
      }
      showToast("Suggestion copied into the goal form");
    }
    if (action.dataset.action === "approve-sheet") {
      await api(`/api/manager/sheets/${action.dataset.sheetId}/approve`, { method: "POST", body: JSON.stringify({}) });
      showToast("Goal sheet approved and locked");
      await refresh();
    }
    if (action.dataset.action === "manager-save-goal") {
      const goalId = action.dataset.goalId;
      const inputs = [...document.querySelectorAll(`[data-manager-goal="${goalId}"]`)];
      const payload = {};
      inputs.forEach((input) => {
        if (input.value !== "") payload[input.dataset.field] = input.type === "number" ? Number(input.value) : input.value;
      });
      await api(`/api/manager/goals/${goalId}`, { method: "PATCH", body: JSON.stringify(payload) });
      showToast("Manager edit saved");
      await refresh();
    }
    if (action.dataset.action === "export-report") {
      const response = await fetch("/api/reports/achievement.csv", { headers: { Authorization: `Bearer ${token}` } });
      if (!response.ok) throw new Error("Could not export report");
      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = "achievement-report.csv";
      link.click();
      URL.revokeObjectURL(url);
      showToast("Achievement report downloaded");
    }
    if (action.dataset.action === "demo-mode") {
      await api("/api/admin/demo-mode", { method: "POST", body: JSON.stringify({ today: new Date().toISOString().slice(0, 10) }) });
      showToast("All cycle windows are open for demo");
      await refresh();
    }
  } catch (error) {
    showToast(error.message);
  }
}

document.addEventListener("submit", handleSubmit);
document.addEventListener("click", handleClick);
document.addEventListener("change", async (event) => {
  const switcher = event.target.closest("[data-role-switch]");
  if (!switcher) return;
  const demo = demoUsers.find((item) => item.email === switcher.value);
  if (!demo) return;
  try {
    const result = await api("/api/auth/login", {
      method: "POST",
      body: JSON.stringify({ email: demo.email, password: demo.password }),
    });
    token = result.token;
    localStorage.setItem(storageKey, token);
    showToast(`Switched to ${demo.role}`);
    await refresh();
  } catch (error) {
    showToast(error.message);
  }
});

// Keep the boot path boring and quick. The real work happens after app-state loads.
refresh();
