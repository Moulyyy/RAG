import os
from typing import List, Dict, Any
from pypdf import PdfReader


def load_pdf(file_path: str) -> List[Dict[str, Any]]:
    """
    Extracts text page-by-page from a PDF file.
    Returns a list of dicts: [{'text': '...', 'page': 1, 'source': 'book.pdf'}]
    """
    reader = PdfReader(file_path)
    pages_data = []
    file_name = os.path.basename(file_path)

    for page_idx, page in enumerate(reader.pages):
        text = page.extract_text()
        if text and text.strip():
            pages_data.append({
                "text": text.strip(),
                "page": page_idx + 1,  # 1-indexed for humans
                "source": file_name
            })
    return pages_data


def load_txt(file_path: str) -> List[Dict[str, Any]]:
    """
    Reads plain text files (.txt or .md).
    """
    file_name = os.path.basename(file_path)
    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
        content = f.read()

    return [{
        "text": content.strip(),
        "page": 1,
        "source": file_name
    }]


def chunk_text(
    pages_data: List[Dict[str, Any]], 
    chunk_size: int = 1000, 
    chunk_overlap: int = 200
) -> List[Dict[str, Any]]:
    """
    Splits page text into overlapping chunks while preserving page numbers and source metadata.
    """
    chunks = []
    chunk_counter = 0

    for item in pages_data:
        text = item["text"]
        page = item["page"]
        source = item["source"]

        start = 0
        text_len = len(text)

        while start < text_len:
            end = start + chunk_size
            chunk_content = text[start:end]

            # Try to snap to the end of a sentence or word if possible
            if end < text_len:
                last_space = chunk_content.rfind(" ")
                if last_space > chunk_size * 0.7:  # Only snap if reasonable
                    end = start + last_space
                    chunk_content = text[start:end]

            chunk_id = f"{source}_p{page}_c{chunk_counter}"
            chunks.append({
                "chunk_id": chunk_id,
                "text": chunk_content.strip(),
                "metadata": {
                    "source": source,
                    "page": page,
                    "chunk_id": chunk_id
                }
            })

            chunk_counter += 1

            # Once the end of the text is reached, terminate this page
            if end >= text_len:
                break

            # Step forward by chunk_size - chunk_overlap
            step = max(1, len(chunk_content) - chunk_overlap)
            start += step

    return chunks


if __name__ == "__main__":
    # Test with dummy book pages
    sample_pages = [
        {
            "text": "Chapter 1: The Beginning. In an ancient library hidden deep within the mountains, scholars studied forgotten languages and mysterious stars. Every book contained a piece of a forgotten puzzle.",
            "page": 1,
            "source": "the_ancient_library.txt"
        },
        {
            "text": "Chapter 2: The Discovery. On a cold autumn morning, a strange glowing tome was uncovered beneath the floorboards. It spoke of artificial minds that could understand all human speech.",
            "page": 2,
            "source": "the_ancient_library.txt"
        }
    ]
    
    test_chunks = chunk_text(sample_pages, chunk_size=120, chunk_overlap=30)
    print(f"Total chunks created: {len(test_chunks)}")
    for i, c in enumerate(test_chunks):
        print(f"\n--- Chunk {i+1} [Page {c['metadata']['page']}] ---")
        print(f"ID: {c['chunk_id']}")
        print(f"Text: \"{c['text']}\"")
