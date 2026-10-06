import os

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
