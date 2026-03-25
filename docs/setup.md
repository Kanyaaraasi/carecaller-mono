# Setup

## Prerequisites

- Node.js 20+
- Python 3.13+
- [uv](https://docs.astral.sh/uv/) (Python package manager)

## UI (carecaller-ui)

```bash
cd carecaller-ui
npm install
npm run dev
```

Runs on `http://localhost:5173` by default.

### Environment Variables

Create `carecaller-ui/.env.local`:

```
VITE_API_BASE_URL=http://localhost:8000
```

### Other Commands

| Command | Description |
|---|---|
| `npm run build` | Production build to `dist/` |
| `npm run preview` | Preview production build |
| `npm run typecheck` | TypeScript type checking |
| `npm run lint` | ESLint |
| `npm run format` | Prettier format |

## API (carecaller-api)

```bash
cd carecaller-api
uv sync
uv run uvicorn main:app --reload
```

Runs on `http://localhost:8000` by default.

## Ticket Classifier (carecaller-ticket)

```bash
cd carecaller-ticket
uv sync
uv run python main.py
```

## Running Everything Together

Open two terminals:

```bash
# Terminal 1 — API
cd carecaller-api && uv run uvicorn main:app --reload

# Terminal 2 — UI
cd carecaller-ui && npm run dev
```

The UI proxies API calls to `VITE_API_BASE_URL`. Make sure the API is running before starting a call.
