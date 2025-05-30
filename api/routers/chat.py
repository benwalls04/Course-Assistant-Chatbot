from fastapi import APIRouter
router = APIRouter()
from main import vectorstore_service

@router.get()
async def get_conversation_chain(user_id, course_id):
  collection_name = vectorstore_service.get_collection_name(user_id)
  conversation_chain = vectorstore_service.get_conversation_chain(collection_name, course_id)
  return conversation_chain


