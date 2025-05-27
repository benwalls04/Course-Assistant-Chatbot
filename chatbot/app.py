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
import os
import requests

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

def get_conversation_chain(collection_name, course_id):

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

def handle_userinput(user_question):
  response = st.session_state.conversation({'question': user_question})
  st.session_state.chat_history = response["chat_history"]

  for i, message in enumerate(st.session_state.chat_history):
    if i % 2 == 0:
      st.write(user_template.replace("{{MSG}}", message.content), unsafe_allow_html=True)
    else: 
      st.write(bot_template.replace("{{MSG}}", message.content), unsafe_allow_html=True)

def get_courses(canvas_api_key, canvas_api_url):
  headers = {
    "Authorization": f"Bearer {canvas_api_key}"
  }
  response = requests.get(f"{canvas_api_url}/courses", headers=headers, params={"enrollment_state": "completed"})

  courses = []
  for course in response.json():
    if "name" in course:
      full_name = course["name"]
      if "-" in full_name and "(" in full_name:
          name_parts = full_name.split("-", 1)
          course_name = name_parts[1].split("(")[0]
          courses.append({
              "id": course["id"],
              "name": course_name
          })
      else: 
        courses.append({
          "id": course["id"],
          "name": full_name
        })
  return courses

def get_modules(canvas_api_key, canvas_api_url, course_id):
  headers = {
    "Authorization": f"Bearer {canvas_api_key}"
  }
  response = requests.get(f"{canvas_api_url}/courses/{course_id}/modules", headers=headers)

  modules = []

  for module in response.json():
    modules.append({
      "id": module["id"],
      "name": module["name"]
    })

  return modules

def handle_course_change(collection_name, course_id):
  st.session_state.chat_history = []
  st.session_state.previous_course = course_id
  st.session_state.user_question = ""
  
  if "question_input" in st.session_state:
      del st.session_state["question_input"]

  if st.session_state.processed:
      st.session_state.conversation = get_conversation_chain(collection_name, course_id)

def get_module_docs(canvas_api_key, canvas_api_url, course_id, module_id):
    headers = {
        "Authorization": f"Bearer {canvas_api_key}"
    }

    response = requests.get(f"{canvas_api_url}/courses/{course_id}/modules/{module_id}/items", headers=headers)

    items = []
    for item in response.json():
      if item["type"] == "File":
        items.append(item)
    
    st.write(items)

    return items

def main():
  load_dotenv()
  client = chromadb.PersistentClient(path="chroma_db")
  user_id = "user_1"
  collection_name = f"user_{user_id}_collection"
  try:
    collection = client.get_collection(name=collection_name)
  except Exception as e:
    collection = client.create_collection(name=collection_name)


  canvas_api_key = os.getenv("CANVAS_API_KEY")
  canvas_api_url = "https://canvas.instructure.com/api/v1"
  courses = get_courses(canvas_api_key, canvas_api_url)
  modules = get_modules(canvas_api_key, canvas_api_url, courses[0]["id"])

  st.set_page_config(page_title="Course Assistant", page_icon=":books:")
  st.write(css, unsafe_allow_html=True)

  if "conversation" not in st.session_state:
    st.session_state.conversation = None
  if "chat_history" not in st.session_state:
    st.session_state.chat_history = None
  if "processed" not in st.session_state:
    st.session_state.processed = False

  st.header("Course Assistant")

  # Create a selectbox for course selection
  course_names = [course["name"] for course in courses]
  selected_course = st.selectbox(
    "Select a course:",
    options=course_names,
    index=0 if course_names else None
  )

  # Get the selected course ID
  selected_course_id = next(
    (course["id"] for course in courses if course["name"] == selected_course),
    None
  )

  if selected_course:
    st.subheader(f"Selected Course: {selected_course}")
    
    # Check if course has changed
    if "previous_course" not in st.session_state:
        st.session_state.previous_course = selected_course_id
    elif st.session_state.previous_course != selected_course_id:
        handle_course_change(collection_name, selected_course_id)
        modules = get_modules(canvas_api_key, canvas_api_url, selected_course_id)

  with st.sidebar:
    st.subheader("Your documents")
    
    # Get existing documents from the collection
    existing_docs = collection.get()
    if existing_docs and existing_docs['metadatas']:
      # Get unique file names from metadata
      file_names = set()
      for metadata in existing_docs['metadatas']:
        if 'file_name' in metadata and 'course_id' in metadata and metadata['course_id'] == selected_course_id:
          file_names.add(metadata['file_name'])
      
      for i, file_name in enumerate(sorted(file_names)):
        st.write(f"{i+1}. {file_name}")
      
      # If there are existing documents, set processed to True and create conversation chain
      st.session_state.processed = True
      if not st.session_state.conversation:
        st.session_state.conversation = get_conversation_chain(collection_name, selected_course_id)

    st.subheader("Download a module")
    module_names = ["No module selected"] + [module["name"] for module in modules]
    selected_module = st.selectbox("Select a module:", options=module_names, index=0 if module_names else None)
    
    docs = st.file_uploader("Or upload your PDFs here and click on 'Process'", accept_multiple_files=True)
    
    if st.button("Process"):  
      with st.spinner("Processing"): 

        if selected_module != "No module selected":
          module_id = next(module["id"] for module in modules if module["name"] == selected_module)
          docs = get_module_docs(canvas_api_key, canvas_api_url, selected_course_id, module_id)
        
        # get the text 
        raw_text = get_pdf_text(docs)

        # get the text chunks 
        text_chunks = get_text_chunks(raw_text)

        # create vector store 
        store_docs(collection, docs, text_chunks, user_id, selected_course_id)
    
        # create conversation chain
        st.session_state.conversation = get_conversation_chain(collection_name, selected_course_id)
        st.session_state.processed = True
        st.success("Documents processed successfully!")

  # Always create a new conversation chain when the page loads
  if st.session_state.processed:
    # Initialize user_question in session state if it doesn't exist
    if "user_question" not in st.session_state:
        st.session_state.user_question = ""
    
    # Use the session state variable for the text input
    user_question = st.text_input(
        "Ask a question about your documents:",
        value=st.session_state.user_question,
        key="question_input"
    )
    
    # Update session state with new question
    st.session_state.user_question = user_question
    
    if user_question:
        handle_userinput(user_question)
  else:
    st.info("Please upload and process your documents first!")


if __name__ == '__main__':
  main()