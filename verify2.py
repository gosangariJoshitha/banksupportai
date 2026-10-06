import sys, json

print("Step 1: config")
from config import KB_PATH, TOP_K, MIN_RELEVANCE
print("  KB_PATH:", KB_PATH, "  TOP_K:", TOP_K)

print("Step 2: DB + JWT")
from database import create_tables, create_user, login_user, generate_token, verify_token
create_tables()
tok = generate_token(1, "t@b.com", "agent")
p   = verify_token(tok)
assert p and p["email"] == "t@b.com"
print("  JWT OK")

print("Step 3: Loading KB retriever (may take a few seconds)…")
from rag.retriever import KnowledgeRetriever
r = KnowledgeRetriever(KB_PATH)
print(f"  {len(r.documents)} articles indexed")

print("Step 4: KB search")
docs = r.search("atm cash not dispensed account debited", top_k=2, min_score=0.01)
print(f"  Got {len(docs)} results")
for d in docs:
    print(f"    {d['id']}: {d['title']}  score={d['score']:.4f}")

print("Step 5: RAG pipeline")
from rag.pipeline import run_pipeline
ticket = {"id":1,"title":"ATM not dispensing cash","description":"ATM swallowed card did not give cash account debited","category":"ATM","priority":"P1"}
out = run_pipeline(ticket, r)
print(f"  Status={out['resolution']['status']}  Steps={len(out['resolution']['steps'])}  Time={out['response_time']}s")

print("Step 6: Flask app routes")
from app import app
routes = sorted([str(rule) for rule in app.url_map.iter_rules()])
print(f"  {len(routes)} routes registered")
for rt in routes:
    print(f"    {rt}")

print("\nALL OK – run: python app.py")
