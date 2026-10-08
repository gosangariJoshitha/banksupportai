import os
<<<<<<< HEAD
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent / ".env")

JIRA_URL = os.getenv("JIRA_URL", "").rstrip("/")
JIRA_EMAIL = os.getenv("JIRA_EMAIL", "")
JIRA_API_TOKEN = os.getenv("JIRA_API_TOKEN", "")
JIRA_PROJECT_KEY = os.getenv("JIRA_PROJECT_KEY", "BANK")

SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_EMAIL = os.getenv("SMTP_EMAIL", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")

AUTO_RESOLVE_THRESHOLD = float(os.getenv("AUTO_RESOLVE_THRESHOLD", "75.0"))
JIRA_SIMULATION_MODE = os.getenv("JIRA_SIMULATION_MODE", "true").lower() in ("true", "1", "yes")

=======

# -------------------------------------------
# Application Configuration
# -------------------------------------------

SECRET_KEY = os.environ.get("SECRET_KEY", "supportpilot-bank-secret-2024-xk9z")
JWT_SECRET  = os.environ.get("JWT_SECRET",  "supportpilot-jwt-secret-2024-xk9z")

# JWT expiry (seconds)
JWT_EXPIRY_SECONDS = 3600  # 1 hour

DATABASE = "tickets.db"

# Knowledge base path
KB_PATH = "knowledge_base_bank_support_300_fraud-1 (2).json"

# Retrieval settings
TOP_K          = 3
MIN_RELEVANCE  = 0.05   # lower threshold for banking KB

# Metrics (computed dynamically; seed values for display)
SEED_RETRIEVAL_ACCURACY = 0.92
SEED_RESOLUTION_RATE    = 0.78
SEED_AVG_RESPONSE_TIME  = 3.2
>>>>>>> 3a451190ad8d366b56c9c3829c7600740b7b98f5
