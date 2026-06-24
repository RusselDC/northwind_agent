import json
import os
import re
import sqlite3
from pathlib import Path
from typing import Any, AsyncGenerator

import httpx
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from starlette.responses import StreamingResponse


class ChatRequest(BaseModel):
    question: str = Field(min_length=1)


class NorthwindDatabase:
    _FORBIDDEN_SQL = re.compile(
        r"\b(insert|update|delete|drop|alter|create|replace|attach|detach|pragma|vacuum|reindex|truncate)\b",
        re.IGNORECASE,
    )

    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

    def initialize(self) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS Suppliers (
                    SupplierID INTEGER PRIMARY KEY,
                    CompanyName TEXT NOT NULL,
                    Country TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS Categories (
                    CategoryID INTEGER PRIMARY KEY,
                    CategoryName TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS Products (
                    ProductID INTEGER PRIMARY KEY,
                    ProductName TEXT NOT NULL,
                    SupplierID INTEGER,
                    CategoryID INTEGER,
                    UnitPrice REAL NOT NULL,
                    UnitsInStock INTEGER NOT NULL,
                    Discontinued INTEGER NOT NULL DEFAULT 0,
                    FOREIGN KEY(SupplierID) REFERENCES Suppliers(SupplierID),
                    FOREIGN KEY(CategoryID) REFERENCES Categories(CategoryID)
                );
                CREATE TABLE IF NOT EXISTS Customers (
                    CustomerID TEXT PRIMARY KEY,
                    CompanyName TEXT NOT NULL,
                    Country TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS Orders (
                    OrderID INTEGER PRIMARY KEY,
                    CustomerID TEXT NOT NULL,
                    OrderDate TEXT NOT NULL,
                    ShipCountry TEXT NOT NULL,
                    FOREIGN KEY(CustomerID) REFERENCES Customers(CustomerID)
                );
                CREATE TABLE IF NOT EXISTS OrderDetails (
                    OrderID INTEGER NOT NULL,
                    ProductID INTEGER NOT NULL,
                    UnitPrice REAL NOT NULL,
                    Quantity INTEGER NOT NULL,
                    Discount REAL NOT NULL DEFAULT 0,
                    PRIMARY KEY (OrderID, ProductID),
                    FOREIGN KEY(OrderID) REFERENCES Orders(OrderID),
                    FOREIGN KEY(ProductID) REFERENCES Products(ProductID)
                );
                """
            )

            existing = conn.execute("SELECT COUNT(*) FROM Products").fetchone()[0]
            if existing:
                return

            conn.executemany(
                "INSERT INTO Suppliers (SupplierID, CompanyName, Country) VALUES (?, ?, ?)",
                [
                    (1, "Exotic Liquids", "UK"),
                    (2, "New Orleans Cajun Delights", "USA"),
                ],
            )
            conn.executemany(
                "INSERT INTO Categories (CategoryID, CategoryName) VALUES (?, ?)",
                [(1, "Beverages"), (2, "Condiments")],
            )
            conn.executemany(
                """
                INSERT INTO Products
                (ProductID, ProductName, SupplierID, CategoryID, UnitPrice, UnitsInStock, Discontinued)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (1, "Chai", 1, 1, 18.0, 39, 0),
                    (2, "Chang", 1, 1, 19.0, 17, 0),
                    (3, "Aniseed Syrup", 1, 2, 10.0, 13, 0),
                    (4, "Chef Anton's Cajun Seasoning", 2, 2, 22.0, 53, 0),
                ],
            )
            conn.executemany(
                "INSERT INTO Customers (CustomerID, CompanyName, Country) VALUES (?, ?, ?)",
                [("ALFKI", "Alfreds Futterkiste", "Germany"), ("ANATR", "Ana Trujillo Emparedados", "Mexico")],
            )
            conn.executemany(
                "INSERT INTO Orders (OrderID, CustomerID, OrderDate, ShipCountry) VALUES (?, ?, ?, ?)",
                [(10248, "ALFKI", "1996-07-04", "France"), (10249, "ANATR", "1996-07-05", "Belgium")],
            )
            conn.executemany(
                "INSERT INTO OrderDetails (OrderID, ProductID, UnitPrice, Quantity, Discount) VALUES (?, ?, ?, ?, ?)",
                [(10248, 1, 18.0, 12, 0), (10249, 2, 19.0, 10, 0)],
            )

    def execute_select(self, query: str) -> list[dict[str, Any]]:
        cleaned = query.strip().rstrip(";")
        if not cleaned:
            raise ValueError("Query cannot be empty")

        lowered = cleaned.lower()
        if not (lowered.startswith("select") or lowered.startswith("with")):
            raise ValueError("Only SELECT queries are allowed")
        if self._FORBIDDEN_SQL.search(lowered):
            raise ValueError("Only read-only SQL is allowed")
        if ";" in cleaned:
            raise ValueError("Multiple SQL statements are not allowed")

        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(cleaned).fetchall()
            return [dict(row) for row in rows]


class OllamaNorthwindAgent:
    def __init__(self, db: NorthwindDatabase, model: str | None = None, base_url: str | None = None) -> None:
        self.db = db
        self.model = model or os.getenv("OLLAMA_MODEL", "llama3.1")
        self.base_url = base_url or os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

    async def stream_answer(self, question: str) -> AsyncGenerator[str, None]:
        schema_context = (
            "Northwind schema: Suppliers(SupplierID, CompanyName, Country), "
            "Categories(CategoryID, CategoryName), Products(ProductID, ProductName, SupplierID, CategoryID, UnitPrice, UnitsInStock, Discontinued), "
            "Customers(CustomerID, CompanyName, Country), Orders(OrderID, CustomerID, OrderDate, ShipCountry), "
            "OrderDetails(OrderID, ProductID, UnitPrice, Quantity, Discount)."
        )
        messages: list[dict[str, Any]] = [
            {
                "role": "system",
                "content": (
                    "You are a Northwind SQL assistant. Use the SQL tool for factual answers and provide concise business insights. "
                    + schema_context
                ),
            },
            {"role": "user", "content": question},
        ]

        tools = [
            {
                "type": "function",
                "function": {
                    "name": "run_sql_query",
                    "description": "Run a read-only SQL query against the Northwind database",
                    "parameters": {
                        "type": "object",
                        "properties": {"query": {"type": "string", "description": "SQL SELECT statement"}},
                        "required": ["query"],
                    },
                },
            }
        ]

        try:
            first_response = await self._chat(messages=messages, tools=tools, stream=False)
            assistant_message = first_response.get("message", {})
            tool_calls = assistant_message.get("tool_calls", [])

            if tool_calls:
                messages.append(assistant_message)
                for tool_call in tool_calls:
                    fn = tool_call.get("function", {})
                    if fn.get("name") != "run_sql_query":
                        continue
                    args = fn.get("arguments", {})
                    query = args.get("query", "") if isinstance(args, dict) else ""
                    rows = self.db.execute_select(query)
                    messages.append(
                        {
                            "role": "tool",
                            "name": "run_sql_query",
                            "content": json.dumps(rows),
                        }
                    )

                stream_chunks = await self._chat(messages=messages, stream=True)
                async for chunk in stream_chunks:
                    text = chunk.get("message", {}).get("content", "")
                    if text:
                        yield text
                return

            content = assistant_message.get("content", "")
            if content:
                yield content
            return

        except Exception:
            rows = self.db.execute_select(
                "SELECT ProductName, UnitsInStock FROM Products ORDER BY UnitsInStock DESC LIMIT 5"
            )
            yield (
                "I could not reach Ollama, but here is current inventory insight: "
                + ", ".join(f"{row['ProductName']} ({row['UnitsInStock']})" for row in rows)
            )

    async def _chat(self, messages: list[dict[str, Any]], stream: bool, tools: list[dict[str, Any]] | None = None):
        payload: dict[str, Any] = {"model": self.model, "messages": messages, "stream": stream}
        if tools:
            payload["tools"] = tools

        if not stream:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(f"{self.base_url}/api/chat", json=payload)
                response.raise_for_status()
                return response.json()

        async def _stream() -> AsyncGenerator[dict[str, Any], None]:
            async with httpx.AsyncClient(timeout=60.0) as client:
                async with client.stream("POST", f"{self.base_url}/api/chat", json=payload) as response:
                    response.raise_for_status()
                async for line in response.aiter_lines():
                    if not line:
                        continue
                    yield json.loads(line)

        return _stream()


DB_PATH = Path(os.getenv("NORTHWIND_DB_PATH", Path(__file__).resolve().parent / "data" / "northwind.db"))
database = NorthwindDatabase(DB_PATH)
database.initialize()
agent = OllamaNorthwindAgent(database)

app = FastAPI(title="Northwind Agent", version="0.1.0")


@app.on_event("startup")
def _startup() -> None:
    database.initialize()


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/chat")
async def chat(request: ChatRequest) -> dict[str, str]:
    chunks = [chunk async for chunk in agent.stream_answer(request.question)]
    answer = "".join(chunks).strip()
    if not answer:
        raise HTTPException(status_code=502, detail="No response generated")
    return {"response": answer}


@app.post("/chat/stream")
async def chat_stream(request: ChatRequest) -> StreamingResponse:
    return StreamingResponse(agent.stream_answer(request.question), media_type="text/plain")
