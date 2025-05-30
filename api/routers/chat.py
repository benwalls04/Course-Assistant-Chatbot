from fastapi import APIRouter
router = APIRouter()

@router.post("/chat")
async def chat(user_id, selected_course_id, message):
  pass

@router.get("/collection")
async def get_collection(user_id, client):
  collection_name = f"user_{user_id}_collection"
  try:
    collection = client.get_collection(name=collection_name)
  except Exception as e:
    collection = client.create_collection(name=collection_name)

  return collection

