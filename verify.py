"""Quick smoke-test – run with: python verify.py"""

print("=" * 60)
print("SupportPilot Milestone 2 – Verification")
print("=" * 60)

# 1. Config
from config import SECRET_KEY, KB_PATH, JWT_SECRET, TOP_K, MIN_RELEVANCE
print("[OK] config.py loaded")

# 2. Database
from database import create_tables, create_user, login_user, generate_token, verify_token
create_tables()
print("[OK] database tables created/verified")

# 3. JWT round-trip
token = generate_token(1, "test@bank.com", "agent")
payload = verify_token(token)
assert payload is not None and payload["email"] == "test@bank.com"
print(f"[OK] JWT encode/decode works (user_id={payload['user_id']})")

# 4. User create + login
res = create_user("Test Agent", "verify_test@bank.com", "Test@1234", "agent")
if not res["success"] and "already" in res.get("error", ""):
    print("[OK] User already exists (re-run)")
else:
    print(f"[OK] User created (id={res.get('user_id')})")

login_res = login_user("verify_test@bank.com", "Test@1234")
assert login_res["success"], f"Login failed: {login_res}"
print(f"[OK] Login works, token starts with: {login_res['token'][:20]}…")

# 5. KB Retriever
from rag.retriever import KnowledgeRetriever
r = KnowledgeRetriever(KB_PATH)
print(f"[OK] Knowledge base loaded: {len(r.documents)} articles")

results = r.search("ATM cash not dispensed amount debited", top_k=3)
print(f"[OK] KB search returned {len(results)} results:")
for doc in results:
    print(f"     • {doc['id']}: {doc['title']} (score={doc['score']:.4f})")

# 6. Full RAG Pipeline
from rag.pipeline import run_pipeline
ticket = {
    "id":          99,
    "title":       "ATM did not dispense cash",
    "description": "I tried to withdraw Rs 5000 but the ATM did not give cash. My account was debited Rs 5000.",
    "category":    "ATM/Cash Issue",
    "priority":    "P1",
}
out = run_pipeline(ticket, r)
print(f"\n[OK] RAG pipeline completed in {out['response_time']}s")
print(f"     Workflow: {out['workflow_status']}")
print(f"     Retrieved: {len(out['retrieved_documents'])} docs")
print(f"     Resolution status: {out['resolution']['status']}")
print(f"     Resolution steps:  {len(out['resolution']['steps'])}")
if out["resolution"]["steps"]:
    step1 = out["resolution"]["steps"][0]
    print(f"     Step 1: {step1['text'][:80]}…")
    print(f"     Source: {step1['source_id']} – {step1['source_title']}")

# 7. Flask app import
from app import app
print(f"\n[OK] Flask app imported successfully")
print(f"     Registered routes: {len(list(app.url_map.iter_rules()))}")
for rule in sorted(app.url_map.iter_rules(), key=lambda r: r.rule):
    methods = ",".join(sorted(rule.methods - {"HEAD", "OPTIONS"}))
    print(f"     {methods:8} {rule.rule}")

print("\n" + "=" * 60)
print("ALL CHECKS PASSED – ready to run: python app.py")
print("=" * 60)
