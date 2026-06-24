from sqlmodel import SQLModel


class ChatRequest(SQLModel):
    message:str