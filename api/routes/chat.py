from fastapi import APIRouter
from api.models.ChatModel import ChatRequest
from services.AgentService import AgentDep
chat = APIRouter(prefix="/chat", tags=["chat"])
from fastapi.responses import StreamingResponse
import json

@chat.post("/")
def chat_agent(agent_service: AgentDep, body: ChatRequest):
    def generate():
        response = agent_service.chat(body.message)
        message = str(response)
        
        # Stream by newline or fixed size chunks
        lines = message.split('\n')
        for line in lines:
            if line.strip():
                yield json.dumps({"chunk": line.strip()}) + "\n"
            
    return StreamingResponse(generate(), media_type="application/x-ndjson")

