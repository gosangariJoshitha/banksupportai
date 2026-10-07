import json
import math
import re
from collections import Counter
from pathlib import Path


KB_PATH = Path(__file__).parent / "knowledge_base" / "banking_knowledge.json"
with KB_PATH.open("r", encoding="utf-8") as f:
    KNOWLEDGE_BASE = json.load(f)


class BankingDiagnosisAgent:
    KEYWORDS = {
        "UPI": ["upi", "google pay", "gpay", "phonepe", "paytm", "upi payment"],
        "ATM": ["atm", "cash withdrawal", "cash not received", "cash machine"],
        "Debit Card": ["debit card", "card payment", "pos", "card declined"],
        "Credit Card": ["credit card", "credit card payment"],
        "Authentication": ["password", "forgot password", "pin", "login", "sign in"],
        "Net Banking": ["net banking", "internet banking", "online banking"],
        "Fund Transfer": ["transfer", "neft", "rtgs", "imps", "beneficiary"],
        "Fraud": ["fraud", "unauthorized", "unknown transaction", "not my transaction",
                  "someone used my card", "suspicious transaction"],
        "Account": ["account", "statement", "balance", "bank account"]
    }

    def analyze(self, text):
        value = (text or "").lower()
        scores = {}
        for category, words in self.KEYWORDS.items():
            scores[category] = sum(1 for word in words if word in value)

        category = max(scores, key=scores.get) if max(scores.values(), default=0) else "General Banking"
        matched = scores.get(category, 0)
        confidence = min(0.62 + matched * 0.09, 0.96)

        if category == "Fraud":
            risk = "HIGH"
        elif any(x in value for x in ["money deducted", "amount debited", "cash not received",
                                      "transaction failed", "transaction pending"]):
            risk = "MEDIUM"
        else:
            risk = "LOW"

        return {
            "category": category,
            "diagnosis": f"Banking issue classified as {category}",
            "confidence": round(confidence, 2),
            "risk": risk
        }


class BankingRetrievalAgent:
    def __init__(self):
        self.documents = [
            item["title"] + " " + item["category"] + " " + item["content"]
            for item in KNOWLEDGE_BASE
        ]

    @staticmethod
    def _tokenize(text):
        stopwords = {"my", "the", "a", "an", "is", "was", "in", "to", "of", "and", "or", "for", "with", "on", "at", "by", "from", "it", "this", "that", "but", "be", "are", "have", "has", "had"}
        tokens = re.findall(r"\b[a-z0-9]+\b", (text or "").lower())
        return [t for t in tokens if t not in stopwords]

    @staticmethod
    def _tfidf_scores(query, document):
        query_tokens = BankingRetrievalAgent._tokenize(query)
        doc_tokens = BankingRetrievalAgent._tokenize(document)
        if not query_tokens or not doc_tokens:
            return 0.0

        doc_term_counts = Counter(doc_tokens)
        query_counts = Counter(query_tokens)

        overlap = sum(min(query_counts[token], doc_term_counts[token]) for token in set(query_counts) & set(doc_term_counts))
        if overlap == 0:
            return 0.0

        query_coverage = overlap / len(set(query_tokens))
        doc_density = overlap / len(set(doc_tokens))
        
        score = 0.70 * query_coverage + 0.30 * doc_density
        return min(0.98, round(score, 4))

    def search(self, query):
        best_index = 0
        best_score = 0.0

        for index, document in enumerate(self.documents):
            score = self._tfidf_scores(query, document)
            if score > best_score:
                best_score = score
                best_index = index

        return {
            "article": KNOWLEDGE_BASE[best_index],
            "similarity": best_score
        }


class BankingResolutionAgent:
    def generate(self, diagnosis, article, query):
        content = article["content"]
        steps = [s.strip() for s in re.split(r"\.\s+", content) if s.strip()]
        response = (
            f"We identified your query as a {diagnosis['category']} issue. "
            "Please use the following safe support steps and only use official bank channels."
        )
        return {"response": response, "steps": steps}


class ValidationAgent:
    def validate(self, diagnosis_confidence, retrieval_similarity, number_of_steps, risk, threshold=75.0):
        completeness = min(number_of_steps / 4, 1.0)
        confidence = (
            diagnosis_confidence * 0.40
            + retrieval_similarity * 0.45
            + completeness * 0.15
        )
        confidence = round(confidence * 100, 2)

        if risk == "HIGH":
            status = "ESCALATE"
        elif confidence >= threshold:
            status = "AUTO_RESOLVE"
        else:
            status = "ESCALATE"

        return {
            "confidence": confidence,
            "risk": risk,
            "status": status,
            "reason": "High-risk banking issue" if risk == "HIGH"
                      else ("Confidence threshold met" if status == "AUTO_RESOLVE"
                            else f"Confidence below threshold ({confidence}% < {threshold}%)")
        }


class EscalationAgent:
    def should_escalate(self, validation):
        return validation["status"] == "ESCALATE"


class BankSupportAI:
    def __init__(self, threshold=75.0):
        self.diagnosis_agent = BankingDiagnosisAgent()
        self.retrieval_agent = BankingRetrievalAgent()
        self.resolution_agent = BankingResolutionAgent()
        self.validation_agent = ValidationAgent()
        self.escalation_agent = EscalationAgent()
        self.threshold = threshold

    def process_query(self, query):
        diagnosis = self.diagnosis_agent.analyze(query)
        retrieval = self.retrieval_agent.search(query)
        resolution = self.resolution_agent.generate(
            diagnosis, retrieval["article"], query
        )
        validation = self.validation_agent.validate(
            diagnosis["confidence"],
            retrieval["similarity"],
            len(resolution["steps"]),
            diagnosis["risk"],
            threshold=self.threshold
        )
        escalation = self.escalation_agent.should_escalate(validation)

        return {
            "diagnosis": diagnosis,
            "retrieval": retrieval,
            "resolution": resolution,
            "validation": validation,
            "escalation": escalation
        }

