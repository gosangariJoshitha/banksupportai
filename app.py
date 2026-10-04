from flask import Flask, render_template, request
from classifier import classify_ticket
from database import create_table, insert_ticket
import sqlite3

app = Flask(__name__)

# Create database table
create_table()


# -----------------------------
# Severity Calculation
# -----------------------------
def calculate_severity(description):
    text = description.lower()

    high_keywords = [
        "fraud",
        "unauthorized",
        "unrecognized",
        "scam",
        "money deducted",
        "money was deducted",
        "cash not received",
        "did not receive cash",
        "cash was not received",
        "account blocked",
        "card stolen",
        "stolen card",
        "someone used my account",
        "someone is using my account"
    ]

    for keyword in high_keywords:
        if keyword in text:
            return "High"

    return "Medium"


# -----------------------------
# Priority Calculation
# -----------------------------
def calculate_priority(severity):

    if severity == "High":
        return "P1"

    elif severity == "Medium":
        return "P2"

    else:
        return "P3"


# -----------------------------
# Home / Create Ticket
# -----------------------------
@app.route("/", methods=["GET", "POST"])
def home():

    result = None

    if request.method == "POST":

        customer_name = request.form["customer_name"]
        email = request.form["email"]
        title = request.form["title"]
        description = request.form["description"]

        # AI Classification
        text_for_classification = title + " " + description

        category, confidence = classify_ticket(
            text_for_classification
        )

        # Severity
        severity = calculate_severity(description)

        # Priority
        priority = calculate_priority(severity)

        # Store ticket
        ticket_id = insert_ticket(
            customer_name,
            email,
            title,
            description,
            category,
            severity,
            priority,
            confidence
        )

        result = {
            "ticket_id": ticket_id,
            "category": category,
            "confidence": round(confidence, 2),
            "severity": severity,
            "priority": priority
        }

    return render_template(
        "index.html",
        result=result
    )


# -----------------------------
# Dashboard
# -----------------------------
@app.route("/dashboard")
def dashboard():

    conn = sqlite3.connect("tickets.db")
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Total tickets
    cursor.execute("""
        SELECT COUNT(*) 
        FROM tickets
    """)
    total = cursor.fetchone()[0]

    # Open tickets
    cursor.execute("""
        SELECT COUNT(*) 
        FROM tickets 
        WHERE status = 'Open'
    """)
    open_tickets = cursor.fetchone()[0]

    # High priority tickets
    cursor.execute("""
        SELECT COUNT(*) 
        FROM tickets 
        WHERE priority = 'P1'
    """)
    high_priority = cursor.fetchone()[0]

    # Resolved tickets
    cursor.execute("""
        SELECT COUNT(*) 
        FROM tickets 
        WHERE status = 'Resolved'
    """)
    resolved = cursor.fetchone()[0]

    # Category distribution
    cursor.execute("""
        SELECT category, COUNT(*) AS count
        FROM tickets
        GROUP BY category
        ORDER BY count DESC
    """)
    category_data = cursor.fetchall()

    # Priority distribution
    cursor.execute("""
        SELECT priority, COUNT(*) AS count
        FROM tickets
        GROUP BY priority
        ORDER BY priority
    """)
    priority_data = cursor.fetchall()

    # Severity distribution
    cursor.execute("""
        SELECT severity, COUNT(*) AS count
        FROM tickets
        GROUP BY severity
    """)
    severity_data = cursor.fetchall()

    # Recent tickets
    cursor.execute("""
        SELECT *
        FROM tickets
        ORDER BY ticket_id DESC
        LIMIT 10
    """)
    tickets = cursor.fetchall()

    conn.close()

    # Avoid division by zero
    if total > 0:
        resolution_rate = round((resolved / total) * 100, 1)
    else:
        resolution_rate = 0

    return render_template(
        "dashboard.html",

        total=total,
        open_tickets=open_tickets,
        high_priority=high_priority,
        resolved=resolved,

        resolution_rate=resolution_rate,

        category_data=category_data,
        priority_data=priority_data,
        severity_data=severity_data,

        tickets=tickets
    )


# -----------------------------
# Run Application
# -----------------------------
if __name__ == "__main__":
    app.run(debug=True)