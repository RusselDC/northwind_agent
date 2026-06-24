# northwind_agent

Northwind Agent is a FastAPI chatbot that answers natural language questions about a Northwind-style database.
It uses Ollama with tool-calling to generate SQL, execute read-only queries, and stream responses.

## Run

```bash
pip install -r requirements.txt
uvicorn northwind_agent.main:app --reload
```

## API

- `GET /health`
- `POST /chat` with `{ "question": "..." }`
- `POST /chat/stream` with `{ "question": "..." }`

Set optional environment variables:

- `OLLAMA_BASE_URL` (default `http://localhost:11434`)
- `OLLAMA_MODEL` (default `llama3.1`)
- `NORTHWIND_DB_PATH` (path for SQLite DB file)
