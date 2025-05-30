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
    self.client = chromadb.PersistentClient(
      path="chroma_db",
      settings=Settings(allow_reset=True)
    )
    load_dotenv()

  def get_collection(self, user_id):
    collection_name = self.get_collection_name(user_id)

    try:
      return self.client.get_collection(name=collection_name)
    except:
      return self.client.create_collection(name=collection_name)

  def get_collection_name(self, user_id):
    return f"user_{user_id}_collection"
  
  def get_conversation_chain(self, collection_name, course_id):  
    vectorstore = Chroma(
      collection_name=collection_name,
      embedding_function=HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2"),
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

  def store_docs(self, docs, text_chunks, user_id, course_id):
    embedding_model = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
    embeddings = embedding_model.embed_documents(text_chunks)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Create metadata with file names
    metadatas = []
    for doc in docs:
      for _ in range(len(text_chunks) // len(docs)):
        metadatas.append({
          "user_id": user_id,
          "course_id": course_id,
          "file_name": doc.name
        })

    collection = self.get_collection(user_id)

    collection.add(
      documents=text_chunks,
      embeddings=embeddings,
      ids=[f"{timestamp}_chunk{i}" for i in range(len(text_chunks))],
      metadatas=metadatas
    )


