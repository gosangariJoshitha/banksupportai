"""
RAG Pipeline – orchestrates all 4 steps of the resolution workflow.

Step 1 : Ticket Analysis & Query Generation   (analyzer.py)
Step 2 : Knowledge Base Retrieval             (retriever.py)
Step 3 : Context Augmentation                 (generator.py)
Step 4 : Resolution Generation                (generator.py)
"""

import time
from config import TOP_K, MIN_RELEVANCE
from rag.analyzer  import analyze_ticket
from rag.retriever import KnowledgeRetriever
from rag.generator import build_context, generate_resolution


def run_pipeline(ticket: dict, retriever: KnowledgeRetriever) -> dict:
    """
    Run the full RAG pipeline for a single ticket.

    Parameters
    ----------
    ticket    : dict with id, title, description, category, priority
    retriever : initialised KnowledgeRetriever instance

    Returns
    -------
    dict with workflow_status, analysis, retrieved_documents,
         context, resolution, response_time_seconds
    """
    start_time = time.time()

    workflow_status = {
        "ticket_analysis":       "pending",
        "knowledge_retrieval":   "pending",
        "context_augmentation":  "pending",
        "response_generation":   "pending",
    }

    # --------------------------------------------------
    # Step 1 – Ticket Analysis
    # --------------------------------------------------
    analysis = analyze_ticket(ticket)
    workflow_status["ticket_analysis"] = "completed"

    # --------------------------------------------------
    # Step 2 – Knowledge Base Retrieval
    # --------------------------------------------------
    retrieved_docs = retriever.search(
        analysis["query"],
        top_k=TOP_K,
        min_score=MIN_RELEVANCE,
    )
    workflow_status["knowledge_retrieval"] = "completed"

    # --------------------------------------------------
    # Step 3 – Context Augmentation
    # --------------------------------------------------
    context = build_context(retrieved_docs)
    workflow_status["context_augmentation"] = "completed"

    # --------------------------------------------------
    # Step 4 – Resolution Generation
    # --------------------------------------------------
    resolution = generate_resolution(ticket, retrieved_docs)
    workflow_status["response_generation"] = "completed"

    response_time = round(time.time() - start_time, 2)

    return {
        "workflow_status":     workflow_status,
        "analysis":            analysis,
        "retrieved_documents": retrieved_docs,
        "context":             context,
        "resolution":          resolution,
        "response_time":       response_time,
    }
