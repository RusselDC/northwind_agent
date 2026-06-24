from fastapi import APIRouter
from api.routes.chat import chat

router = APIRouter()


router.include_router(chat)