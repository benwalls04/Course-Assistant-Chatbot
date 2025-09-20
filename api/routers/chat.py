from fastapi import APIRouter, HTTPException
router = APIRouter()
from services.vectorstore_instance import vectorstore_service
from pydantic import BaseModel
from typing import List, Dict, Any
from services.redis_client import redis_client
from fastapi.responses import JSONResponse
from langchain.schema import BaseMessage

# Example Pydantic model for request body
class ChatRequest(BaseModel):
    user_id: str
    course_id: int
    question: str

@router.get("")
async def get_conversation_chain(user_id: str, course_id: str):
    key = f"{user_id}-{course_id}-chat"
    msgs = redis_client.lrange(key, 0, -1)
    
    res = []
    for i, m in enumerate(msgs):
        res.append({"content": m})

    return res

@router.post("/query")
async def chat_endpoint(chat_req: ChatRequest):
    user_id, course_id = chat_req.user_id, str(chat_req.course_id)

    key = f"{user_id}-{course_id}-chat"
    chain = vectorstore_service.get_conversation_chain(user_id, course_id)

    try:
        result = chain({"question": chat_req.question})
        answer = result.get("answer", "Sorry, no answer available.")

        redis_client.rpush(key, chat_req.question)
        redis_client.rpush(key, answer)

        return {
            "answer": answer,
            "chat_history": result.get("chat_history", [])
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))