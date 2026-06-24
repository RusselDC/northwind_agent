"""Agent service module for interacting with the Ollama-backed AI agent."""
from typing import Annotated, Any

from fastapi import Depends
from sqlalchemy import text
from strands import tool, Agent
from strands.models.ollama import OllamaModel

from config import settings
from dep import Session


def make_supplier_tool(db: Session):
    """Create and return a supplier_info tool with an injected database session."""
    @tool
    def supplier_info(product_name: str) -> Any:
        """Get supplier information for given product names
    Args :
            product_name (str): The name of the product to search for. 
            Can be a partial name, and the search will be case-insensitive.
        """

        base_query = (
            "select * from products p "
            "left join suppliers s on s.supplier_id = p.supplier_id "
            "where p.product_name ILIKE :product_name"
        )
        
        print(product_name)

        print(f"Generated SQL Query: {base_query}")
        result = db.execute(text(base_query), {"product_name": f"%{product_name.lower()}%"})  # type: ignore
        rows = result.fetchall()
        print(f"Query Result: {rows}")
        return [row._asdict() for row in rows]

    return supplier_info


class AgentService:
    """Service for interacting with the AI agent backed by an Ollama model."""

    def __init__(self, model: OllamaModel, session: Session):
        self.model = model
        self.db = session

    def _system_prompt(self) -> str:
        return """You are a helpful assistant for answering questions about the northwind database. 

IMPORTANT: You MUST use the supplier_info tool to answer any question about products and their suppliers.

Instructions:
1. For any question about products, suppliers, or product details, ALWAYS call the supplier_info tool with the product name
2. Extract the product name from the user's question
3. Call the tool with the product name to get real data
4. Present the results to the user in a clear format
5. Do NOT give instructions on how to query - actually call the tool and provide the results

Example: If asked "Who supplies Chai?", call supplier_info("Chai") and show the results."""

    def _ask_agent(self) -> Agent:
        supplier_tool = make_supplier_tool(self.db)  # inject db into tool
        agent = Agent(model=self.model, tools=[supplier_tool], system_prompt=self._system_prompt())
        return agent

    def chat(self, message: str) -> Any:
        """Send a message to the agent and return its response."""
        agent = self._ask_agent()
        response = agent(message)  # agent extracts product names and calls supplier_info
        return response


def get_ollama_model() -> OllamaModel:
    """Instantiate and return the OllamaModel using settings."""
    return OllamaModel(model_id=settings.AGENT_NAME, host="localhost")

def get_agent_service(
    session: Session,
    model: OllamaModel = Depends(get_ollama_model),
) -> AgentService:
    """Instantiate and return an AgentService with the given session and model."""
    return AgentService(model=model, session=session)

AgentDep = Annotated[AgentService, Depends(get_agent_service)]
