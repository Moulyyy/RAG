import os
import sys
import argparse
from document_loader import load_pdf, load_txt, chunk_text
from vector_store import BookVectorStore

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')


def ingest_document(
    file_path: str,
    wipe: bool = False,
    max_pages: int = None,
    chunk_size: int = 1000,
    chunk_overlap: int = 200
):
    if not os.path.exists(file_path):
        print(f"Error: File not found at '{file_path}'")
        return

    print(f"\n📂 Loading document: {file_path}")
    ext = os.path.splitext(file_path)[1].lower()

    if ext == ".pdf":
        pages = load_pdf(file_path)
    elif ext in [".txt", ".md"]:
        pages = load_txt(file_path)
    else:
        print(f"Unsupported format '{ext}'. Please provide a PDF, TXT, or MD file.")
        return

    if not pages:
        print("No text could be extracted from the document.")
        return

    total_pages = len(pages)
    print(f"Extracted text from {total_pages} pages.")

    if max_pages and max_pages < total_pages:
        print(f"Limiting to first {max_pages} pages.")
        pages = pages[:max_pages]

    print(f"Chunking with size={chunk_size}, overlap={chunk_overlap}...")
    chunks = chunk_text(pages, chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    print(f"Total chunks in document: {len(chunks)}.")

    store = BookVectorStore()
    if wipe:
        print("Wiping previous knowledge base (--wipe requested)...")
        store.reset_collection()

    # Index chunks with automatic resume checkpointing & rate-limit handling
    store.add_chunks_batched(chunks, batch_size=40)
    print(f"\n🎉 Done! ChromaDB now contains {store.count()} indexed chunks from '{os.path.basename(file_path)}'.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Ingest any book or document into RAG")
    parser.add_argument(
        "--file",
        type=str,
        default="toaz.info-ak-tripathi-essentials-of-medicine-for-dental-students-2nd-edition-pr_6e957ec72d238229092d932861535511.pdf",
        help="Path to the document (PDF or TXT)"
    )
    parser.add_argument(
        "--pages",
        type=int,
        default=None,
        help="Optional: number of pages to index (e.g. --pages 50)"
    )
    parser.add_argument(
        "--wipe",
        action="store_true",
        help="Wipe previous collection to start completely fresh"
    )

    args = parser.parse_args()
    ingest_document(
        file_path=args.file,
        wipe=args.wipe,
        max_pages=args.pages
    )
