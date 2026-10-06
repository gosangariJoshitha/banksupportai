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
