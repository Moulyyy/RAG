import os
import sys
import time
import re
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv
from google import genai
import chromadb

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')

load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")


class BookVectorStore:
    def __init__(self, persist_dir: str = "./chroma_db", collection_name: str = "book_knowledge"):
        """
        Configurable persistent ChromaDB vector store.
        collection_name allows storing different books in different collections.
        """
        self.persist_dir = persist_dir
        self.collection_name = collection_name
        self.client = genai.Client(api_key=api_key)
        self.chroma_client = chromadb.PersistentClient(path=persist_dir)
        self.collection = self.chroma_client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"}
        )
        self._query_cache: Dict[str, List[float]] = {}

    def reset_collection(self):
        """Wipes the current collection so you can replace the document cleanly."""
        try:
            self.chroma_client.delete_collection(self.collection_name)
        except Exception:
            pass
        self.collection = self.chroma_client.get_or_create_collection(
            name=self.collection_name,
            metadata={"hnsw:space": "cosine"}
        )
        print(f"Collection '{self.collection_name}' has been reset.")

    def get_batch_embeddings(self, texts: List[str]) -> List[List[float]]:
        """
        Generates embeddings for multiple chunks in ONE single API call.
        Includes automatic retry for Google Free Tier rate limits (100 embeddings/min).
        """
        for attempt in range(8):
            try:
                response = self.client.models.embed_content(
                    model="gemini-embedding-001",
                    contents=texts,
                )
                return [emb.values for emb in response.embeddings]
            except Exception as e:
                err_str = str(e)
                if "429" in err_str or "RESOURCE_EXHAUSTED" in err_str:
                    wait_time = 32
                    m = re.search(r"retryDelay': '(\d+)s", err_str)
                    if m:
                        wait_time = int(m.group(1)) + 2

                    print(f"\n[Quota limit: 100/min reached] Pausing {wait_time}s for Google API window reset...")
                    for s in range(wait_time, 0, -5):
                        print(f"Resuming in {s}s...", end="\r", flush=True)
                        time.sleep(min(5, s))
                    print("Resuming embedding now...                              ")
                else:
                    raise e
        raise RuntimeError("Failed to get embeddings after multiple retries.")

    def add_chunks_batched(self, chunks: List[Dict[str, Any]], batch_size: int = 40):
        """
        Embeds and stores chunks with checkpointing:
        Already indexed chunks are preserved so you can resume anytime without redoing work!
        """
        if not chunks:
            print("No chunks to add.")
            return

        # Check existing IDs to enable instant resume
        existing = self.collection.get()
        existing_ids = set(existing["ids"]) if existing and "ids" in existing else set()

        chunks_to_index = [c for c in chunks if c["chunk_id"] not in existing_ids]
        total_all = len(chunks)
        already_done = len(chunks) - len(chunks_to_index)

        if already_done > 0:
            print(f"Resume checkpoint: {already_done}/{total_all} chunks already in ChromaDB. Processing remaining {len(chunks_to_index)} chunks...")

        if not chunks_to_index:
            print("All chunks are already indexed!")
            return

        total_remaining = len(chunks_to_index)

        for i in range(0, total_remaining, batch_size):
            batch = chunks_to_index[i:i + batch_size]
            batch_texts = [c["text"] for c in batch]
            batch_ids = [c["chunk_id"] for c in batch]
            batch_metadatas = [c["metadata"] for c in batch]

            # Generate embeddings for the batch
            batch_vectors = self.get_batch_embeddings(batch_texts)

            self.collection.upsert(
                documents=batch_texts,
                embeddings=batch_vectors,
                metadatas=batch_metadatas,
                ids=batch_ids
            )

            current_done = already_done + min(i + batch_size, total_remaining)
            print(f"Progress: [{current_done}/{total_all}] chunks indexed ({int(current_done/total_all*100)}%)...")
            time.sleep(1.0)

        print("All chunks successfully indexed into ChromaDB!")

    def query_similar(self, query: str, top_k: int = 4) -> List[Dict[str, Any]]:
        """Finds closest chunks for a query with in-memory embedding caching."""
        clean_key = query.strip().lower()
        if clean_key in self._query_cache:
            query_vector = self._query_cache[clean_key]
        else:
            response = self.client.models.embed_content(
                model="gemini-embedding-001",
                contents=query,
            )
            query_vector = response.embeddings[0].values
            if len(self._query_cache) > 200:
                self._query_cache.clear()
            self._query_cache[clean_key] = query_vector

        results = self.collection.query(
            query_embeddings=[query_vector],
            n_results=top_k
        )

        matched_chunks = []
        if results and results["documents"]:
            docs = results["documents"][0]
            metas = results["metadatas"][0]
            distances = results["distances"][0] if "distances" in results and results["distances"] else [0] * len(docs)

            for doc, meta, dist in zip(docs, metas, distances):
                matched_chunks.append({
                    "text": doc,
                    "metadata": meta,
                    "similarity_score": 1.0 - dist
                })

        return matched_chunks

    def count(self) -> int:
        """Returns number of chunks currently stored."""
        return self.collection.count()


if __name__ == "__main__":
    store = BookVectorStore()
    print(f"Total chunks in ChromaDB: {store.count()}")
