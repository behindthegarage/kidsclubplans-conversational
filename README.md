# KidsClubPlans Conversational Interface

A modern conversational AI interface for KidsClubPlans with RAG-based activity search, streaming responses, and an intuitive chat UI.

## Features

- **Streaming Chat**: Real-time AI responses using Server-Sent Events
- **RAG Integration**: Semantic search through Pinecone vector database
- **Activity Cards**: Interactive display of activity search results
- **Memory Management**: Conversation context across sessions
- **Voice Ready**: Whisper integration point for voice input
- **Modern Stack**: FastAPI + Next.js 14 + TypeScript + Tailwind + shadcn/ui

## Quick Start

### Prerequisites

- Docker and Docker Compose
- OpenAI API key
- Pinecone API key and index

### Environment Setup

1. Copy the environment template:
```bash
cp .env.example .env
```

2. Edit `.env` with your credentials:
```env
# OpenAI
OPENAI_API_KEY=sk-...

# Pinecone
PINECONE_API_KEY=pc-...
PINECONE_INDEX_NAME=kidsclubplans
PINECONE_DIMENSION=3072

# Database
DATABASE_PATH=/app/data/activities.db

# Backend
BACKEND_PORT=8000
CORS_ORIGINS=http://localhost:3000

# Frontend
NEXT_PUBLIC_API_URL=http://localhost:8000
```

### Run with Docker Compose

```bash
docker-compose up --build
```

This starts:
- Backend API at http://localhost:8000
- Frontend at http://localhost:3000

### Development (without Docker)

**Backend:**
```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

**Frontend:**
```bash
cd frontend
npm install
npm run dev
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/chat` | POST | Streaming chat endpoint (SSE) |
| `/health` | GET | Health check |
| `/activities/search` | POST | Search activities via RAG |
| `/activities/{id}` | GET | Get activity by ID |

## Project Structure

```
kidsclubplans-conversational/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py           # FastAPI app + SSE streaming
│   │   ├── chat.py           # Chat logic & OpenAI integration
│   │   ├── rag.py            # Pinecone RAG retrieval
│   │   ├── memory.py         # Conversation memory
│   │   └── tools.py          # Function calling tools
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── app/                  # Next.js App Router
│   ├── components/           # React components + shadcn/ui
│   ├── lib/                  # Utilities
│   └── package.json
├── data/                     # SQLite database mount point
├── docker-compose.yml
└── README.md
```

## Architecture

```
┌─────────────┐      HTTP/SSE       ┌──────────────┐
│  Next.js    │ ◄─────────────────► │   FastAPI    │
│  Frontend   │   Streaming Chat    │   Backend    │
└─────────────┘                     └──────┬───────┘
                                           │
                    ┌──────────────────────┼──────────────────────┐
                    │                      │                      │
                    ▼                      ▼                      ▼
              ┌─────────┐          ┌────────────┐          ┌──────────┐
              │OpenAI   │          │  Pinecone  │          │ SQLite   │
              │GPT-4o   │          │  Vector DB │          │activities│
              └─────────┘          └────────────┘          └──────────┘
```

## Customization

### Adding New Tools

Edit `backend/app/tools.py` to add new function calling capabilities:

```python
@tool
def my_custom_tool(param: str) -> dict:
    """Description for the AI"""
    return {"result": "data"}
```

### Styling

The frontend uses Tailwind CSS with shadcn/ui components. Customize in:
- `frontend/app/globals.css` - Global styles
- `frontend/tailwind.config.ts` - Theme configuration
- `frontend/components/ui/` - shadcn components

## License

MIT
