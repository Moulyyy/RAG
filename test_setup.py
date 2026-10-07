import os
import sys
from dotenv import load_dotenv
from google import genai
import chromadb

# Ensure Windows terminal prints UTF-8 symbols without crashing
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')

# 1. Load environment variables from .env
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    print("[ERROR] GEMINI_API_KEY is not set in .env")
    exit(1)

print("[SUCCESS] Found API Key!")

# 2. Test Gemini API client
print("Contacting Gemini API (gemini-2.5-flash)...")
client = genai.Client(api_key=api_key)
response = client.models.generate_content(
    model="gemini-2.5-flash",
    contents="Hello! Tell me in one short sentence why books are awesome.",
)
print(f"Gemini response: {response.text.strip()}")

# 3. Test ChromaDB vector store
print("\nTesting ChromaDB vector storage & similarity query...")
chroma_client = chromadb.Client()
collection = chroma_client.get_or_create_collection(name="test_collection")

# Add a sample document
collection.add(
    documents=["Books allow you to travel through time and minds."],
    ids=["id1"]
)

# Query using semantic similarity
results = collection.query(query_texts=["time travel"], n_results=1)
print(f"ChromaDB test retrieved: {results['documents'][0][0]}")

print("\nEverything is working properly!")
