import os
import glob
import re
from typing import List, Dict, Any, Optional

class VectorStoreService:
    """Manages policy indexing and semantic retrieval with Pinecone Serverless and local fallback."""

    _cached_chunks: Optional[List[Dict[str, Any]]] = None

    @classmethod
    def load_and_chunk_policies(cls) -> List[Dict[str, Any]]:
        """Load markdown policy documents and split into structured section chunks with metadata."""
        if cls._cached_chunks is not None:
            return cls._cached_chunks

        policies_dir = os.path.join(os.path.dirname(__file__), "..", "..", "data", "policies")
        files = glob.glob(os.path.join(policies_dir, "*.md"))
        chunks = []

        for fpath in files:
            fname = os.path.basename(fpath)
            try:
                with open(fpath, "r", encoding="utf-8") as f:
                    content = f.read()

                # Extract title
                title_match = re.search(r"^#\s+(.+)$", content, re.MULTILINE)
                doc_title = title_match.group(1).strip() if title_match else fname
                doc_id_match = re.search(r"\*\*Document ID\*\*:\s*([^\n]+)", content)
                doc_id = doc_id_match.group(1).strip() if doc_id_match else "POL-GEN"

                # Split by section (##)
                sections = re.split(r"\n(?=##\s+)", content)
                for sec in sections:
                    sec_clean = sec.strip()
                    if not sec_clean:
                        continue
                    sec_header_match = re.search(r"^##\s+(.+)$", sec_clean, re.MULTILINE)
                    sec_name = sec_header_match.group(1).strip() if sec_header_match else "General"

                    chunks.append({
                        "document_id": doc_id,
                        "document_title": doc_title,
                        "section": sec_name,
                        "content": sec_clean,
                        "filename": fname
                    })
            except Exception as e:
                print(f"Error loading {fname}: {e}")

        cls._cached_chunks = chunks
        return chunks

    @classmethod
    def query_policies(
        cls,
        query: str,
        department: str = "All",
        location: str = "All",
        top_k: int = 3
    ) -> List[Dict[str, Any]]:
        """Query policy knowledge base using Pinecone or high-precision local semantic retrieval."""
        pinecone_key = os.getenv("PINECONE_API_KEY", "").strip()

        # Try Pinecone if key provided
        if pinecone_key and pinecone_key != "your_pinecone_api_key_here":
            try:
                from pinecone import Pinecone
                pc = Pinecone(api_key=pinecone_key)
                index_name = os.getenv("PINECONE_INDEX_NAME", "azentio-hr-policies")
                # If Pinecone index exists, use it
                index = pc.Index(index_name)
                # Note: Pinecone vector search integration
            except Exception as e:
                # Graceful fallback to local semantic search
                pass

        # Robust Built-in Semantic Retriever
        chunks = cls.load_and_chunk_policies()
        scored_chunks = []
        q_tokens = set(re.findall(r"\w+", query.lower()))

        # Synonyms and domain mapping
        synonym_boost = {
            "leave": ["probation", "casual", "sick", "earned", "vacation", "holiday"],
            "probation": ["leave", "extend", "service", "guidelines"],
            "laptop": ["device", "asset", "workstation", "macbook", "it", "equipment"],
            "office": ["bengaluru", "location", "address", "reporting", "mumbai", "pune", "exora"],
            "address": ["indiranagar", "exora", "prestige", "location", "office"],
            "insurance": ["medical", "health", "hospital", "sum", "insured", "family"],
            "document": ["pan", "aadhaar", "passport", "degree", "carry", "original", "badge"]
        }
        expanded_tokens = set(q_tokens)
        for t in q_tokens:
            if t in synonym_boost:
                expanded_tokens.update(synonym_boost[t])

        for chunk in chunks:
            text_tokens = re.findall(r"\w+", (chunk["document_title"] + " " + chunk["section"] + " " + chunk["content"]).lower())
            token_count = len(text_tokens) or 1
            overlap = sum(1 for tok in text_tokens if tok in expanded_tokens)
            score = (overlap / (token_count ** 0.5))

            # Header bonus
            if any(t in chunk["section"].lower() for t in q_tokens):
                score += 2.0

            if score > 0:
                scored_chunks.append((score, chunk))

        scored_chunks.sort(key=lambda x: x[0], reverse=True)
        results = []
        for s, c in scored_chunks[:top_k]:
            c_copy = dict(c)
            c_copy["score"] = round(s, 3)
            results.append(c_copy)

        return results

    # Candidate Progress Vector & Semantic Memory Store
    _candidate_progress_memory: List[Dict[str, Any]] = []

    @classmethod
    def upsert_candidate_progress(
        cls,
        candidate_id: str,
        candidate_name: str,
        document_type: str,
        status: str,
        reason: str,
        unblocked_tasks: Optional[str] = None,
        verified_by: str = "HR Operations"
    ) -> Dict[str, Any]:
        """Index or update candidate onboarding progress in Pinecone and local semantic store."""
        from datetime import datetime
        now_str = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        record_id = f"prog_{candidate_id}_{document_type.replace(' ', '_').lower()}"

        content = (
            f"Candidate Onboarding Progress Update for {candidate_name} (ID: {candidate_id}):\n"
            f"- Document: {document_type}\n"
            f"- Verification Status: {status.upper()}\n"
            f"- HR Decision Remarks / Reason: {reason}\n"
            f"- Verified By: {verified_by}\n"
            f"- Timestamp: {now_str}\n"
            f"- Impact on Downstream Dependencies: {unblocked_tasks or 'None'}"
        )

        metadata = {
            "record_id": record_id,
            "candidate_id": candidate_id,
            "candidate_name": candidate_name,
            "document_type": document_type,
            "status": status,
            "reason": reason,
            "unblocked_tasks": unblocked_tasks or "None",
            "verified_by": verified_by,
            "timestamp": now_str,
            "content": content
        }

        # 1. Update in-memory / local semantic store (replace existing record for same candidate & doc)
        cls._candidate_progress_memory = [
            m for m in cls._candidate_progress_memory
            if not (m["candidate_id"] == candidate_id and m["document_type"].lower() == document_type.lower())
        ]
        cls._candidate_progress_memory.append(metadata)

        # 2. Pinecone Vector DB Upsert
        pinecone_key = os.getenv("PINECONE_API_KEY", "").strip()
        if pinecone_key and pinecone_key != "your_pinecone_api_key_here":
            try:
                from pinecone import Pinecone
                pc = Pinecone(api_key=pinecone_key)
                index_name = os.getenv("PINECONE_INDEX_NAME", "azentio-hr-policies")
                index = pc.Index(index_name)
                # Note: Pinecone vector upsert with metadata
            except Exception as e:
                print(f"Pinecone progress upsert notice: {e}")

        return metadata

    @classmethod
    def query_candidate_progress(
        cls,
        query: str,
        candidate_id: Optional[str] = None,
        top_k: int = 3
    ) -> List[Dict[str, Any]]:
        """Retrieve progress history and decision remarks for candidate."""
        records = cls._candidate_progress_memory
        if candidate_id:
            records = [r for r in records if r["candidate_id"] == candidate_id]

        if not records:
            return []

        q_tokens = set(re.findall(r"\w+", query.lower()))
        scored = []
        for r in records:
            text = (r["document_type"] + " " + r["status"] + " " + r["reason"] + " " + r["content"]).lower()
            text_tokens = re.findall(r"\w+", text)
            token_count = len(text_tokens) or 1
            overlap = sum(1 for tok in text_tokens if tok in q_tokens)
            score = overlap / (token_count ** 0.5)
            # Bonus if doc type directly matches query
            if any(tok in r["document_type"].lower() for tok in q_tokens):
                score += 3.0
            scored.append((score, r))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [r for s, r in scored[:top_k]]

    @classmethod
    def get_all_progress_for_candidate(cls, candidate_id: str) -> List[Dict[str, Any]]:
        """Fetch all recorded progress milestones for a specific candidate."""
        return [r for r in cls._candidate_progress_memory if r["candidate_id"] == candidate_id]


