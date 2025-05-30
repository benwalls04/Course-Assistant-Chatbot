from langchain_community.embeddings import HuggingFaceEmbeddings
from datetime import datetime
import chromadb
from chromadb.config import Settings

class VectorStoreService:
  def __init__(self):
    self.client = chromadb.PersistentClient(
      path="chroma_db",
      settings=Settings(allow_reset=True)
    )

  def get_collection(self, user_id):
    collection_name = f"user_{user_id}_collection"
    try:
      return self.client.get_collection(name=collection_name)
    except:
      return self.client.create_collection(name=collection_name)

  def store_docs(collection, docs, text_chunks, user_id, course_id):
    embedding_model = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
    embeddings = embedding_model.embed_documents(text_chunks)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Create metadata with file names
    metadatas = []
    for doc in docs:
      for _ in range(len(text_chunks) // len(docs)):  # Distribute chunks across files
        metadatas.append({
          "user_id": user_id,
          "course_id": course_id,
          "file_name": doc.name
        })

    collection.add(
      documents=text_chunks,
      embeddings=embeddings,
      ids=[f"{timestamp}_chunk{i}" for i in range(len(text_chunks))],
      metadatas=metadatas
    )


