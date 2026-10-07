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


@app.route("/api/settings", methods=["GET", "POST"])
def settings_route():
    if request.method == "POST":
        data = request.get_json(silent=True) or {}
        new_threshold = float(data.get("threshold", 75.0))
        config.AUTO_RESOLVE_THRESHOLD = new_threshold
        bank_ai.threshold = new_threshold
        return jsonify({"success": True, "message": f"Threshold updated to {new_threshold}%"})

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


@app.route("/api/health")
def health():
    return jsonify({"status": "running", "service": "BankSupport AI Milestone 3"})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
