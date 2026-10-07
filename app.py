import os
import sys
import base64
import shutil
import json
from typing import Optional
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Response
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from pydantic import BaseModel

from document_loader import load_pdf, load_txt, chunk_text
from vector_store import BookVectorStore
from rag_engine import BookRAG
from voice_service import VoiceService

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')

app = FastAPI(title="Voice Book RAG")

# Global instances
store = BookVectorStore()
rag = BookRAG(vector_store=store)
tts = VoiceService()

current_document_name = "Essentials of Medicine for Dental Students"


class QueryRequest(BaseModel):
    question: str
    voice: Optional[str] = "en-US-ChristopherNeural"


class TTSRequest(BaseModel):
    text: str
    voice: Optional[str] = "en-US-ChristopherNeural"


@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    """Serves an inline SVG favicon to prevent 404 errors in browser logs."""
    svg_icon = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><text y=".9em" font-size="90">🩺</text></svg>'
    return Response(content=svg_icon, media_type="image/svg+xml")


@app.get("/", response_class=HTMLResponse)
async def serve_ui():
    """Serves the interactive web interface."""
    with open("index.html", "r", encoding="utf-8") as f:
        return f.read()


@app.get("/api/status")
async def get_status():
    """Returns current active document stats."""
    return {
        "current_document": current_document_name,
        "total_chunks": store.count()
    }


@app.post("/api/upload")
async def upload_document(
    file: UploadFile = File(...),
    max_pages: Optional[int] = Form(None)
):
    """
    Uploads and indexes a new document, replacing the current knowledge base.
    """
    global current_document_name

    upload_dir = "./uploads"
    os.makedirs(upload_dir, exist_ok=True)
    file_path = os.path.join(upload_dir, file.filename)

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    ext = os.path.splitext(file.filename)[1].lower()
    if ext == ".pdf":
        pages = load_pdf(file_path)
    elif ext in [".txt", ".md"]:
        pages = load_txt(file_path)
    else:
        raise HTTPException(status_code=400, detail="Only PDF, TXT, or MD files are supported.")

    if not pages:
        raise HTTPException(status_code=400, detail="Could not extract text from the file.")

    if max_pages and max_pages < len(pages):
        pages = pages[:max_pages]

    chunks = chunk_text(pages, chunk_size=1000, chunk_overlap=200)

    # Wipe previous book and index the new one
    store.reset_collection()
    store.add_chunks_batched(chunks, batch_size=50)

    current_document_name = file.filename
    return {
        "message": f"Successfully loaded '{file.filename}'",
        "chunks_indexed": len(chunks),
        "total_pages": len(pages)
    }


@app.post("/api/query")
async def process_query(req: QueryRequest):
    """
    Runs RAG query, synthesizes answer, and generates voice narration.
    """
    if not req.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty.")

    # 1. RAG Answer
    rag_result = rag.answer_question(req.question, top_k=4)

    # 2. Generate Voice Audio via Edge-TTS
    tts.voice = req.voice or "en-US-ChristopherNeural"
    audio_bytes = await tts.text_to_speech_bytes(rag_result["answer"])
    audio_base64 = base64.b64encode(audio_bytes).decode("utf-8")

    return {
        "question": req.question,
        "answer": rag_result["answer"],
        "sources": rag_result["sources"],
        "audio_base64": f"data:audio/mp3;base64,{audio_base64}"
    }


@app.post("/api/query/stream")
async def process_query_stream(req: QueryRequest):
    """
    Real-time Server-Sent Events (SSE) streaming endpoint:
    - Yields retrieved sources immediately (~350ms)
    - Streams tokens word-by-word with ultra-low latency (~15ms per token)
    - Signals completion with a final done event
    """
    if not req.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty.")

    async def event_generator():
        for event in rag.stream_answer_question(req.question, top_k=4):
            yield f"data: {json.dumps(event)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@app.post("/api/tts")
async def process_tts(req: TTSRequest):
    """
    On-demand Edge-TTS voice generation.
    Allows UI to play audio without blocking the real-time token stream!
    """
    if not req.text.strip():
        raise HTTPException(status_code=400, detail="Text cannot be empty.")

    tts.voice = req.voice or "en-US-ChristopherNeural"
    audio_bytes = await tts.text_to_speech_bytes(req.text)
    audio_base64 = base64.b64encode(audio_bytes).decode("utf-8")
    return {"audio_base64": f"data:audio/mp3;base64,{audio_base64}"}


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    print(f"\n🚀 Starting Voice RAG Server on http://0.0.0.0:{port}")
    uvicorn.run("app:app", host="0.0.0.0", port=port, reload=True)
