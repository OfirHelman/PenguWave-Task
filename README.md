# PenguWave: Security Operations Portal

A security operations portal for monitoring security events across your infrastructure.

This is a **frontend-only** starter app with mock data and an API contract. It's the starting point for the bootcamp task.

> **Your task is in [`ASSIGNMENT.md`](./ASSIGNMENT.md).** Read it first.

## Getting started

```bash
npm install
npm run dev
```

The frontend runs at http://localhost:5173. You'll see a login modal, an events table, and a users management page. The app works standalone with mock data, so explore it before you start building.

## Backend

The Python backend lives in [`backend/`](./backend) (FastAPI + SQLite). It runs on http://localhost:3001 to match the Base URL in [`docs/api_contract.md`](./docs/api_contract.md).

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python seed.py        # create the SQLite DB and load events + demo users
python main.py        # starts the API on http://localhost:3001
```

`python main.py` defaults to port 3001 — no need to pass it manually. Override with `PORT=<port> python main.py` if necessary. Health check: http://localhost:3001/api/health, interactive docs at http://localhost:3001/docs.

## What's included

- React + Vite + TypeScript frontend (3 pages)
- Realistic mock security events (`data/mock_events.json`)
- API endpoint contract (`docs/api_contract.md`)
- No backend (building one is Track A)
