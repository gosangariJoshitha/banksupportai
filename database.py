import sqlite3

DATABASE = "tickets.db"


def create_table():
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tickets (
            ticket_id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_name TEXT,
            email TEXT,
            title TEXT,
            description TEXT,
            category TEXT,
            severity TEXT,
            priority TEXT,
            confidence REAL,
            status TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.commit()
    conn.close()


def insert_ticket(customer_name, email, title, description,
                  category, severity, priority, confidence):

    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO tickets
        (customer_name, email, title, description,
         category, severity, priority, confidence, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        customer_name,
        email,
        title,
        description,
        category,
        severity,
        priority,
        confidence,
        "Open"
    ))

    conn.commit()
    ticket_id = cursor.lastrowid
    conn.close()

    return ticket_id


if __name__ == "__main__":
    create_table()
    print("Database and tickets table created successfully!")