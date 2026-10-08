"""
RAG Step 2 – Knowledge Base Retrieval
Uses TF-IDF + cosine similarity to find the most relevant KB articles.
"""

import json
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


class KnowledgeRetriever:
    """Loads the banking KB JSON and retrieves top-K relevant documents."""

    def __init__(self, kb_path: str):
        with open(kb_path, "r", encoding="utf-8") as f:
            kb_data = json.load(f)

        self.documents = kb_data.get("entries", [])

        # Build corpus: title + content for each document
        texts = [
            doc["title"] + " " + doc["content"]
            for doc in self.documents
        ]

        self.vectorizer = TfidfVectorizer(stop_words="english", max_features=5000)
        self.doc_vectors = self.vectorizer.fit_transform(texts)

    def search(self, query: str, top_k: int = 3, min_score: float = 0.05):
        """
        Return top_k documents most relevant to the query.

        Parameters
        ----------
        query     : search string (usually ticket title + description)
        top_k     : maximum results to return
        min_score : minimum cosine similarity threshold

        Returns
        -------
        list of dicts with id, title, category, content, score
        """
        query_vector = self.vectorizer.transform([query])
        scores = cosine_similarity(query_vector, self.doc_vectors)[0]
        ranked = scores.argsort()[::-1]

        results = []
        for idx in ranked[:top_k]:
            score = float(scores[idx])
            if score < min_score:
                continue
            doc = self.documents[idx]
            results.append({
                "id":       doc["id"],
                "title":    doc["title"],
                "category": doc.get("category", ""),
                "content":  doc["content"],
                "score":    round(score, 4),
            })

        return results
