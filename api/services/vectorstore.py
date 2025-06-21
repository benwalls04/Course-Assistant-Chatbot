from langchain_community.embeddings import HuggingFaceEmbeddings
from datetime import datetime
import chromadb
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma
from langchain.memory import ConversationBufferMemory
from langchain.chains import ConversationalRetrievalChain
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv
from chromadb.config import Settings

class VectorStoreService:
  def __init__(self):
    load_dotenv()

    # Set up embedding model once
    self.embedding_model = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")

    # Create only ONE ChromaDB PersistentClient instance
    try:
        self.client = chromadb.PersistentClient(path="chroma_db")
        print("[VectorStoreService] Connected to ChromaDB at path: chroma_db")
    except Exception as e:
        print("[VectorStoreService] Failed to connect to ChromaDB:", e)
        raise e

  def get_collection(self, user_id):
      collection_name = self.get_collection_name(user_id)
      try:
          collection = self.client.get_collection(name=collection_name)
          print(f"[VectorStoreService] Found existing collection: {collection_name}")
          return collection
      except:
          print(f"[VectorStoreService] Creating new collection: {collection_name}")
          return self.client.create_collection(name=collection_name)

  def get_collection_name(self, user_id):
    return f"user_{user_id}_collection"
  
  def get_conversation_chain(self, collection_name, course_id):  
    vectorstore = Chroma(
      client=self.client,
      collection_name=collection_name,
      embedding_function=self.embedding_model,
      persist_directory="chroma_db"
    )

    llm = ChatOpenAI(
      temperature=0.5,
      model_name="gpt-3.5-turbo"  
    )
    memory = ConversationBufferMemory(memory_key="chat_history", return_messages=True)

    retriever = vectorstore.as_retriever(
      search_kwargs={
        "filter": {
            "course_id": course_id
        }
      }
    )

    conversation_chain = ConversationalRetrievalChain.from_llm( 
      llm=llm,
      retriever=retriever,
      memory=memory
    )
    return conversation_chain

  def store_docs(self, text_chunks, metadata):
    print(f"[store_docs] Attempting to store {len(text_chunks)} chunks...")

    embeddings = self.embedding_model.embed_documents(text_chunks)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    collection = self.get_collection(metadata[0]["user_id"])
    print(f"[store_docs] Using collection: {collection.name}")

    collection.add(
        documents=text_chunks,
        embeddings=embeddings,
        ids=[f"{timestamp}_chunk{i}" for i in range(len(text_chunks))],
        metadatas=metadata
    )

    print(f"[store_docs] Successfully stored all chunks.")




