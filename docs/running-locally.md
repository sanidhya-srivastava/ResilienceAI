# Running ResilienceAI Locally

## Prerequisites

- **Python 3.11+** (tested on Python 3.13)
- **Node.js 20+** and **pnpm**
- **Docker Desktop** (only required for live container failure injection)
- **Ollama** with `qwen2.5:7b` (only required when `MOCK_MODE=false`)

## 1. Mock Mode Setup (Zero External Dependencies)

Mock mode simulates container crashes and LLM responses deterministically so you can run the entire dashboard and test suite locally in seconds.

### Backend

```powershell
python -m venv .venv
.\.venv\Scripts\pip.exe install -r backend/requirements.txt
copy backend\.env.example backend\.env
# Ensure MOCK_MODE=true in backend/.env
.\.venv\Scripts\python.exe -m uvicorn backend.api.main:app --reload --port 8000
```

Verify health: `http://localhost:8000/health`

### Frontend

```powershell
cd frontend
pnpm install
pnpm dev
```

Open `http://localhost:5173`.

## 2. Live Mode Setup (Ollama + Docker Compose)

1. Start **Docker Desktop**.
2. Pull the local LLM model:
   ```powershell
   ollama pull qwen2.5:7b
   ```
3. Copy `backend/.env.example` to `backend/.env` and set `MOCK_MODE=false`.
4. Start all containers:
   ```powershell
   docker compose up --build
   ```

## 3. Running Automated Tests

### Backend Tests

```powershell
.\.venv\Scripts\python.exe -m pytest backend/tests/ -v
```

### Frontend Tests & Typecheck

```powershell
cd frontend
pnpm test --run
pnpm run build
```
