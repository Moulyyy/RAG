import os
import sys
from typing import Dict, Any, List
from dotenv import load_dotenv
from google import genai
from vector_store import BookVectorStore

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')

load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")


class BookRAG:
    def __init__(self, vector_store: BookVectorStore = None):
        self.vector_store = vector_store or BookVectorStore()
        self.client = genai.Client(api_key=api_key)

    def answer_question(self, question: str, top_k: int = 3) -> Dict[str, Any]:
        """
        1. Retrieves top_k chunks from ChromaDB.
        2. Formats a context block with source and page citations.
        3. Calls Gemini 2.5 Flash to synthesize a grounded answer.
        """
        # Step 1: Semantic Retrieval
        retrieved_chunks = self.vector_store.query_similar(question, top_k=top_k)

        if not retrieved_chunks:
            return {
                "answer": "I couldn't find any relevant sections in the book for your question.",
                "sources": []
            }

        # Step 2: Assemble Context with Citations
        context_blocks = []
        sources = []
        for c in retrieved_chunks:
            meta = c["metadata"]
            source_citation = f"[{meta['source']}, Page {meta['page']}]"
            context_blocks.append(f"{source_citation}:\n\"{c['text']}\"")
            sources.append({
                "source": meta["source"],
                "page": meta["page"],
                "similarity": round(c["similarity_score"], 2),
                "excerpt": c["text"]
            })

        formatted_context = "\n\n".join(context_blocks)

        # Step 3: Prompt Engineering for Truthfulness, Citations & Dental Exam Tutoring
        system_instruction = (
            "You are an expert clinical medical companion and tutor specifically assisting dental students preparing for medical/dental exams.\n"
            "Guidelines:\n"
            "1. Primary Textbook Grounding: If the provided book excerpts contain relevant information (e.g., causes of acute hepatitis, diagnostic tables), "
            "synthesize a clear answer grounded in the text and cite the specific page numbers [Page X].\n"
            "2. Exam Preparation Fallback: If the provided excerpts do not contain the details or only mention the term in passing "
            "(e.g., topics like clinical features and complications of tetanus, which are not covered in detail in this specific textbook), "
            "clearly state that the topic is not covered in detail in the current textbook ('Essentials of Medicine for Dental Students'), "
            "and then provide a comprehensive, high-yield, structured clinical answer tailored for dental students "
            "(highlighting oral/dental implications such as trismus/lockjaw, facial muscle spasms, and post-trauma prophylaxis).\n"
            "3. Formatting: Well-structured, concise, and suitable for voice narration."
        )

        prompt = f"""Here are the retrieved book excerpts:

---
{formatted_context}
---

Question: {question}

Provide a structured, clear answer citing page numbers where applicable:"""

        # Step 4: Call Gemini 2.5 Flash
        response = self.client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config={"system_instruction": system_instruction}
        )

        return {
            "answer": response.text.strip(),
            "sources": sources
        }

    def stream_answer_question(self, question: str, top_k: int = 4):
        """
        Streams answer tokens in real time:
        1. Yields sources immediately after vector search (~400ms).
        2. Streams Gemini 2.5 Flash tokens word-by-word as they generate (~15ms per token).
        3. Yields done event with complete answer.
        """
        # Step 1: Semantic Retrieval
        retrieved_chunks = self.vector_store.query_similar(question, top_k=top_k)

        if not retrieved_chunks:
            yield {"type": "sources", "sources": []}
            not_found_msg = "I couldn't find any relevant sections in the book for your question."
            yield {"type": "token", "token": not_found_msg}
            yield {"type": "done", "full_answer": not_found_msg}
            return

        # Step 2: Assemble Context with Citations
        context_blocks = []
        sources = []
        for c in retrieved_chunks:
            meta = c["metadata"]
            source_citation = f"[{meta['source']}, Page {meta['page']}]"
            context_blocks.append(f"{source_citation}:\n\"{c['text']}\"")
            sources.append({
                "source": meta["source"],
                "page": meta["page"],
                "similarity": round(c["similarity_score"], 2),
                "excerpt": c["text"]
            })

        # Yield sources right away so the client can display them instantly!
        yield {"type": "sources", "sources": sources}

        formatted_context = "\n\n".join(context_blocks)

        # Step 3: Prompt Engineering
        system_instruction = (
            "You are an expert clinical medical companion and tutor specifically assisting dental students preparing for medical/dental exams.\n"
            "Guidelines:\n"
            "1. Primary Textbook Grounding: If the provided book excerpts contain relevant information (e.g., causes of acute hepatitis, diagnostic tables), "
            "synthesize a clear answer grounded in the text and cite the specific page numbers [Page X].\n"
            "2. Exam Preparation Fallback: If the provided excerpts do not contain the details or only mention the term in passing "
            "(e.g., topics like clinical features and complications of tetanus, which are not covered in detail in this specific textbook), "
            "clearly state that the topic is not covered in detail in the current textbook ('Essentials of Medicine for Dental Students'), "
            "and then provide a comprehensive, high-yield, structured clinical answer tailored for dental students "
            "(highlighting oral/dental implications such as trismus/lockjaw, facial muscle spasms, and post-trauma prophylaxis).\n"
            "3. Formatting: Well-structured, concise, and suitable for voice narration."
        )

        prompt = f"""Here are the retrieved book excerpts:

---
{formatted_context}
---

Question: {question}

Provide a structured, clear answer citing page numbers where applicable:"""

        # Step 4: Real-time token streaming from Gemini 2.5 Flash
        response_stream = self.client.models.generate_content_stream(
            model="gemini-2.5-flash",
            contents=prompt,
            config={"system_instruction": system_instruction}
        )

        full_text = []
        for chunk in response_stream:
            if chunk.text:
                full_text.append(chunk.text)
                yield {"type": "token", "token": chunk.text}

        yield {
            "type": "done",
            "full_answer": "".join(full_text).strip()
        }


if __name__ == "__main__":
    rag = BookRAG()
    
    question = "What science was Hari Seldon known for, and what did it do?"
    print(f"❓ Question: {question}")
    
    result = rag.answer_question(question)
    print(f"\n💡 Answer:\n{result['answer']}")
    print("\n📚 Sources Consulted:")
    for s in result["sources"]:
        print(f" - {s['source']} (Page {s['page']}, Score: {s['similarity']})")
