import streamlit as st 
from dotenv import load_dotenv
from PyPDF2 import PdfReader
from langchain.text_splitter import CharacterTextSplitter
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma
from langchain.memory import ConversationBufferMemory
from langchain.chains import ConversationalRetrievalChain
from langchain_openai import ChatOpenAI
from htmlTemplates import css, bot_template, user_template
import chromadb
from datetime import datetime

def get_pdf_text(pdf_docs):
  text = ""
  for pdf in pdf_docs:
    pdf_reader = PdfReader(pdf)
    for page in pdf_reader.pages:
      text += page.extract_text()

    return text

def get_text_chunks(raw_text):
  text_splitter = CharacterTextSplitter(
    separator = "\n",
    chunk_size=1000,
    chunk_overlap=200,
    length_function=len
  )
  chunks = text_splitter.split_text(raw_text)
  return chunks


def get_conversation_chain(collection_name):

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

  conversation_chain = ConversationalRetrievalChain.from_llm( 
    llm=llm,
    retriever=vectorstore.as_retriever(),
    memory=memory
  )

  return conversation_chain

def handle_userinput(user_question):
  response = st.session_state.conversation({'question': user_question})
  st.session_state.chat_history = response["chat_history"]

  for i, message in enumerate(st.session_state.chat_history):
    if i % 2 == 0:
      st.write(user_template.replace("{{MSG}}", message.content), unsafe_allow_html=True)
    else: 
      st.write(bot_template.replace("{{MSG}}", message.content), unsafe_allow_html=True)

def get_collection(client, collection_name):
  try:
    collection = client.get_collection(name=collection_name)
  except Exception as e:
    collection = client.create_collection(name=collection_name)

  return collection

def main():
  load_dotenv()
  client = chromadb.PersistentClient(path="chroma_db")
  user_id = "user_1"
  collection_name = f"user_{user_id}_collection"
  collection = get_collection(client, collection_name)

  st.set_page_config(page_title="Course Assistant", page_icon=":books:")
  st.write(css, unsafe_allow_html=True)

  if "conversation" not in st.session_state:
    st.session_state.conversation = None
  if "chat_history" not in st.session_state:
    st.session_state.chat_history = None
  if "processed" not in st.session_state:
    st.session_state.processed = False

  st.header("Select course, download materials, ask questions")

  with st.sidebar:
    st.subheader("Your documents")
    
    # Get existing documents from the collection
    existing_docs = collection.get()
    if existing_docs and existing_docs['metadatas']:
      st.write("Previously uploaded documents:")
      # Get unique file names from metadata
      file_names = set()
      for metadata in existing_docs['metadatas']:
        if 'file_name' in metadata:
          file_names.add(metadata['file_name'])
      
      for i, file_name in enumerate(sorted(file_names)):
        st.write(f"{i+1}. {file_name}")
      
      # If there are existing documents, set processed to True and create conversation chain
      st.session_state.processed = True
      if not st.session_state.conversation:
        st.session_state.conversation = get_conversation_chain(collection_name)
    
    docs = st.file_uploader("Upload your PDFs here and click on 'Process'", accept_multiple_files=True)
    if st.button("Process"):
      with st.spinner("Processing"): 
        # get the text 
        raw_text = get_pdf_text(docs)

        # get the text chunks 
        text_chunks = get_text_chunks(raw_text)

        # create vector store 
        embedding_model = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
        embeddings = embedding_model.embed_documents(text_chunks)
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Create metadata with file names
        metadatas = []
        for doc in docs:
          for _ in range(len(text_chunks) // len(docs)):  # Distribute chunks across files
            metadatas.append({
              "user_id": user_id,
              "course_name": "Course 1",
              "file_name": doc.name
            })

        collection.add(
          documents=text_chunks,
          embeddings=embeddings,
          ids=[f"{timestamp}_chunk{i}" for i in range(len(text_chunks))],
          metadatas=metadatas
        )

        # create conversation chain
        st.session_state.conversation = get_conversation_chain(collection_name)
        st.session_state.processed = True
        st.success("Documents processed successfully!")

  # Always create a new conversation chain when the page loads
  if st.session_state.processed:
    user_question = st.text_input("Ask a question about your documents:")
    if user_question:
      handle_userinput(user_question)
  else:
    st.info("Please upload and process your documents first!")


if __name__ == '__main__':
  main()