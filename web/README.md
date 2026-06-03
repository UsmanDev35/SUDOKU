# Sudoku Solver Evaluator - Web UI

A web-based interface for the Sudoku Solver Evaluator project, featuring a FastAPI backend and React frontend.

## Architecture

```
web/
├── backend/         FastAPI server (Python)
│   ├── app.py       Single-file API server
│   └── requirements.txt
├── frontend/        React + Vite app
│   ├── src/
│   │   ├── components/   Reusable UI components
│   │   └── pages/        Page components (Home, Solve, Race, Stats)
│   ├── package.json
│   └── vite.config.js
└── README.md
```

## Getting Started

### Prerequisites

- Python 3.10+ with the sudoku_solver_evaluator package available
- Node.js 18+

### Backend Setup

```bash
cd web/backend

# Create a virtual environment (optional, or use the project's existing .venv)
pip install -r requirements.txt

# Run the server
python app.py
# or
uvicorn app:app --reload --port 8000
```

The API will be available at `http://localhost:8000`.

### Frontend Setup

```bash
cd web/frontend

# Install dependencies
npm install

# Start the dev server
npm run dev
```

The frontend will be available at `http://localhost:3000`.

The Vite dev server proxies `/api` requests to the backend at `http://localhost:8000`, so both servers need to be running simultaneously.

## API Endpoints

| Method | Endpoint        | Description                          |
|--------|-----------------|--------------------------------------|
| POST   | `/api/generate` | Generate a puzzle at a difficulty    |
| POST   | `/api/solve`    | Solve a puzzle with one or all solvers |
| POST   | `/api/race`     | Run an adversarial race              |
| GET    | `/api/stats`    | Get aggregate performance statistics |

### POST /api/generate

```json
{ "difficulty": "easy" | "medium" | "hard" | "expert" }
```

### POST /api/solve

```json
{
  "puzzle": [[0,0,3,...], ...],
  "solver": "backtracking" | "informed" | "local_search" | "forward_checking" | "all"
}
```

### POST /api/race

```json
{
  "puzzle": [[0,0,3,...], ...],
  "solver_a": "backtracking",
  "solver_b": "informed"
}
```

## Features

- **Generate & Solve** - Generate puzzles at 4 difficulty levels, solve with any of 4 algorithms or compare all at once
- **Adversarial Race** - Pit two solvers against each other head-to-head
- **Statistics** - View aggregate performance data with bar charts
- **Dark/Light Mode** - Toggle between dark and light themes
- **Responsive Design** - Works on desktop and mobile

## Tech Stack

- **Backend**: FastAPI, Pydantic, Uvicorn
- **Frontend**: React 18, Vite, Tailwind CSS (via CDN), React Router
- **Styling**: Tailwind CSS utility classes with dark mode support
