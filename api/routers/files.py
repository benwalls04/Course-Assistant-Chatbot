from fastapi import APIRouter
from services.text import TextService
from services.vectorstore import VectorStoreService
from fastapi import HTTPException

router = APIRouter()

@router.post()
async def upload_docs(docs, user_id, selected_course_id):
  text_service = TextService()
  vector_store_service = VectorStoreService()

  raw_text = text_service.get_pdf_text(docs)
  text_chunks = text_service.get_text_chunks(raw_text)
  vector_store_service.store_docs(docs, text_chunks, user_id, selected_course_id)

  pass

@router.get()
async def get_files(collection, selected_course_id):
  existing_docs = collection.get()
  if existing_docs and existing_docs['metadatas']:
    # Get unique file names from metadata
    file_names = set()
    for metadata in existing_docs['metadatas']:
      if 'file_name' in metadata and 'course_id' in metadata and metadata['course_id'] == selected_course_id:
        file_names.add(metadata['file_name'])
    return file_names
  else: 
    return HTTPException(status_code=404, detail="No files found")
      

