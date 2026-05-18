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
          <div class="auth-topline">
            <div class="brand-mark"><span class="brand-dot">A</span> AtomQuest</div>
            <span class="auth-badge">Goal OS for HR teams</span>
          </div>
          <h1>Run employee goals from draft to appraisal without spreadsheet chaos.</h1>
          <p>A polished workspace for goal creation, approvals, quarterly achievement tracking, shared KPIs, analytics, escalations, and audit-ready governance.</p>
          <div class="auth-proof-grid">
            <div><strong>100%</strong><span>weightage validation</span></div>
            <div><strong>3</strong><span>role-based journeys</span></div>
            <div><strong>Q1-Q4</strong><span>check-in lifecycle</span></div>
          </div>
          <div class="auth-showcase">
            <div>
              <span>Current Cycle</span>
              <strong>FY 2026 Goal Cycle</strong>
            </div>
            <div>
              <span>Approval Queue</span>
              <strong>2 waiting</strong>
            </div>
            <div>
              <span>Completion</span>
              <strong>64%</strong>
            </div>
          </div>
        </div>
        <div class="auth-feature-list">
          <span>Manager approval</span>
          <span>Shared goals</span>
          <span>Audit trail</span>
          <span>Excel reports</span>
        </div>
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
                  <p class="auth-footnote">New Employee accounts start with a draft goal sheet. Manager and Admin accounts open directly into their workspace.</p>
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
                  <p class="auth-footnote">Tip: use the role cards above for a fast judge demo, or create a fresh account from Sign up.</p>
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
                <span>${esc(titleCase(user.role))} &middot; ${esc(user.department || "Org")}</span>
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
  const item = (ok, text) => `<div class="validation-item ${ok ? "ok" : "bad"}"><strong>${ok ? "OK" : "!"}</strong><span>${text}</span></div>`;
  return `
    <div class="validation-list">
      ${item(check.totalOk, `Total weightage is ${check.total}%; it must be exactly 100%.`)}
      ${item(check.minOk, "Every goal has at least 10% weightage.")}
      ${item(check.maxOk, "Maximum 8 goals per employee.")}
      ${item(check.hasGoals, "At least one goal exists before submission.")}
    </div>
  `;
}

function renderWorkspaceHero({ eyebrow, title, subtitle, actions = "", meta = "" }) {
  return `
    <section class="workspace-hero">
      <div>
        <span class="eyebrow">${esc(eyebrow)}</span>
        <h1>${esc(title)}</h1>
        <p>${esc(subtitle)}</p>
        ${meta ? `<div class="hero-meta">${meta}</div>` : ""}
      </div>
      <div class="hero-actions">${actions}</div>
    </section>
  `;
}

function renderSectionNav(items) {
  return `
    <nav class="section-nav" aria-label="Dashboard sections">
      ${items.map((item) => `<a href="#${esc(item.href)}">${esc(item.label)}</a>`).join("")}
    </nav>
  `;
}

function renderQuickActions(items) {
  return `
    <section class="quick-actions">
      ${items
        .map(
          (item) => `
            <a class="quick-action" href="#${esc(item.href)}">
              <span>${esc(item.kicker)}</span>
              <strong>${esc(item.title)}</strong>
              <em>${esc(item.body)}</em>
            </a>
          `,
        )
        .join("")}
    </section>
  `;
}

function renderWorkflowRail(currentState) {
  const steps = [
    ["draft", "Draft goals"],
    ["submitted", "Manager review"],
    ["locked", "Locked sheet"],
    ["progress", "Quarterly updates"],
  ];
  const normalized = currentState === "returned" || currentState === "unlocked" ? "draft" : currentState;
  const activeIndex = Math.max(0, steps.findIndex(([key]) => key === normalized));
  return `
    <div class="workflow-rail">
      ${steps
        .map(
          ([, label], index) => `
            <div class="workflow-step ${index <= activeIndex ? "done" : ""} ${index === activeIndex ? "active" : ""}">
              <span>${index + 1}</span>
              <strong>${esc(label)}</strong>
            </div>
          `,
        )
        .join("")}
    </div>
  `;
}

function renderEmployee() {
  const sheet = state.my_sheet;
  const editable = ["draft", "returned", "unlocked"].includes(sheet.state);
  const lockedEnough = ["locked", "unlocked"].includes(sheet.state);
  return `
    ${renderWorkspaceHero({
      eyebrow: "Employee workspace",
      title: "Build a clean, approval-ready goal sheet",
      subtitle: "Create measurable goals, keep weightage balanced, and move smoothly into quarterly achievement tracking.",
      actions: `
        <button class="btn" data-action="submit-sheet" ${editable ? "" : "disabled"}>Submit for Approval</button>
        <a class="btn secondary" href="#progress">Quarterly Updates</a>
      `,
      meta: `<span class="status ${esc(sheet.state)}">${esc(titleCase(sheet.state))}</span><span>${esc(sheet.employee_name)}</span><span>${sheet.goals.length}/8 goals</span>`,
    })}
    ${renderSectionNav([
      { href: "overview", label: "Overview" },
      { href: "goals", label: "Goals" },
      { href: "progress", label: "Progress" },
      { href: "analytics", label: "Analytics" },
    ])}
    ${renderQuickActions([
      { href: "goals", kicker: "Next", title: "Balance goal weightage", body: "Hit exactly 100% before submission." },
      { href: "assistant", kicker: "Assist", title: "Use smart suggestions", body: "Draft relevant goals faster." },
      { href: "progress", kicker: "Later", title: "Update achievement", body: "Capture actuals during open windows." },
    ])}
    <section class="hero-row" id="overview">
      <div class="panel panel-accent">
        <h2>Goal Sheet Health</h2>
        <p>Your current sheet is <span class="status ${esc(sheet.state)}">${esc(titleCase(sheet.state))}</span>.</p>
        ${sheet.manager_comment ? `<p class="section-note"><strong>Manager note:</strong> ${esc(sheet.manager_comment)}</p>` : ""}
        ${renderWorkflowRail(sheet.state)}
        ${renderValidation(sheet)}
      </div>
      ${renderCyclePanel()}
    </section>
    ${renderMetrics()}
    <div id="analytics">${renderAnalyticsPanel()}</div>
    ${renderNotifications()}
    <section class="grid-two" id="goals">
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
    <section class="panel" style="margin-top:18px" id="progress">
      <h2>Quarterly Achievement Updates</h2>
      <p>Progress capture is allowed only during the configured quarterly window.</p>
      ${lockedEnough ? sheet.goals.map(renderProgressCard).join("") : `<div class="empty">Progress opens after manager approval locks the goal sheet.</div>`}
    </section>
  `;
}

function renderSmartGoalAssistant() {
  return `
    <div class="goal-card" id="assistant">
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
          <p>Target: ${esc(targetText(goal))} &middot; Weightage ${Number(goal.weightage)}%</p>
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
    ${renderWorkspaceHero({
      eyebrow: "Manager workspace",
      title: "Review goals, coach progress, and keep check-ins moving",
      subtitle: "A focused team command center for submitted goal sheets, planned-vs-actual progress, and structured feedback.",
      actions: `
        <button class="btn secondary" data-action="export-report" data-format="csv">Export CSV</button>
        <button class="btn" data-action="export-report" data-format="xlsx">Export Excel</button>
      `,
      meta: `<span class="status submitted">${approvals.length} Pending Approvals</span><span>${team.length} team sheets</span>`,
    })}
    ${renderSectionNav([
      { href: "approvals", label: "Approvals" },
      { href: "checkins", label: "Check-ins" },
      { href: "reports", label: "Reports" },
      { href: "analytics", label: "Analytics" },
    ])}
    ${renderQuickActions([
      { href: "approvals", kicker: "Review", title: "Clear approval queue", body: "Edit targets inline and lock final sheets." },
      { href: "checkins", kicker: "Coach", title: "Record check-ins", body: "Capture discussion notes per quarter." },
      { href: "reports", kicker: "Export", title: "Download reports", body: "Use CSV or Excel for appraisal prep." },
    ])}
    <section class="hero-row">
      <div class="panel panel-accent">
        <h2>Team Review Snapshot</h2>
        <p>Approval and check-in work are grouped below so the demo feels like a real manager console.</p>
        <div class="demo-readiness">
          <div class="readiness-item"><span class="status submitted">${approvals.length}</span><div><strong>Pending reviews</strong><span>Goal sheets waiting for your decision.</span></div></div>
          <div class="readiness-item"><span class="status locked">${team.length}</span><div><strong>Team members</strong><span>Employees mapped to this manager.</span></div></div>
        </div>
      </div>
      ${renderCyclePanel()}
    </section>
    ${renderMetrics()}
    <div id="analytics">${renderAnalyticsPanel()}</div>
    <div id="reports">${renderReportCenter()}</div>
    ${renderNotifications()}
    <section class="panel" id="approvals">
      <h2>Approval Queue</h2>
      <p>Inline edits are available only while a sheet is submitted for review.</p>
      ${approvals.length ? approvals.map(renderApprovalSheet).join("") : `<div class="empty">No submitted sheets waiting for review.</div>`}
    </section>
    <section class="panel" style="margin-top:18px" id="checkins">
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
          <p>${esc(sheet.department)} &middot; ${sheet.goals.length} goals &middot; <span class="status ${esc(sheet.state)}">${esc(titleCase(sheet.state))}</span></p>
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
          <p>${esc(sheet.employee_email)} &middot; <span class="status ${esc(sheet.state)}">${esc(titleCase(sheet.state))}</span></p>
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
    ${renderWorkspaceHero({
      eyebrow: "Admin / HR control center",
      title: "Run the full goal cycle from one governed workspace",
      subtitle: "Configure windows, manage hierarchy, push shared KPIs, handle exceptions, monitor escalations, and export appraisal-ready reports.",
      actions: `
        <button class="btn" data-action="export-report" data-format="xlsx">Export Excel</button>
        <button class="btn secondary" data-action="export-report" data-format="csv">Export CSV</button>
        <button class="btn secondary" data-action="demo-mode">Open Demo Windows</button>
      `,
      meta: `<span class="status locked">${state.metrics.completion_rate}% Complete</span><span>${(state.org_users || []).length} users</span><span>${(state.shared_goals || []).length} shared KPIs</span>`,
    })}
    ${renderSectionNav([
      { href: "cycle", label: "Cycle" },
      { href: "org", label: "Org" },
      { href: "shared", label: "Shared Goals" },
      { href: "reports", label: "Reports" },
      { href: "audit", label: "Audit" },
    ])}
    ${renderQuickActions([
      { href: "cycle", kicker: "Setup", title: "Open active windows", body: "Make quarterly capture demo-ready." },
      { href: "org", kicker: "Govern", title: "Manage hierarchy", body: "Map people to managers and departments." },
      { href: "audit", kicker: "Control", title: "Inspect audit trail", body: "Show who changed what and when." },
    ])}
    <section class="hero-row">
      <div class="panel panel-accent">
        <h2>HR Operating Snapshot</h2>
        <p>Everything HR needs for cycle readiness, exception handling, and submission governance is available below.</p>
        <div class="demo-readiness">
          <div class="readiness-item"><span class="status locked">${state.metrics.locked_sheets}</span><div><strong>Locked sheets</strong><span>Approved sheets ready for tracking.</span></div></div>
          <div class="readiness-item"><span class="status submitted">${state.metrics.submitted_sheets}</span><div><strong>Pending approval</strong><span>Manager actions still open.</span></div></div>
        </div>
      </div>
      ${renderCyclePanel()}
    </section>
    ${renderMetrics()}
    <div id="analytics">${renderAnalyticsPanel()}</div>
    <div id="reports">${renderReportCenter()}</div>
    ${renderNotifications()}
    <section class="grid-two" id="cycle">
      <div class="panel">
        <h2>Cycle Windows</h2>
        <p>Adjust windows when you need to demo quarterly capture during the hackathon.</p>
        ${state.cycle.windows.map(renderWindowForm).join("")}
      </div>
      <div class="panel" id="shared">
        <h2>Create Shared Goal</h2>
        <p>Title and target stay read-only for recipients; only weightage is editable.</p>
        ${renderSharedGoalForm()}
      </div>
    </section>
    <section class="panel" style="margin-top:18px" id="org">
      <h2>Organization Hierarchy</h2>
      <p>Manage roles, departments, titles, and manager mapping from one HR console.</p>
      ${renderOrgDirectory()}
    </section>
    <section class="panel" style="margin-top:18px" id="exceptions">
      <h2>Goal Sheet Exceptions</h2>
      <p>Admin unlocks are logged with reason and timestamp.</p>
      ${renderAdminSheets()}
    </section>
    <section class="panel" style="margin-top:18px" id="escalations">
      <h2>Escalation Monitor</h2>
      <p>Rule-based escalation events are visible to HR for follow-up.</p>
      ${renderEscalations()}
    </section>
    <section class="panel" style="margin-top:18px" id="audit">
      <h2>Audit Trail</h2>
      <p>Every meaningful workflow change is stored for governance review.</p>
      ${renderAuditLog()}
    </section>
  `;
}

function renderReportCenter() {
  return `
    <section class="panel" style="margin-top:18px">
      <h2>Report Center</h2>
      <p>Download planned-vs-actual achievement data for appraisal discussions and HR governance.</p>
      <div class="notice-grid">
        <div class="notice">
          <span class="chip">CSV</span>
          <strong>Achievement report</strong>
          <span>Lightweight export for quick review, filtering, and upload into other tools.</span>
          <button class="btn secondary" style="margin-top:12px" data-action="export-report" data-format="csv">Download CSV</button>
        </div>
        <div class="notice">
          <span class="chip">Excel</span>
          <strong>Achievement workbook</strong>
          <span>Excel-ready report with planned targets, actual achievement, statuses, and scores.</span>
          <button class="btn" style="margin-top:12px" data-action="export-report" data-format="xlsx">Download XLSX</button>
        </div>
        <div class="notice">
          <span class="chip">Audit</span>
          <strong>Governance trail</strong>
          <span>Admin audit logs capture who changed what, when it happened, and why.</span>
        </div>
      </div>
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
    ${renderSharedGoalLibrary()}
  `;
}

function renderSharedGoalLibrary() {
  const sharedGoals = state.shared_goals || [];
  if (!sharedGoals.length) return `<div class="empty" style="margin-top:14px">No shared goals pushed yet.</div>`;
  return `
    <div class="table-wrap" style="margin-top:14px">
      <table>
        <thead><tr><th>Shared KPI</th><th>UoM</th><th>Target</th><th>Primary Owner</th></tr></thead>
        <tbody>
          ${sharedGoals
            .map((goal) => {
              const owner = (state.employees || []).find((employee) => employee.id === goal.primary_owner_id);
              return `
                <tr>
                  <td><strong>${esc(goal.title)}</strong><br /><small>${esc(goal.thrust_area)}</small></td>
                  <td>${esc(titleCase(goal.uom_type))}</td>
                  <td>${esc(goal.target_value ?? goal.target_date ?? "-")}</td>
                  <td>${esc(owner?.name || "-")}</td>
                </tr>
              `;
            })
            .join("")}
        </tbody>
      </table>
    </div>
  `;
}

function renderOrgDirectory() {
  const users = state.org_users || [];
  if (!users.length) return `<div class="empty">No users available.</div>`;
  return `
    <div class="org-directory">
      <div class="org-header">
        <span>Person</span>
        <span>Role</span>
        <span>Department</span>
        <span>Manager</span>
        <span></span>
      </div>
      ${users
        .map(
          (user) => `
            <form data-form="org-user" data-user-id="${user.id}" class="org-row">
              <div>
                <input name="name" value="${esc(user.name)}" />
                <input name="title" value="${esc(user.title || "")}" style="margin-top:8px" />
                <small>${esc(user.email)}</small>
              </div>
              <select name="role">
                ${["employee", "manager", "admin"].map((role) => `<option value="${role}" ${user.role === role ? "selected" : ""}>${esc(titleCase(role))}</option>`).join("")}
              </select>
              <select name="department">
                ${["Sales", "Customer Success", "Operations", "Product", "People Ops"].map((department) => `<option ${user.department === department ? "selected" : ""}>${esc(department)}</option>`).join("")}
              </select>
              <select name="manager_id">
                <option value="">No manager</option>
                ${(state.managers || [])
                  .map((manager) => `<option value="${manager.id}" ${user.manager_id === manager.id ? "selected" : ""}>${esc(manager.name)}</option>`)
                  .join("")}
              </select>
              <button class="btn secondary" type="submit">Save</button>
            </form>
          `,
        )
        .join("")}
    </div>
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
            <small>${esc(log.entity_type)} #${esc(log.entity_id)} ${log.reason ? `&middot; ${esc(log.reason)}` : ""}</small>
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
    if (kind === "org-user") {
      await api(`/api/admin/users/${form.dataset.userId}`, { method: "PATCH", body: JSON.stringify(payload) });
      showToast("Organization profile updated");
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
      const format = action.dataset.format || "csv";
      const response = await fetch(`/api/reports/achievement.${format}`, { headers: { Authorization: `Bearer ${token}` } });
      if (!response.ok) throw new Error("Could not export report");
      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = `achievement-report.${format}`;
      link.click();
      URL.revokeObjectURL(url);
      showToast(`Achievement ${format.toUpperCase()} downloaded`);
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
