import os
import glob
import re
from typing import List, Dict, Any
from dotenv import load_dotenv

# Load credentials
load_dotenv()

def index_all_policies_to_pinecone():
    """Index all markdown policy handbooks into Pinecone Serverless vector index."""
    pinecone_key = os.getenv("PINECONE_API_KEY", "").strip()
    if not pinecone_key or pinecone_key == "your_pinecone_api_key_here":
        print("Pinecone API key not provided, skipping remote vector indexing.")
        return False

    try:
        from pinecone import Pinecone
        pc = Pinecone(api_key=pinecone_key)
        index_name = os.getenv("PINECONE_INDEX_NAME", "azentio-hr-policies")
        index = pc.Index(index_name)

        # 1. Load policy chunks
        policies_dir = os.path.join(os.path.dirname(__file__), "..", "..", "data", "policies")
        files = glob.glob(os.path.join(policies_dir, "*.md"))
        chunks = []

        for fpath in files:
            fname = os.path.basename(fpath)
            with open(fpath, "r", encoding="utf-8") as f:
                content = f.read()

            title_match = re.search(r"^#\s+(.+)$", content, re.MULTILINE)
            doc_title = title_match.group(1).strip() if title_match else fname
            doc_id_match = re.search(r"\*\*Document ID\*\*:\s*([^\n]+)", content)
            doc_id = doc_id_match.group(1).strip() if doc_id_match else "POL-GEN"

            sections = re.split(r"\n(?=##\s+)", content)
            for idx, sec in enumerate(sections):
                sec_clean = sec.strip()
                if not sec_clean:
                    continue
                sec_header_match = re.search(r"^##\s+(.+)$", sec_clean, re.MULTILINE)
                sec_name = sec_header_match.group(1).strip() if sec_header_match else f"Section {idx+1}"

                clean_id = f"{doc_id}_{idx}".replace(" ", "_").replace("/", "_").lower()
                chunks.append({
                    "id": clean_id,
                    "document_id": doc_id,
                    "document_title": doc_title,
                    "section": sec_name,
                    "content": sec_clean,
                    "filename": fname
                })

        print(f"Embedding {len(chunks)} policy chunks with Pinecone multilingual-e5-large...")
        texts_to_embed = [f"{c['document_title']} - {c['section']}:\n{c['content']}" for c in chunks]

        # Embed using Pinecone inference
        embeddings = pc.inference.embed(
            model="multilingual-e5-large",
            inputs=texts_to_embed,
            parameters={"input_type": "passage", "truncate": "END"}
        )

        vectors_to_upsert = []
        for i, chunk in enumerate(chunks):
            vectors_to_upsert.append({
                "id": chunk["id"],
                "values": embeddings[i].values,
                "metadata": {
                    "document_id": chunk["document_id"],
                    "document_title": chunk["document_title"],
                    "section": chunk["section"],
                    "content": chunk["content"][:900], # Store section content
                    "filename": chunk["filename"],
                    "type": "policy"
                }
            })

        # Upsert in batches of 50
        batch_size = 50
        for b_start in range(0, len(vectors_to_upsert), batch_size):
            batch = vectors_to_upsert[b_start:b_start + batch_size]
            index.upsert(vectors=batch)

        print(f"[OK] Successfully indexed {len(vectors_to_upsert)} policy chunks into Pinecone index '{index_name}'!")
        return True

    except Exception as e:
        print(f"Error indexing to Pinecone: {e}")
        return False

if __name__ == "__main__":
    index_all_policies_to_pinecone()
