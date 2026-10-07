// Global State & Utilities
document.addEventListener("DOMContentLoaded", () => {
    initNavigation();
    loadAllData();
});

function esc(value) {
    return String(value ?? "").replace(/[&<>"']/g, c => ({
        "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#039;"
    }[c]));
}

function initNavigation() {
    const navItems = document.querySelectorAll(".nav-item");
    const tabViews = document.querySelectorAll(".tab-view");
    const pageTitle = document.getElementById("pageTitle");

    const titles = {
        "dashboard-view": "Multi-Agent Support Engine",
        "queries-view": "Customer Support Queries History",
        "agents-view": "Multi-Agent AI System Architecture",
        "knowledge-view": "Banking Knowledge Base Repository",
        "escalations-view": "Escalated Case Audits & Tickets",
        "jira-view": "Jira Cloud Integration Log",
        "emails-view": "Email Customer Notification Logs",
        "analytics-view": "System Analytics & AI Performance",
        "settings-view": "Platform Settings & Threshold Config"
    };

    function switchTab(targetTabId) {
        navItems.forEach(item => {
            if (item.dataset.tab === targetTabId) {
                item.classList.add("active");
            } else {
                item.classList.remove("active");
            }
        });

        tabViews.forEach(view => {
            if (view.id === targetTabId) {
                view.classList.add("active");
            } else {
                view.classList.remove("active");
            }
        });

        if (pageTitle && titles[targetTabId]) {
            pageTitle.textContent = titles[targetTabId];
        }
    }

    navItems.forEach(item => {
        item.addEventListener("click", (e) => {
            e.preventDefault();
            const target = item.dataset.tab;
            window.location.hash = item.getAttribute("href");
            switchTab(target);
        });
    });

    // Handle direct URL hash navigation
    const hash = window.location.hash;
    if (hash) {
        const matchingNav = Array.from(navItems).find(item => item.getAttribute("href") === hash);
        if (matchingNav) {
            switchTab(matchingNav.dataset.tab);
        }
    }
}

async function loadAllData() {
    await Promise.all([
        loadStats(),
        loadQueriesHistory(),
        loadAgents(),
        loadKnowledgeBase(),
        loadEscalations(),
        loadJiraTickets(),
        loadEmailLogs(),
        loadSettings()
    ]);
}

// Preset Quick Fill
function fillSample(type) {
    const nameInput = document.getElementById("customerName");
    const queryInput = document.getElementById("query");

    if (type === "upi") {
        nameInput.value = "Rahul Sharma";
        queryInput.value = "My UPI payment of Rs 2,500 failed at a store but money was debited from my account.";
    } else if (type === "atm") {
        nameInput.value = "Priya Patel";
        queryInput.value = "I tried to withdraw cash from ATM but no money came out, but account received SMS for debit.";
    } else if (type === "fraud") {
        nameInput.value = "Amit Verma";
        queryInput.value = "An unauthorized transaction of Rs 15,000 was made on my credit card without my OTP or permission!";
    } else if (type === "pwd") {
        nameInput.value = "Sneha Gupta";
        queryInput.value = "I forgot my net banking password and cannot log into my bank account.";
    }
}

// 1. Process Query via Multi-Agent Engine
async function processQuery() {
    const customerName = document.getElementById("customerName").value.trim();
    const email = document.getElementById("email").value.trim();
    const query = document.getElementById("query").value.trim();
    const button = document.getElementById("processBtn");
    const processing = document.getElementById("processing");
    const output = document.getElementById("result");

    if (!query) {
        output.innerHTML = '<div class="badge red">Please enter a banking issue query.</div>';
        return;
    }

    button.disabled = true;
    processing.textContent = "Step 1/4: Diagnosis Agent classifying category & risk...";

    // Highlight Flow Step 1
    highlightStep("step-diag");

    try {
        const response = await fetch("/api/ticket", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                customer_name: customerName,
                email: email,
                query: query
            })
        });

        const data = await response.json();

        if (!data.success) {
            throw new Error(data.message || "Query processing failed.");
        }

        // Highlight Flow Steps sequentially
        highlightStep("step-retrieval");
        processing.textContent = "Step 2/4: Knowledge Retrieval Agent searching articles...";
        await new Promise(r => setTimeout(r, 200));

        highlightStep("step-resolution");
        processing.textContent = "Step 3/4: Resolution Agent extracting action steps...";
        await new Promise(r => setTimeout(r, 200));

        highlightStep("step-validation");
        processing.textContent = "Step 4/4: Validation & Escalation Agents finalizing score...";
        await new Promise(r => setTimeout(r, 200));

        const result = data.result;
        const validation = result.validation;
        const auto = data.status === "AUTO_RESOLVE";

        if (!auto) {
            highlightStep("step-escalation");
        }

        const steps = result.resolution.steps.map(step => `<li>${esc(step)}</li>`).join("");

        let integrations = "";
        if (data.email) {
            integrations += `<div class="integration-box">✉ <b>Customer Email Notification:</b> ${esc(data.email.message)}</div>`;
        }
        if (data.jira) {
            integrations += `<div class="integration-box">🔗 <b>Jira Support Ticket:</b> ${esc(data.jira.message)} ${data.jira.ticket_id ? "— Ticket ID: <b>" + esc(data.jira.ticket_id) + "</b>" : ""}</div>`;
        }

        output.innerHTML = `
            <div class="result-block">
                <div class="result-row">
                    <span class="result-key">Diagnosis Category</span>
                    <span class="badge blue">${esc(result.diagnosis.category)}</span>
                </div>
                <div class="result-row">
                    <span class="result-key">Matched Article</span>
                    <span class="result-val">${esc(result.retrieval.article.title)} (${Math.round(result.retrieval.similarity * 100)}% match)</span>
                </div>
                <div class="result-row">
                    <span class="result-key">Risk Evaluation</span>
                    <span class="badge ${validation.risk === "HIGH" ? "red" : validation.risk === "MEDIUM" ? "yellow" : "green"}">${esc(validation.risk)}</span>
                </div>
                <div class="result-row">
                    <span class="result-key">Resolution Confidence</span>
                    <span class="result-val">${esc(data.confidence)}%</span>
                </div>
                <div class="result-row">
                    <span class="result-key">Decision Status</span>
                    <span class="badge ${auto ? "green" : "red"}">${auto ? "✓ AUTO RESOLVE" : "⚠ ESCALATED"}</span>
                </div>
                <div>
                    <span class="result-key">Recommended Action Steps:</span>
                    <ol class="steps-list">${steps}</ol>
                </div>
                ${integrations}
            </div>
        `;

        // Refresh stats & tables
        await loadAllData();

    } catch (err) {
        output.innerHTML = `<div class="badge red">${esc(err.message)}</div>`;
    } finally {
        button.disabled = false;
        processing.textContent = "";
        clearStepHighlights();
    }
}

function highlightStep(stepId) {
    clearStepHighlights();
    const el = document.getElementById(stepId);
    if (el) el.classList.add("active");
}

function clearStepHighlights() {
    ["step-diag", "step-retrieval", "step-resolution", "step-validation", "step-escalation"].forEach(id => {
        const el = document.getElementById(id);
        if (el) el.classList.remove("active");
    });
}

// 2. Load Stats & Charts
async function loadStats() {
    try {
        const res = await fetch("/api/stats");
        const data = await res.json();

        document.getElementById("statQueries").textContent = data.total;
        document.getElementById("statResolved").textContent = data.auto_resolved;
        document.getElementById("statEscalated").textContent = data.escalated;
        document.getElementById("statConfidence").textContent = data.avg_confidence + "%";

        // Render Analytics Charts
        renderCategoryBars(data.categories, data.total);
        renderRiskBars(data.risks, data.total);
    } catch (e) {
        console.error("Error loading stats:", e);
    }
}

function renderCategoryBars(categories, total) {
    const container = document.getElementById("categoryBars");
    if (!container) return;

    if (!total || Object.keys(categories).length === 0) {
        container.innerHTML = '<div class="muted">No query data available yet.</div>';
        return;
    }

    let html = "";
    for (const [cat, count] of Object.entries(categories)) {
        const pct = Math.round((count / total) * 100);
        html += `
            <div class="bar-row">
                <div class="bar-info">
                    <span>${esc(cat)}</span>
                    <span>${count} (${pct}%)</span>
                </div>
                <div class="bar-track">
                    <div class="bar-fill" style="width: ${pct}%"></div>
                </div>
            </div>
        `;
    }
    container.innerHTML = html;
}

function renderRiskBars(risks, total) {
    const container = document.getElementById("riskBars");
    if (!container) return;

    if (!total) {
        container.innerHTML = '<div class="muted">No risk data available yet.</div>';
        return;
    }

    let html = "";
    const colors = { HIGH: "var(--accent-red)", MEDIUM: "var(--accent-yellow)", LOW: "var(--accent-green)" };
    for (const [risk, count] of Object.entries(risks)) {
        const pct = Math.round((count / total) * 100);
        html += `
            <div class="bar-row">
                <div class="bar-info">
                    <span>${esc(risk)} Risk</span>
                    <span>${count} (${pct}%)</span>
                </div>
                <div class="bar-track">
                    <div class="bar-fill" style="width: ${pct}%; background: ${colors[risk] || "var(--primary)"}"></div>
                </div>
            </div>
        `;
    }
    container.innerHTML = html;
}

// 3. Customer Queries Table
async function loadQueriesHistory() {
    try {
        const res = await fetch("/api/cases");
        const data = await res.json();
        const tbody = document.getElementById("queriesTableBody");

        if (!data.cases || data.cases.length === 0) {
            tbody.innerHTML = '<tr><td colspan="8" class="muted" style="text-align: center;">No customer queries recorded yet.</td></tr>';
            return;
        }

        renderQueriesTable(data.cases);
    } catch (e) {
        console.error("Error loading queries history:", e);
    }
}

function renderQueriesTable(cases) {
    const tbody = document.getElementById("queriesTableBody");
    tbody.innerHTML = cases.map(c => `
        <tr>
            <td>${esc(c.timestamp.replace("T", " "))}</td>
            <td><b>${esc(c.customer_name)}</b><br><small class="muted">${esc(c.customer_email || (typeof c.email === "string" ? c.email : "No Email"))}</small></td>
            <td><span class="badge blue">${esc(c.category)}</span></td>
            <td>${esc(c.query)}</td>
            <td><span class="badge ${c.risk === "HIGH" ? "red" : c.risk === "MEDIUM" ? "yellow" : "green"}">${esc(c.risk)}</span></td>
            <td><b>${esc(c.confidence)}%</b></td>
            <td><span class="badge ${c.status === "AUTO_RESOLVE" ? "green" : "red"}">${esc(c.status)}</span></td>
            <td>${c.jira?.ticket_id ? '<span class="badge blue">Jira: ' + esc(c.jira.ticket_id) + '</span>' : c.email?.success ? '<span class="badge green">Email Sent</span>' : c.email?.message ? '<span class="badge yellow">' + esc(c.email.message) + '</span>' : '<span class="muted">None</span>'}</td>
        </tr>
    `).join("");
}

function filterQueriesTable() {
    const search = document.getElementById("querySearch").value.toLowerCase();
    const status = document.getElementById("queryFilterStatus").value;

    fetch(`/api/cases?search=${encodeURIComponent(search)}&status=${encodeURIComponent(status)}`)
        .then(r => r.json())
        .then(d => renderQueriesTable(d.cases || []));
}

async function clearAllCases() {
    if (confirm("Are you sure you want to clear all query history?")) {
        await fetch("/api/cases/clear", { method: "POST" });
        await loadAllData();
    }
}

// 4. AI Agents View
async function loadAgents() {
    try {
        const res = await fetch("/api/agents");
        const data = await res.json();
        const container = document.getElementById("agentsList");

        container.innerHTML = data.agents.map(a => `
            <div class="agent-card">
                <div class="agent-header">
                    <span class="agent-title">${esc(a.name)}</span>
                    <span class="badge green">● ${esc(a.status)}</span>
                </div>
                <div class="agent-role">${esc(a.role)}</div>
                <div class="agent-metrics">${esc(a.metrics)}</div>
            </div>
        `).join("");
    } catch (e) {
        console.error("Error loading agents:", e);
    }
}

// 5. Knowledge Base View
async function loadKnowledgeBase() {
    try {
        const search = document.getElementById("kbSearch")?.value || "";
        const cat = document.getElementById("kbCategory")?.value || "";

        const res = await fetch(`/api/knowledge_base?search=${encodeURIComponent(search)}&category=${encodeURIComponent(cat)}`);
        const data = await res.json();
        const container = document.getElementById("kbGrid");

        if (!data.articles || data.articles.length === 0) {
            container.innerHTML = '<div class="muted">No knowledge base articles found.</div>';
            return;
        }

        container.innerHTML = data.articles.map(article => `
            <div class="kb-card">
                <div class="kb-card-header">
                    <div class="kb-title">${esc(article.title)}</div>
                    <span class="badge blue">${esc(article.category)}</span>
                </div>
                <div class="kb-content">${esc(article.content)}</div>
            </div>
        `).join("");
    } catch (e) {
        console.error("Error loading knowledge base:", e);
    }
}

function showAddKbModal() {
    document.getElementById("kbModal").classList.remove("hidden");
}

function hideAddKbModal() {
    document.getElementById("kbModal").classList.add("hidden");
}

async function submitNewKbArticle() {
    const title = document.getElementById("newKbTitle").value.trim();
    const category = document.getElementById("newKbCategory").value;
    const content = document.getElementById("newKbContent").value.trim();

    if (!title || !content) {
        alert("Please fill in both article title and resolution content.");
        return;
    }

    try {
        const res = await fetch("/api/knowledge_base", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ title, category, content })
        });
        const data = await res.json();
        if (data.success) {
            hideAddKbModal();
            document.getElementById("newKbTitle").value = "";
            document.getElementById("newKbContent").value = "";
            await loadKnowledgeBase();
        } else {
            alert(data.message || "Failed to save article");
        }
    } catch (e) {
        alert("Error saving article: " + e.message);
    }
}

// 6. Escalated Cases View
async function loadEscalations() {
    try {
        const res = await fetch("/api/cases?status=ESCALATE");
        const data = await res.json();
        const tbody = document.getElementById("escalationsTableBody");

        if (!data.cases || data.cases.length === 0) {
            tbody.innerHTML = '<tr><td colspan="7" class="muted" style="text-align: center;">No escalated cases recorded.</td></tr>';
            return;
        }

        tbody.innerHTML = data.cases.map(c => `
            <tr>
                <td>${esc(c.timestamp.replace("T", " "))}</td>
                <td><b>${esc(c.customer_name)}</b></td>
                <td><span class="badge blue">${esc(c.category)}</span></td>
                <td>${esc(c.query)}</td>
                <td><span class="badge ${c.risk === "HIGH" ? "red" : "yellow"}">${esc(c.risk)}</span></td>
                <td><b>${esc(c.confidence)}%</b></td>
                <td>${c.jira?.ticket_id ? '<span class="badge green">Jira Key: ' + esc(c.jira.ticket_id) + '</span>' : '<span class="badge red">Escalated (Config Pending)</span>'}</td>
            </tr>
        `).join("");
    } catch (e) {
        console.error("Error loading escalations:", e);
    }
}

// 7. Jira Tickets View
async function loadJiraTickets() {
    try {
        const res = await fetch("/api/jira/tickets");
        const data = await res.json();
        const tbody = document.getElementById("jiraTableBody");

        if (!data.tickets || data.tickets.length === 0) {
            tbody.innerHTML = '<tr><td colspan="6" class="muted" style="text-align: center;">No Jira tickets created yet.</td></tr>';
            return;
        }

        tbody.innerHTML = data.tickets.map(t => `
            <tr>
                <td>${esc(t.timestamp.replace("T", " "))}</td>
                <td><b>${esc(t.customer_name)}</b></td>
                <td>${esc(t.query)}</td>
                <td><span class="badge ${t.risk === "HIGH" ? "red" : "yellow"}">${esc(t.risk)}</span></td>
                <td><b>${esc(t.jira?.ticket_id || "PENDING")}</b></td>
                <td><span class="badge ${t.jira?.success ? "green" : "yellow"}">${esc(t.jira?.message || "Triggered")}</span></td>
            </tr>
        `).join("");
    } catch (e) {
        console.error("Error loading Jira tickets:", e);
    }
}

// 8. Email Logs View
async function loadEmailLogs() {
    try {
        const res = await fetch("/api/email/logs");
        const data = await res.json();
        const tbody = document.getElementById("emailsTableBody");

        if (!data.logs || data.logs.length === 0) {
            tbody.innerHTML = '<tr><td colspan="6" class="muted" style="text-align: center;">No customer emails sent yet.</td></tr>';
            return;
        }

        tbody.innerHTML = data.logs.map(l => `
            <tr>
                <td>${esc(l.timestamp.replace("T", " "))}</td>
                <td><b>${esc(l.customer_name)}</b></td>
                <td>${esc(l.email)}</td>
                <td><span class="badge blue">${esc(l.category)}</span></td>
                <td><span class="badge ${l.status === "AUTO_RESOLVE" ? "green" : "yellow"}">${esc(l.status)}</span></td>
                <td><span class="badge ${l.email_result?.success ? "green" : "red"}">${esc(l.email_result?.message || "No notification result")}</span></td>
            </tr>
        `).join("");
    } catch (e) {
        console.error("Error loading email logs:", e);
    }
}

// 9. Settings View
async function loadSettings() {
    try {
        const res = await fetch("/api/settings");
        const data = await res.json();
        const s = data.settings;

        document.getElementById("thresholdSlider").value = s.threshold;
        document.getElementById("currentThresholdLabel").textContent = s.threshold + "%";

        const infoGrid = document.getElementById("settingsInfo");
        infoGrid.innerHTML = `
            <div class="info-item">
                <div class="info-label">Jira URL</div>
                <div class="info-val">${esc(s.jira_url)}</div>
            </div>
            <div class="info-item">
                <div class="info-label">Jira Account Email</div>
                <div class="info-val">${esc(s.jira_email)}</div>
            </div>
            <div class="info-item">
                <div class="info-label">Jira Project Key</div>
                <div class="info-val">${esc(s.jira_project)}</div>
            </div>
            <div class="info-item">
                <div class="info-label">Jira Connection</div>
                <div class="info-val">${s.jira_configured ? "Configured" : "Missing credentials in .env"}</div>
            </div>
            <div class="info-item">
                <div class="info-label">SMTP Gateway</div>
                <div class="info-val">${esc(s.smtp_server)}:${esc(s.smtp_port)}</div>
            </div>
            <div class="info-item">
                <div class="info-label">Email Connection</div>
                <div class="info-val">${s.smtp_configured ? "Configured" : "Missing credentials in .env"}</div>
            </div>
        `;
    } catch (e) {
        console.error("Error loading settings:", e);
    }
}

async function saveSettings() {
    const val = document.getElementById("thresholdSlider").value;
    try {
        const res = await fetch("/api/settings", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ threshold: parseFloat(val) })
        });
        const data = await res.json();
        if (data.success) {
            alert(data.message);
            await loadAllData();
        }
    } catch (e) {
        alert("Failed to save settings: " + e.message);
    }
}
