# Northwind Agent - Architecture & Technology Stack

## Project Overview
An AI-powered chatbot that answers natural language questions about the Northwind database. Users ask questions in plain English, and the agent uses tool-calling to execute SQL queries and return structured results with streaming responses.

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    Client (Browser/API)                     │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│              FastAPI Web Server (Uvicorn)                   │
│  - REST API with streaming responses                        │
│  - Request/Response handling                                │
└────────┬────────────────────────────────────────────┬───────┘
         │                                            │
         ▼                                            ▼
┌─────────────────────────┐         ┌──────────────────────────┐
│   Chat Route Handler    │         │  Config & Settings       │
│  - POST /chat/          │         │  - Database credentials  │
│  - Streaming response   │         │  - LLM model selection   │
└────────┬────────────────┘         └──────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────┐
│                  Agent Service                              │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ Strands Agent Framework                             │   │
│  │  - System prompt configuration                      │   │
│  │  - Tool management                                  │   │
│  │  - LLM routing & decision making                    │   │
│  └──────────────────┬──────────────────────────────────┘   │
│                     │                                       │
│  ┌──────────────────┴──────────────────┐                   │
│  │ Available Tools                     │                   │
│  │  - supplier_info(product_name)      │                   │
│  │    └─> Queries Products + Suppliers│                   │
│  └─────────────────────────────────────┘                   │
└─────────────┬──────────────────────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────────────────────────┐
│            Ollama LLM (Local Language Model)                │
│  - Runs on localhost:11434                                  │
│  - Tool-calling capable model                               │
│  - No API keys required (local inference)                   │
└─────────────────────────────────────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────────────────────────┐
│          Database Layer (SQLAlchemy/SQLModel)               │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ Query Execution                                     │   │
│  │  - Dynamic SQL generation                          │   │
│  │  - Result fetching & serialization                 │   │
│  └──────────────────┬──────────────────────────────────┘   │
└─────────────────────┼──────────────────────────────────────┘
                      │
                      ▼
          ┌───────────────────────────────┐
          │   Northwind Database          │
          │   (MySQL/PostgreSQL/etc)      │
          │                               │
          │   Tables:                     │
          │   - Products                  │
          │   - Suppliers                 │
          │   - Orders                    │
          │   - Customers                 │
          │   - Employees                 │
          │   - (+ more)                  │
          └───────────────────────────────┘
```

---

## Technology Stack

### Backend Framework
- **FastAPI** (v0.135.1) - Modern async web framework
  - Auto-generated API documentation (Swagger/OpenAPI)
  - Dependency injection system
  - Built-in data validation with Pydantic

- **Uvicorn** (v0.41.0) - ASGI server
  - Async request handling
  - Hot-reload in development

### AI & LLM
- **Strands Agent Framework** (v1.28.0)
  - Multi-turn agent conversations
  - Tool/function calling support
  - System prompt management

- **Ollama** (external, localhost:11434)
  - Local LLM inference
  - No cloud dependencies
  - Privacy-first approach

### Database
- **SQLAlchemy** (v2.0.47) - ORM/SQL toolkit
- **SQLModel** (v0.0.37) - Pydantic + SQLAlchemy hybrid
- **Python Database Drivers:**
  - `PyMySQL` - MySQL support
  - `asyncpg` - PostgreSQL async support
  - `aiosqlite` - SQLite async support

### Configuration & Environment
- **Pydantic Settings** (v2.13.1) - Configuration management
- **python-dotenv** (v1.2.2) - Environment variable loading

### Streaming & Async
- **Starlette** (v0.52.1) - ASGI toolkit (used by FastAPI)
- **httpx** (v0.28.1) - Async HTTP client
- **anyio** (v4.12.1) - Async abstraction layer

### Additional Libraries
- **Pydantic** (v2.12.5) - Data validation
- **python-multipart** - Form data handling
- **PyJWT** - JWT token handling (auth support)
- **google-auth** - Google authentication support

---

## Project Structure

```
northwind_agent/
├── main.py                 # FastAPI app entry point
├── config.py              # Settings & environment config
├── dep.py                 # Database session dependency
├── requirements.txt       # Python dependencies
├── .env                   # Environment variables
│
├── api/
│   ├── main.py           # Router aggregation
│   ├── routes/
│   │   └── chat.py       # Chat endpoint with streaming
│   └── models/
│       └── ChatModel.py   # Pydantic request/response models
│
├── services/
│   └── AgentService.py   # Strands Agent setup & configuration
│       ├── make_supplier_tool()    # Tool factory for DB queries
│       ├── _system_prompt()        # Agent behavior definition
│       ├── _ask_agent()            # Agent initialization
│       └── chat()                  # Main chat entry point
│
└── queries/              # (SQL queries directory - optional)
```

---

## Core Components

### 1. **Configuration (config.py)**
- Loads database credentials from `.env`
- Constructs database URL from components
- Stores agent model name

### 2. **Database Session (dep.py)**
- Creates database engine with SQLAlchemy
- Provides session dependency injection
- Supports multiple database drivers (MySQL, PostgreSQL, SQLite)

### 3. **Agent Service (services/AgentService.py)**
- **`supplier_info(product_name)` Tool:**
  - Queries Products + Suppliers tables
  - Case-insensitive search
  - Returns list of JSON objects
  
- **System Prompt:**
  - Instructs agent to use tools
  - Emphasizes always calling the supplier_info tool
  - Provides examples to guide behavior
  
- **Chat Flow:**
  1. Receives user message
  2. Creates Strands Agent with Ollama model
  3. Attaches supplier_info tool
  4. Agent calls LLM with system prompt
  5. LLM decides to call supplier_info tool (or respond directly)
  6. Tool executes SQL query, returns results
  7. Agent processes tool output
  8. Returns structured AgentResult

### 4. **Chat Endpoint (api/routes/chat.py)**
- **Endpoint:** `POST /chat/`
- **Request:** `{"message": "Who supplies Chai?"}`
- **Response:** Streaming NDJSON
  ```
  {"chunk": "The"}
  {"chunk": "supplier"}
  ...
  ```
- **Streaming Strategy:**
  - Calls agent.chat() (gets full response)
  - Converts AgentResult to string
  - Yields response line-by-line for streaming effect
  - Media type: `application/x-ndjson`

---

## Data Flow

### Request to Response Cycle

```
1. Client sends HTTP POST request
   POST /chat/ {"message": "Who supplies Chai?"}
   
2. FastAPI validates request (ChatRequest model)

3. Chat endpoint extracts message

4. Agent Service creates Strands Agent:
   - Initializes Ollama model connection
   - Attaches supplier_info tool
   - Sets system prompt
   
5. Agent processes query:
   agent(message) → AgentResult
   
6. Ollama LLM analyzes request:
   - Recognizes need for supplier_info tool
   - Extracts product name: "Chai"
   
7. LLM calls supplier_info("Chai")

8. Tool executes SQL:
   SELECT * FROM products p
   LEFT JOIN suppliers s ON s.supplier_id = p.supplier_id
   WHERE p.product_name ILIKE '%chai%'
   
9. Query returns product & supplier rows

10. Tool serializes results → list of dicts

11. Strands Agent processes tool output:
    - Formats response in natural language
    - Returns AgentResult with message
    
12. Chat endpoint streams response:
    - Converts AgentResult to string
    - Splits by newlines
    - Yields each chunk as NDJSON
    
13. Client receives streaming response
    and displays results progressively
```

---

## Key Features

| Feature | Implementation |
|---------|----------------|
| **Natural Language Q&A** | Ollama LLM + Strands Agent Framework |
| **Database Queries** | SQLAlchemy + SQLModel ORM |
| **Tool Calling** | Strands `@tool` decorator on functions |
| **Streaming Responses** | FastAPI StreamingResponse + NDJSON |
| **Async Support** | Uvicorn ASGI server + asyncio |
| **Configuration** | Pydantic Settings + .env files |
| **Multiple DB Support** | SQLAlchemy drivers (MySQL, PostgreSQL, SQLite) |
| **Extensibility** | Easy to add more tools via `@tool` decorator |

---

## Configuration Flow

```
.env file
    ↓
pydantic_settings.BaseSettings
    ↓
Settings class (config.py)
    ↓
settings object
    ↓
Used by:
├── dep.py (DATABASE_URL)
└── services/AgentService.py (AGENT_NAME)
```

---

## Example Query Walkthrough

**User asks:** "Who supplies Chai?"

1. **Request arrives:** `POST /chat/ {"message": "Who supplies Chai?"}`

2. **Agent processes:**
   - System prompt: "Use supplier_info tool to answer"
   - LLM recognizes entity: product "Chai"
   - Decides to call: `supplier_info("Chai")`

3. **Tool executes:**
   ```python
   supplier_info("Chai")
   # ↓ SQL ↓
   SELECT * FROM products p
   LEFT JOIN suppliers s ON s.supplier_id = p.supplier_id
   WHERE p.product_name ILIKE '%chai%'
   # ↓ Returns ↓
   [
     {
       "product_id": 1,
       "product_name": "Chai",
       "supplier_id": 1,
       "company_name": "Specialty Biscuits, Ltd.",
       "contact_name": "Peter Wilson",
       ...
     }
   ]
   ```

4. **Agent formats response:**
   ```
   "The supplier of Chai is Specialty Biscuits, Ltd.
    Their contact information includes:
    * Contact Name: Peter Wilson
    * Contact Title: Sales Representative
    * Address: 29 King's Way
    * City: Manchester
    ..."
   ```

5. **Response streams to client:**
   ```
   {"chunk": "The supplier of Chai is Specialty Biscuits, Ltd.\n"}
   {"chunk": "Their contact information includes:\n"}
   {"chunk": "* Contact Name: Peter Wilson\n"}
   ...
   ```

---

## Extensibility

### Adding New Tools

```python
def _ask_agent(self) -> Agent:
    supplier_tool = make_supplier_tool(self.db)
    
    # Add a new tool:
    @tool
    def get_orders(customer_name: str):
        """Get orders for a customer"""
        result = self.db.execute(...)
        return [row._asdict() for row in result]
    
    agent = Agent(
        model=self.model,
        tools=[supplier_tool, get_orders],  # ← Add here
        system_prompt=self._system_prompt()
    )
    return agent
```

### Extending Streaming

Currently streams by newlines. To stream character-by-character with delay:

```python
async def generate():
    response = agent_service.chat(body.message)
    message = str(response)
    for char in message:
        yield json.dumps({"chunk": char}) + "\n"
        await asyncio.sleep(0.01)
```

---

## Dependencies Summary

| Category | Key Libraries |
|----------|---------------|
| **Web Framework** | FastAPI, Uvicorn, Starlette |
| **AI/LLM** | Strands Agent, Ollama (external) |
| **Database** | SQLAlchemy, SQLModel, PyMySQL, asyncpg |
| **Config** | Pydantic, pydantic-settings, python-dotenv |
| **Streaming** | httpx, anyio |
| **Auth (optional)** | PyJWT, google-auth |

---

## Security Considerations

1. **Environment Variables:** Database credentials stored in `.env` (never in code)
2. **Local LLM:** Ollama runs locally, no data sent to external APIs
3. **SQL Injection:** Uses parameterized queries with `:param` syntax
4. **Input Validation:** Pydantic validates all API inputs

---

## Future Enhancements

- [ ] True streaming from LLM (token-by-token as model generates)
- [ ] Chat memory/conversation history
- [ ] Additional tools (orders, customers, employees)
- [ ] Response caching for common queries
- [ ] Rate limiting & authentication
- [ ] Structured output support (JSON schema)
- [ ] Multi-turn context awareness
- [ ] Query optimization suggestions
