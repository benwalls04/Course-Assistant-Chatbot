from fastapi import APIRouter
from services.text import TextService
from fastapi import HTTPException
import requests
from services.vectorstore_instance import vectorstore_service
from fastapi import Body, Query
from typing import List, Dict
from pydantic import BaseModel
from io import BytesIO
from services.redis_client import redis_client
router = APIRouter()
text_service = TextService()

class FileDetails(BaseModel):
  id: int
  name: str
  url: str
  content_type: str

@router.get("")
async def get_files(user_id, selected_course_id):

    key = f"{user_id}-{selected_course_id}-files"
    if redis_client.llen(key) == 0:
      return []
    else:
      return redis_client.lrange(key, 0, -1)

# @router.post("/ingest_uploaded_files")
# async def upload_docs(docs, user_id, selected_course_id):
#     raw_text = text_service.get_pdf_text(docs)
#     text_chunks = text_service.get_text_chunks(raw_text)
#     vectorstore_service.store_docs(docs, text_chunks, user_id, selected_course_id)
    
@router.post("/ingest_canvas_files")
async def ingest_canvas_files(
    file_details: List[FileDetails] = Body(...),
    user_id: str = Query(...),
    course_id: str = Query(...)
):
  all_text_chunks = []
  all_metadatas = []

  key = f"{user_id}-{course_id}-files"
  existing_files = redis_client.lrange(key, 0, -1)

  for file in file_details:
    response = requests.get(file.url)
    if response.status_code != 200 or file.content_type != 'application/pdf' or file.name in existing_files:
      continue

    text_chunks = text_service.get_pdf_text_chunks(BytesIO(response.content))
    all_text_chunks.extend(text_chunks)
    all_metadatas.extend([{
      "user_id": user_id,
      "course_id": course_id,
      "file_name": file.name
    }] * len(text_chunks))
    redis_client.rpush(key, file.name)
  
  vectorstore_service.store_docs(all_text_chunks, all_metadatas)
