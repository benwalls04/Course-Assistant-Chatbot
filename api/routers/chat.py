from fastapi import APIRouter, HTTPException
router = APIRouter()
from services.vectorstore_instance import vectorstore_service
from pydantic import BaseModel
from typing import List, Dict, Any

# Example Pydantic model for request body
class ChatRequest(BaseModel):
    user_id: str
    course_id: int
    question: str

@router.get("")
async def get_conversation_chain(user_id, course_id):
  collection_name = vectorstore_service.get_collection_name(user_id)
  conversation_chain = vectorstore_service.get_conversation_chain(collection_name, course_id)
  return conversation_chain

@router.post("/query")
async def chat_endpoint(chat_req: ChatRequest):
    collection_name = vectorstore_service.get_collection_name(chat_req.user_id)
    chain = vectorstore_service.get_conversation_chain(collection_name, str(chat_req.course_id))

    try:
        result = chain({"question": chat_req.question})
        return {
            "answer": result.get("answer", "Sorry, no answer available."),
            "chat_history": result.get("chat_history", [])
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))