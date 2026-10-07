# 🎙️ Voice RAG — Real-Time Low-Latency Book AI Companion

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115%2B-009688.svg)](https://fastapi.tiangolo.com)
[![Gemini](https://img.shields.io/badge/Gemini-2.5%20Flash-orange.svg)](https://ai.google.dev)
[![ChromaDB](https://img.shields.io/badge/Vector%20Store-ChromaDB-red.svg)](https://www.trychroma.com)
[![TTS](https://img.shields.io/badge/Voice-Edge--TTS-brightgreen.svg)](https://github.com/rany2/edge-tts)

A conversational, voice-enabled Retrieval-Augmented Generation (RAG) assistant optimized for **ultra-low latency and real-time streaming responses**. Ask questions by speaking into your microphone or typing, and receive answers grounded in your textbooks, complete with precise page citations and audio narration.

---

## ⚡ Real-Time & Low-Latency Optimizations

This application has been tailored for interactive real-time performance:

1. **Server-Sent Events (SSE) Token Streaming (`/api/query/stream`)**:
   Instead of waiting several seconds for the entire LLM response and TTS audio, tokens are streamed via SSE word-by-word with ~15ms token intervals and sub-500ms time-to-first-token.
2. **Instant Source-First Yielding**:
   Retrieved textbook excerpts and citations are delivered to the frontend immediately after semantic vector search (~300ms), giving the user feedback and sources while the answer generates.
3. **In-Memory Embedding Caching**:
   Vector embeddings for queries are cached in memory. Repeated or similar student queries bypass remote embedding calls, reducing retrieval latency to near-zero.
4. **Non-Blocking Asynchronous Voice Generation**:
   Audio narration is synthesized asynchronously via Edge-TTS and streamed as base64 without blocking the instant visual text stream. Users can also select *Text-Only Mode* for maximum speed.
5. **Interactive Controls & Cancellation**:
   Full support for stopping generation or speech mid-sentence using the `Stop` button or pressing `Esc`.

---

## 🛠️ Architecture & Tech Stack

```text
  [ User Microphone / Text Input ]
                  │
                  ▼
         [ FastAPI Server ]
         ┌────────┴────────┐
         ▼                 ▼
  [ ChromaDB ]     [ Embedding Cache ]
  Vector Search    gemini-embedding-001
         │
         ▼
  [ Gemini 2.5 Flash ] ──(SSE Stream)──▶ [ Instant Text Display ]
         │
         ▼ (Async)
   [ Edge-TTS ] ─────────(Base64)──────▶ [ Neural Audio Playback ]
```

- **LLM**: Google Gemini 2.5 Flash (via `google-genai` SDK)
- **Vector Database**: ChromaDB (Cosine similarity index)
- **Embeddings**: `gemini-embedding-001`
- **Voice Synthesis**: Microsoft Edge Neural TTS (`edge-tts`)
- **Backend**: FastAPI with async StreamingResponse & Uvicorn
- **Frontend**: Single-page modern glassmorphic interface with speech recognition, audio visualizer wave, and dynamic document upload.

---

## 🚀 Quick Start Guide

### 1. Clone Repository
```bash
git clone https://github.com/Moulyyy/RAG.git
cd RAG
```

### 2. Set Up Virtual Environment
```bash
# Windows
python -m venv venv
.\venv\Scripts\activate

# Linux / macOS
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```
Open `.env` and add your Gemini API key:
```env
GEMINI_API_KEY=your_gemini_api_key_here
```
*(Get a free key from [Google AI Studio](https://aistudio.google.com/app/apikey))*

### 5. Launch the Web Application
```bash
python app.py
```
Open your browser and navigate to:
```
http://127.0.0.1:8000
```

---

## 📚 Ingesting Books & Custom Documents

### Option A: Via the Web UI
Click the **"Change Book"** button in the top navigation bar, drag and drop any PDF or TXT document, and click **"Upload & Index"**.

### Option B: Via Command Line CLI
```bash
# Ingest entire document
python ingest.py --file "path/to/your_book.pdf"

# Ingest with wipe and page limit
python ingest.py --file "path/to/your_book.pdf" --pages 60 --wipe
```

---

## 📡 API Endpoints

| Endpoint | Method | Description |
|---|---|---|
| `GET /` | `GET` | Serves the interactive Web UI |
| `POST /api/query/stream` | `POST` | Real-time SSE streaming answer + citations |
| `POST /api/query` | `POST` | Standard synchronous RAG query with audio |
| `POST /api/tts` | `POST` | On-demand Edge-TTS voice generation |
| `POST /api/upload` | `POST` | Upload and index new PDF/TXT documents |
| `GET /api/status` | `GET` | Current active book title and chunk count |

---

## 🌐 Cloud Deployment & Hosting

### Note on GitHub Pages:
GitHub Pages only hosts static files (HTML, CSS, client-side JS) and **cannot run Python backends, FastAPI, ChromaDB, or Edge-TTS**. To run the live interactive app in the cloud, choose one of the free/low-cost platforms below:

### Option 1: Hugging Face Spaces (Recommended Free Option)
1. Create a new Space on [Hugging Face](https://huggingface.co/spaces) and select **Docker** as the SDK.
2. Push this repository to your Space repository.
3. In Space Settings, add the secret `GEMINI_API_KEY`.
4. Your application is live with persistent URL!

### Option 2: Render.com
1. Create a new **Web Service** on [Render](https://render.com).
2. Connect your GitHub repository `https://github.com/Moulyyy/RAG.git`.
3. Choose **Docker** environment or Python environment (`uvicorn app:app --host 0.0.0.0 --port $PORT`).
4. Add environment variable `GEMINI_API_KEY`.

### Option 3: Docker Local / VPS
```bash
docker build -t voice-rag .
docker run -p 8000:8000 -e GEMINI_API_KEY="your_api_key" voice-rag
```

---

## 📄 License
MIT License. Built for education and real-time medical & dental student exam preparation.
