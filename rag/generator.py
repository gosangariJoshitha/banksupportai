"""
RAG Step 3 & 4 – Context Augmentation + Resolution Generation
Builds the context string and generates a structured resolution.
"""

import re


# ------------------------------------------------------------------
# Step 3 – Context Augmentation
# ------------------------------------------------------------------

def build_context(results: list) -> str:
    """
    Convert retrieved KB articles into a formatted context block
    for the resolution generator (or a future LLM prompt).
    """
    if not results:
        return ""

    context = ""
    for doc in results:
        context += (
            f"\nSOURCE: {doc['id']}\n"
            f"TITLE: {doc['title']}\n"
            f"CATEGORY: {doc['category']}\n"
            f"RELEVANCE: {doc['score']:.2f}\n"
            f"{doc['content']}\n"
            f"{'=' * 60}\n"
        )
    return context


# ------------------------------------------------------------------
# Step 4 – Resolution Generation
# ------------------------------------------------------------------

def _extract_steps(content: str) -> list:
    """Pull numbered steps (1. … 2. … etc.) from KB content."""
    lines  = content.split("\n")
    steps  = []
    buffer = []

    for line in lines:
        stripped = line.strip()
        if re.match(r"^\d+\.", stripped):
            if buffer:
                steps.append(" ".join(buffer))
                buffer = []
            buffer.append(re.sub(r"^\d+\.\s*", "", stripped))
        elif buffer and stripped:
            buffer.append(stripped)

    if buffer:
        steps.append(" ".join(buffer))

    return steps


def generate_resolution(ticket: dict, retrieved_docs: list) -> dict:
    """
    Generate a structured resolution from retrieved KB articles.

    Returns
    -------
    dict with:
        status       : "RESOLVED" | "INSUFFICIENT_KNOWLEDGE"
        steps        : list of {step, text, source_id, source_title}
        sources_used : list of KB article ids
        prompt       : the conceptual LLM prompt (for display)
    """
    if not retrieved_docs:
        return {
            "status":       "INSUFFICIENT_KNOWLEDGE",
            "steps":        [],
            "sources_used": [],
            "message":      "No sufficiently relevant knowledge-base articles were found. Please escalate to a human agent.",
            "prompt":       "",
        }

    context = build_context(retrieved_docs)

    # Build the conceptual prompt (shown in UI)
    prompt = (
        "SYSTEM: You are a banking support assistant. "
        "Use only the supplied knowledge-base information. "
        "Do not invent bank-specific policies, fees, or numbers.\n\n"
        f"TICKET:\nTitle: {ticket.get('title', '')}\n"
        f"Description: {ticket.get('description', '')}\n"
        f"Priority: {ticket.get('priority', '')}\n\n"
        f"KNOWLEDGE BASE:\n{context}\n"
        "INSTRUCTIONS:\n"
        "1. Use the knowledge base as the primary source.\n"
        "2. Do not invent company-specific policies.\n"
        "3. Provide numbered troubleshooting steps.\n"
        "4. Explain the likely cause when possible.\n"
        "5. If the KB lacks enough info, state that additional investigation is required.\n"
        "6. Keep the response concise and suitable for a support agent.\n\n"
        "Generate the recommended resolution."
    )

    # --- Resolution generation from KB content ---
    steps        = []
    sources_used = []
    step_number  = 1

    for doc in retrieved_docs:
        sources_used.append(doc["id"])
        extracted = _extract_steps(doc["content"])
        for step_text in extracted:
            steps.append({
                "step":         step_number,
                "text":         step_text,
                "source_id":    doc["id"],
                "source_title": doc["title"],
            })
            step_number += 1

    # Fallback if no numbered steps were extracted
    if not steps:
        for doc in retrieved_docs:
            # Take first two sentences of content
            sentences = [s.strip() for s in doc["content"].split(".") if s.strip()][:2]
            for sentence in sentences:
                steps.append({
                    "step":         step_number,
                    "text":         sentence + ".",
                    "source_id":    doc["id"],
                    "source_title": doc["title"],
                })
                step_number += 1

    # Add a universal closing step
    steps.append({
        "step":         step_number,
        "text":         "If the issue is not resolved after following the above steps, escalate the case to the relevant department and provide the customer with a reference number.",
        "source_id":    "SYS",
        "source_title": "System Policy",
    })

    return {
        "status":       "RESOLVED",
        "steps":        steps,
        "sources_used": sources_used,
        "message":      f"Resolution generated from {len(retrieved_docs)} knowledge base article(s).",
        "prompt":       prompt,
    }
