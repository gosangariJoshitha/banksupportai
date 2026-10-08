<<<<<<< HEAD
from datetime import datetime
import json
from pathlib import Path

from flask import Flask, jsonify, render_template, request
from dotenv import load_dotenv

import config
from agents import BankSupportAI
from jira_service import JiraService
from email_service import EmailService

load_dotenv()

app = Flask(__name__)
bank_ai = BankSupportAI(threshold=config.AUTO_RESOLVE_THRESHOLD)
jira_service = JiraService()
email_service = EmailService()

DATA_PATH = Path(__file__).parent / "data" / "transactions.json"
KB_PATH = Path(__file__).parent / "knowledge_base" / "banking_knowledge.json"


def load_cases():
    try:
        return json.loads(DATA_PATH.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def save_case(record):
    records = load_cases()
    records.insert(0, record)  # Newest first
    DATA_PATH.write_text(json.dumps(records, indent=2), encoding="utf-8")


def load_kb():
    try:
        return json.loads(KB_PATH.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def save_kb(articles):
    KB_PATH.write_text(json.dumps(articles, indent=2), encoding="utf-8")


@app.route("/")
def dashboard():
    return render_template("dashboard.html")


@app.route("/api/ticket", methods=["POST"])
def process_query():
    data = request.get_json(silent=True) or {}
    query = (data.get("query") or "").strip()
    customer_name = (data.get("customer_name") or "Customer").strip()
    email = (data.get("email") or "").strip()

    if not query:
        return jsonify({"success": False, "message": "Banking query is required"}), 400

    result = bank_ai.process_query(query)
    validation = result["validation"]
    status = validation["status"]

    email_result = None
    jira_result = None

    if status != "AUTO_RESOLVE":
        priority = "Highest" if validation["risk"] == "HIGH" else "High"
        jira_result = jira_service.create_ticket(
            summary=result["diagnosis"]["diagnosis"],
            description=(
                f"Customer: {customer_name}\n"
                f"Email: {email}\n"
                f"Query: {query}\n\n"
                f"Diagnosis: {result['diagnosis']['diagnosis']}\n"
                f"Risk: {validation['risk']}\n"
                f"AI Confidence: {validation['confidence']}%\n\n"
                "Suggested resolution:\n"
                + "\n".join(result["resolution"]["steps"])
            ),
            priority=priority
        )

    if email:
        email_status = (
            "automatically resolved"
            if status == "AUTO_RESOLVE"
            else "escalated to human support"
        )
        jira_reference = (
            f"\nJira ticket: {jira_result['ticket_id']}"
            if jira_result and jira_result.get("ticket_id")
            else ""
        )
        body = (
            f"Hello {customer_name},\n\n"
            f"Your banking support case has been {email_status}.\n\n"
            f"{result['resolution']['response']}\n\n"
            "Recommended steps:\n"
            + "\n".join(
                f"{i + 1}. {step}"
                for i, step in enumerate(result["resolution"]["steps"])
            )
            + f"\n\nCase status: {status}"
            + f"\nResolution confidence: {validation['confidence']}%"
            + jira_reference
            + "\n\nBankSupport AI"
        )
        email_result = email_service.send_email(
            email, "BankSupport AI - Support Case Update", body
        )
    else:
        email_result = {
            "success": False,
            "message": "No customer email address provided; notification was not sent."
        }

    case = {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "customer_name": customer_name,
        "customer_email": email,
        "query": query,
        "category": result["diagnosis"]["category"],
        "risk": validation["risk"],
        "confidence": validation["confidence"],
        "status": status,
        "jira": jira_result,
        "email": email_result,
        "steps": result["resolution"]["steps"]
    }
    save_case(case)

    return jsonify({
        "success": True,
        "status": status,
        "confidence": validation["confidence"],
        "risk": validation["risk"],
        "result": result,
        "jira": jira_result,
        "email": email_result
    })


@app.route("/api/stats", methods=["GET"])
def get_stats():
    cases = load_cases()
    total = len(cases)
    resolved = sum(1 for c in cases if c.get("status") == "AUTO_RESOLVE")
    escalated = sum(1 for c in cases if c.get("status") == "ESCALATE")
    avg_conf = round(sum(c.get("confidence", 0) for c in cases) / total, 1) if total > 0 else 0

    categories = {}
    risks = {"HIGH": 0, "MEDIUM": 0, "LOW": 0}
    for c in cases:
        cat = c.get("category", "General Banking")
        categories[cat] = categories.get(cat, 0) + 1
        r = c.get("risk", "LOW")
        if r in risks:
            risks[r] += 1

    return jsonify({
        "total": total,
        "auto_resolved": resolved,
        "escalated": escalated,
        "avg_confidence": avg_conf,
        "categories": categories,
        "risks": risks
    })


@app.route("/api/cases", methods=["GET"])
def get_cases():
    cases = load_cases()
    status_filter = request.args.get("status")
    category_filter = request.args.get("category")
    search = request.args.get("search", "").lower()

    filtered = cases
    if status_filter:
        filtered = [c for c in filtered if c.get("status") == status_filter]
    if category_filter:
        filtered = [c for c in filtered if c.get("category") == category_filter]
    if search:
        filtered = [
            c for c in filtered
            if search in c.get("query", "").lower()
            or search in c.get("customer_name", "").lower()
            or search in c.get("category", "").lower()
        ]

    return jsonify({"success": True, "count": len(filtered), "cases": filtered})


@app.route("/api/cases/clear", methods=["POST"])
def clear_cases():
    DATA_PATH.write_text("[]", encoding="utf-8")
    return jsonify({"success": True, "message": "Transaction history cleared"})


@app.route("/api/knowledge_base", methods=["GET", "POST"])
def knowledge_base_route():
    articles = load_kb()
    if request.method == "POST":
        data = request.get_json(silent=True) or {}
        title = (data.get("title") or "").strip()
        category = (data.get("category") or "General Banking").strip()
        content = (data.get("content") or "").strip()
        if not title or not content:
            return jsonify({"success": False, "message": "Title and content are required"}), 400
        
        new_article = {
            "id": len(articles) + 1,
            "title": title,
            "category": category,
            "content": content
        }
        articles.append(new_article)
        save_kb(articles)
        bank_ai.retrieval_agent.__init__() # Refresh retrieval index
        return jsonify({"success": True, "article": new_article, "message": "Article added successfully"})

    category_filter = request.args.get("category")
    search = request.args.get("search", "").lower()
    filtered = articles
    if category_filter:
        filtered = [a for a in filtered if a.get("category") == category_filter]
    if search:
        filtered = [
            a for a in filtered
            if search in a.get("title", "").lower() or search in a.get("content", "").lower()
        ]
    return jsonify({"success": True, "count": len(filtered), "articles": filtered})


@app.route("/api/agents", methods=["GET"])
def get_agents():
    agents = [
        {
            "name": "BankingDiagnosisAgent",
            "type": "Diagnosis",
            "status": "Active",
            "role": "Classifies queries into categories (UPI, ATM, Cards, Fraud) and evaluates preliminary risk level.",
            "metrics": "Coverage: 9 Categories | Match Engine: Lexical Keyword Mapping"
        },
        {
            "name": "BankingRetrievalAgent",
            "type": "Knowledge Retrieval",
            "status": "Active",
            "role": "Performs TF-IDF similarity scoring against the official banking knowledge base.",
            "metrics": f"Documents Index: {len(load_kb())} Articles | Scoring Algorithm: Dual TF-IDF & Coverage"
        },
        {
            "name": "BankingResolutionAgent",
            "type": "Resolution Generator",
            "status": "Active",
            "role": "Extracts actionable resolution steps and formats safe guidance for banking customers.",
            "metrics": "Format: Bulleted Action Steps | Compliance: Official Bank Channel Filter"
        },
        {
            "name": "ValidationAgent",
            "type": "Quality & Confidence",
            "status": "Active",
            "role": "Computes weighted confidence score and determines AUTO_RESOLVE vs ESCALATE decision.",
            "metrics": f"Threshold: {bank_ai.threshold}% | Weights: 40% Diagnosis, 45% Retrieval, 15% Completeness"
        },
        {
            "name": "EscalationAgent",
            "type": "Escalation Handler",
            "status": "Active",
            "role": "Triggers Jira support ticket creation and human operator handover for high-risk or low-confidence cases.",
            "metrics": "Integrations: Jira REST API v3, SMTP Email Gateway"
        }
    ]
    return jsonify({"success": True, "agents": agents})


@app.route("/api/jira/tickets", methods=["GET"])
def get_jira_tickets():
    cases = load_cases()
    tickets = [
        {
            "timestamp": c.get("timestamp"),
            "customer_name": c.get("customer_name"),
            "query": c.get("query"),
            "category": c.get("category"),
            "risk": c.get("risk"),
            "confidence": c.get("confidence"),
            "jira": c.get("jira")
        }
        for c in cases if c.get("jira") or c.get("status") == "ESCALATE"
    ]
    return jsonify({"success": True, "count": len(tickets), "tickets": tickets})


@app.route("/api/email/logs", methods=["GET"])
def get_email_logs():
    cases = load_cases()
    logs = [
        {
            "timestamp": c.get("timestamp"),
            "customer_name": c.get("customer_name"),
            "email": c.get("customer_email", ""),
            "category": c.get("category"),
            "status": c.get("status"),
            "email_result": c.get("email")
        }
        for c in cases if c.get("email") or c.get("customer_email")
    ]
    return jsonify({"success": True, "count": len(logs), "logs": logs})


ENV_PATH = Path(__file__).parent / ".env"

def save_env_key(key, value):
    lines = []
    if ENV_PATH.exists():
        lines = ENV_PATH.read_text(encoding="utf-8").splitlines()
    found = False
    new_lines = []
    for line in lines:
        if line.startswith(f"{key}="):
            new_lines.append(f"{key}={value}")
            found = True
        else:
            new_lines.append(line)
    if not found:
        new_lines.append(f"{key}={value}")
    ENV_PATH.write_text("\n".join(new_lines) + "\n", encoding="utf-8")

@app.route("/api/settings", methods=["GET", "POST"])
def settings_route():
    if request.method == "POST":
        data = request.get_json(silent=True) or {}
        if "threshold" in data:
            new_threshold = float(data.get("threshold", 75.0))
            config.AUTO_RESOLVE_THRESHOLD = new_threshold
            bank_ai.threshold = new_threshold
            save_env_key("AUTO_RESOLVE_THRESHOLD", str(new_threshold))

        if "jira_url" in data:
            val = data["jira_url"].strip()
            config.JIRA_URL = val
            save_env_key("JIRA_URL", val)
        if "jira_email" in data:
            val = data["jira_email"].strip()
            config.JIRA_EMAIL = val
            save_env_key("JIRA_EMAIL", val)
        if "jira_api_token" in data and data["jira_api_token"]:
            val = data["jira_api_token"].strip()
            config.JIRA_API_TOKEN = val
            save_env_key("JIRA_API_TOKEN", val)
        if "jira_project" in data:
            val = data["jira_project"].strip()
            config.JIRA_PROJECT_KEY = val
            save_env_key("JIRA_PROJECT_KEY", val)

        if "smtp_email" in data:
            val = data["smtp_email"].strip()
            config.SMTP_EMAIL = val
            save_env_key("SMTP_EMAIL", val)
        if "smtp_password" in data and data["smtp_password"]:
            val = "".join(data["smtp_password"].split())
            config.SMTP_PASSWORD = val
            save_env_key("SMTP_PASSWORD", val)

        return jsonify({"success": True, "message": "Settings updated successfully."})

    return jsonify({
        "success": True,
        "settings": {
            "jira_url": config.JIRA_URL or "Not Configured",
            "jira_email": config.JIRA_EMAIL or "Not Configured",
            "jira_project": config.JIRA_PROJECT_KEY,
            "jira_configured": all([
                config.JIRA_URL,
                config.JIRA_EMAIL,
                config.JIRA_API_TOKEN,
                config.JIRA_PROJECT_KEY
            ]),
            "smtp_server": config.SMTP_SERVER,
            "smtp_port": config.SMTP_PORT,
            "smtp_email": config.SMTP_EMAIL or "Not Configured",
            "smtp_configured": bool(config.SMTP_EMAIL and config.SMTP_PASSWORD),
            "threshold": bank_ai.threshold
        }
    })

@app.route("/api/test/jira", methods=["POST"])
def test_jira_route():
    res = jira_service.test_connection()
    return jsonify(res)

@app.route("/api/test/email", methods=["POST"])
def test_email_route():
    res = email_service.test_connection()
    return jsonify(res)



@app.route("/api/health")
def health():
    return jsonify({"status": "running", "service": "BankSupport AI Milestone 3"})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
=======
"""
SupportPilot – AI Ticket Resolution Agent
Knowledge Retrieval & Resolution Generation
Flask app with JWT auth + full RAG pipeline
"""

import json
import time
from flask import (
    Flask, render_template, request,
    redirect, url_for, flash, make_response, jsonify
)

from config import (
    SECRET_KEY, DATABASE, KB_PATH,
    SEED_RETRIEVAL_ACCURACY, SEED_RESOLUTION_RATE, SEED_AVG_RESPONSE_TIME
)
from database import (
    create_tables, insert_ticket, get_all_tickets,
    get_ticket_by_id, update_ticket_status, get_dashboard_stats,
    create_user, login_user, save_rag_result
)
from auth import login_required, get_current_user
from classifier import classify_ticket
from rag.retriever import KnowledgeRetriever
from rag.pipeline  import run_pipeline

# ──────────────────────────────────────────────
# App setup
# ──────────────────────────────────────────────
app = Flask(__name__)
app.secret_key = SECRET_KEY

# Initialise DB tables
create_tables()

# Initialise the knowledge-base retriever once (shared across requests)
retriever = KnowledgeRetriever(KB_PATH)

# Count KB articles for display
with open(KB_PATH, "r", encoding="utf-8") as _f:
    _kb_data = json.load(_f)
    KB_COUNT      = len(_kb_data.get("entries", []))
    KB_CATEGORIES = len({e.get("category", "") for e in _kb_data["entries"]})


# ──────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────

def calculate_severity(title: str, description: str = "") -> str:
    """
    Determines ticket severity using:
    1. The ML classifier's predicted category (primary signal)
    2. Confidence score as a modulator
    3. A small set of genuine emergency override keywords (last resort)

    Returns 'High', 'Medium', or 'Low'.
    """
    # ── Category → severity map (all 77 Banking77 classes) ──
    HIGH_CATEGORIES = {
        # Fraud / compromise
        "compromised_card",
        "card_payment_not_recognised",
        "cash_withdrawal_not_recognised",
        "direct_debit_payment_not_recognised",
        "transaction_charged_twice",
        "extra_charge_on_statement",
        # Lost / stolen
        "lost_or_stolen_card",
        "lost_or_stolen_phone",
        # Card & cash failures
        "card_swallowed",
        "declined_cash_withdrawal",
        "declined_card_payment",
        "wrong_amount_of_cash_received",
        "pending_cash_withdrawal",
        # Transfer failures
        "failed_transfer",
        "transfer_not_received_by_recipient",
        "declined_transfer",
        "reverted_card_payment?",
        "beneficiary_not_allowed",
        # Account / identity
        "unable_to_verify_identity",
        "terminate_account",
        "pin_blocked",
    }

    MEDIUM_CATEGORIES = {
        # Card management
        "card_not_working",
        "card_about_to_expire",
        "card_arrival",
        "card_delivery_estimate",
        "activate_my_card",
        "contactless_not_working",
        "virtual_card_not_working",
        # Payments
        "card_payment_fee_charged",
        "card_payment_wrong_exchange_rate",
        "pending_card_payment",
        # Transfers & balance
        "balance_not_updated_after_bank_transfer",
        "balance_not_updated_after_cheque_or_cash_deposit",
        "cancel_transfer",
        "pending_transfer",
        "transfer_timing",
        "transfer_into_account",
        "receiving_money",
        "pending_top_up",
        "top_up_failed",
        "top_up_reverted",
        # Refunds
        "request_refund",
        "Refund_not_showing_up",
        # Charges
        "cash_withdrawal_charge",
        "exchange_charge",
        "top_up_by_bank_transfer_charge",
        "top_up_by_card_charge",
        "transfer_fee_charged",
        # ATM / PIN
        "atm_support",
        "change_pin",
        "passcode_forgotten",
        # Identity
        "verify_my_identity",
        "verify_source_of_funds",
        "verify_top_up",
        "why_verify_identity",
    }

    # LOW_CATEGORIES = everything else (informational / account setup)

    # ── Step 1: classify the ticket ──
    combined = title + " " + description
    category, confidence = classify_ticket(combined)
    category = category.strip()

    # ── Step 2: base severity from category ──
    if category in HIGH_CATEGORIES:
        base = "High"
    elif category in MEDIUM_CATEGORIES:
        base = "Medium"
    else:
        base = "Low"

    # ── Step 3: confidence modulation ──
    # Low confidence (<40%) → downgrade one level (model is unsure)
    if confidence < 40:
        if base == "High":
            base = "Medium"
        elif base == "Medium":
            base = "Low"

    # ── Step 4: genuine emergency override (only true emergencies) ──
    text = (title + " " + description).lower()
    true_emergency = [
        "compromised", "hacked", "stolen card", "card stolen",
        "account blocked", "fraud", "unauthorized transaction",
        "unauthorised transaction",
    ]
    for kw in true_emergency:
        if kw in text:
            base = "High"
            break

    return base


def calculate_priority(severity: str) -> str:
    return {"High": "P1", "Medium": "P2", "Low": "P3"}.get(severity, "P3")


# ──────────────────────────────────────────────
# Auth Routes
# ──────────────────────────────────────────────

@app.route("/login", methods=["GET", "POST"])
def login():
    # Already logged in?
    if get_current_user():
        return redirect(url_for("home"))

    error = None
    if request.method == "POST":
        email    = request.form.get("email", "").strip()
        password = request.form.get("password", "")

        result = login_user(email, password)
        if result["success"]:
            resp = make_response(redirect(url_for("home")))
            resp.set_cookie(
                "jwt_token", result["token"],
                httponly=True, samesite="Lax",
                max_age=3600
            )
            return resp
        else:
            error = result["error"]

    return render_template("login.html", error=error)


@app.route("/signup", methods=["GET", "POST"])
def signup():
    if get_current_user():
        return redirect(url_for("home"))

    error   = None
    success = None

    if request.method == "POST":
        name     = request.form.get("name", "").strip()
        email    = request.form.get("email", "").strip()
        password = request.form.get("password", "")
        confirm  = request.form.get("confirm_password", "")
        role     = request.form.get("role", "agent")

        if not name or not email or not password:
            error = "All fields are required."
        elif password != confirm:
            error = "Passwords do not match."
        elif len(password) < 8:
            error = "Password must be at least 8 characters."
        else:
            result = create_user(name, email, password, role)
            if result["success"]:
                success = "Account created! You can now log in."
            else:
                error = result["error"]

    return render_template("signup.html", error=error, success=success)


@app.route("/logout")
def logout():
    resp = make_response(redirect(url_for("login")))
    resp.delete_cookie("jwt_token")
    return resp


# ──────────────────────────────────────────────
# Main Routes (protected)
# ──────────────────────────────────────────────

@app.route("/", methods=["GET", "POST"])
@login_required
def home():
    current_user = get_current_user()
    result = None

    if request.method == "POST":
        customer_name = request.form.get("customer_name", "").strip()
        email         = request.form.get("email", "").strip()
        title         = request.form.get("title", "").strip()
        description   = request.form.get("description", "").strip()

        # ── AI Classification ──
        combined      = title + " " + description
        category, confidence = classify_ticket(combined)
        severity      = calculate_severity(title, description)
        priority      = calculate_priority(severity)

        # ── RAG Pipeline ──
        ticket_dict = {
            "id":          None,
            "title":       title,
            "description": description,
            "category":    category,
            "priority":    priority,
        }

        pipeline_output = run_pipeline(ticket_dict, retriever)
        response_time   = pipeline_output["response_time"]

        # Build resolution text for DB
        resolution_steps = pipeline_output["resolution"].get("steps", [])
        resolution_text  = "\n".join(
            f"{s['step']}. {s['text']} [Source: {s['source_id']}]"
            for s in resolution_steps
        )

        # Save ticket
        ticket_id = insert_ticket(
            customer_name, email, title, description,
            category, severity, priority,
            round(confidence, 2),
            resolution=resolution_text,
            response_time=response_time
        )

        # Save RAG result
        retrieved_ids = [d["id"] for d in pipeline_output["retrieved_documents"]]
        save_rag_result(
            ticket_id,
            pipeline_output["analysis"]["query"],
            retrieved_ids,
            resolution_text,
            response_time
        )

        result = {
            "ticket_id":        ticket_id,
            "category":         category,
            "confidence":       round(confidence, 2),
            "severity":         severity,
            "priority":         priority,
            "response_time":    response_time,
            "workflow":         pipeline_output["workflow_status"],
            "retrieved_docs":   pipeline_output["retrieved_documents"],
            "resolution":       pipeline_output["resolution"],
            "retrieval_accuracy": round(SEED_RETRIEVAL_ACCURACY * 100, 0),
            "resolution_rate":    round(SEED_RESOLUTION_RATE * 100, 0),
        }

    return render_template("index.html", result=result, current_user=current_user)


@app.route("/dashboard")
@login_required
def dashboard():
    current_user = get_current_user()
    stats = get_dashboard_stats()
    return render_template(
        "dashboard.html",
        current_user=current_user,
        **stats,
    )


@app.route("/ai-agent")
@login_required
def ai_agent():
    current_user = get_current_user()
    return render_template(
        "ai_agent.html",
        current_user=current_user,
        kb_count=KB_COUNT,
        kb_categories=KB_CATEGORIES,
    )


# ──────────────────────────────────────────────
# API Endpoints
# ──────────────────────────────────────────────

@app.route("/api/rag-query", methods=["POST"])
@login_required
def api_rag_query():
    """
    JSON endpoint used by the AI Agent chat interface.
    Body: { "query": "..." }
    Returns: analysis + retrieved docs + resolution steps
    """
    data  = request.get_json(force=True)
    query = data.get("query", "").strip()
    if not query:
        return jsonify({"error": "Query is required."}), 400

    ticket_dict = {
        "id":          None,
        "title":       query,
        "description": query,
        "category":    "General",
        "priority":    "Medium",
    }

    pipeline_output = run_pipeline(ticket_dict, retriever)

    return jsonify({
        "keywords":  pipeline_output["analysis"]["keywords"],
        "retrieved": pipeline_output["retrieved_documents"],
        "steps":     pipeline_output["resolution"].get("steps", []),
        "status":    pipeline_output["resolution"]["status"],
        "response_time": pipeline_output["response_time"],
    })


@app.route("/api/ticket/<int:ticket_id>/resolve", methods=["POST"])
@login_required
def api_resolve_ticket(ticket_id):
    """Mark a ticket as resolved and return updated counts."""
    update_ticket_status(ticket_id, "Resolved")
    # Return fresh counts so the UI can update stats live
    stats = get_dashboard_stats()
    return jsonify({
        "success":         True,
        "ticket_id":       ticket_id,
        "status":          "Resolved",
        "resolved":        stats["resolved"],
        "open_tickets":    stats["open_tickets"],
        "resolution_rate": stats["resolution_rate"],
    })


@app.route("/api/ticket/<int:ticket_id>")
@login_required
def api_get_ticket(ticket_id):
    """Return ticket JSON."""
    row = get_ticket_by_id(ticket_id)
    if not row:
        return jsonify({"error": "Ticket not found."}), 404
    return jsonify(dict(row))


@app.route("/api/stats")
@login_required
def api_stats():
    """Return dashboard stats as JSON."""
    stats = get_dashboard_stats()
    # sqlite Row objects aren't JSON serialisable; convert
    stats["category_data"] = [dict(r) for r in stats["category_data"]]
    stats["priority_data"] = [dict(r) for r in stats["priority_data"]]
    stats["severity_data"] = [dict(r) for r in stats["severity_data"]]
    stats["recent_tickets"] = [dict(r) for r in stats["recent_tickets"]]
    return jsonify(stats)


# ──────────────────────────────────────────────
# Error handlers
# ──────────────────────────────────────────────

@app.errorhandler(404)
def not_found(e):
    return render_template("login.html", error="Page not found (404)."), 404


@app.errorhandler(500)
def server_error(e):
    return render_template("login.html", error=f"Server error: {e}"), 500


# ──────────────────────────────────────────────
# Run
# ──────────────────────────────────────────────

if __name__ == "__main__":
    app.run(debug=True, port=5000)
>>>>>>> 3a451190ad8d366b56c9c3829c7600740b7b98f5
