from fastapi import APIRouter
from services.text import TextService
from fastapi import HTTPException
import requests
from services.vectorstore_instance import vectorstore_service
from fastapi import Body, Query
from typing import List, Dict
from pydantic import BaseModel
from io import BytesIO
router = APIRouter()
text_service = TextService()

class FileDetails(BaseModel):
  id: int
  name: str
  url: str
  content_type: str

@router.get("")
async def get_files(user_id, selected_course_id):
    collection = vectorstore_service.get_collection(user_id)
    existing_docs = collection.get()
    if existing_docs and existing_docs['metadatas']:
        # Get unique file names from metadata
        file_names = set()
        for metadata in existing_docs['metadatas']:
            if 'file_name' in metadata and 'course_id' in metadata and metadata['course_id'] == selected_course_id:
                file_names.add(metadata['file_name'])
        return file_names
    else: 
        raise HTTPException(status_code=404, detail="No files found")

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

  existing = vectorstore_service.get_collection(user_id).get()
  existing_files = {meta.get("file_name") for meta in existing.get("metadatas", [])}

  for file in file_details:
    response = requests.get(file.url)
    if response.status_code == 200:
      if not file.content_type == 'application/pdf':
        print(f"[ingest] Skipping {file.name}: not a PDF file")
        continue
      elif file.name in existing_files:
        print(f"[ingest] Skipping {file.name}: already exists in collection")
        continue
      else:
        text_chunks = text_service.get_pdf_text_chunks(BytesIO(response.content))
        print("text chunks: ", len(text_chunks))
        all_text_chunks.extend(text_chunks)
        all_metadatas.extend([{
          "user_id": user_id,
          "course_id": course_id,
          "file_name": file.name
        }] * len(text_chunks))
    else:
      print(f"[ingest] Skipping {file.name}: failed to download file")
      continue
    
  vectorstore_service.store_docs(all_text_chunks, all_metadatas)
