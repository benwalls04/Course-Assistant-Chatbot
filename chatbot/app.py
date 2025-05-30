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
import io
import mimetypes

backend_url = "http://localhost:8000"

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
    
    try:
        response = requests.get(
            f"{canvas_api_url}/courses/{course_id}/modules/{module_id}/items", 
            headers=headers
        )
        
        if response.status_code == 200:
            items = response.json()
            
            # Filter for only file items
            file_items = [item for item in items if item.get('type') == 'File']
            
            if not file_items:
                st.warning("No files found in this module.")
                return []
                
            # Get file details for each file item
            file_details = []
            for file_item in file_items:
                file_id = file_item['content_id']
                file_response = requests.get(
                    f"{canvas_api_url}/files/{file_id}",
                    headers=headers
                )
                
                if file_response.status_code == 200:
                    file_data = file_response.json()
                    file_details.append({
                        'id': file_id,
                        'name': file_data['display_name'],
                        'url': file_data['url'],
                        'content_type': file_data['content-type']
                    })
                else:
                    st.error(f"Error fetching file details for {file_item['title']}: {file_response.status_code}")
            
            return file_details
            
        elif response.status_code == 404:
            st.error(f"Module not found. Please check if the module ID {module_id} is correct.")
            return []
        elif response.status_code == 401:
            st.error("Authentication failed. Please check your API key.")
            return []
        else:
            st.error(f"Error fetching module items: {response.status_code}")
            st.write("Error Response:", response.text)
            return []
            
    except Exception as e:
        st.error(f"Error making request: {str(e)}")
        return []

def show_existing_files(collection, selected_course_id, collection_name):    
  # Get existing documents from the collection
  response = requests.get(f"{backend_url}/files", params={
    'collection': collection,
    'selected_course_id': selected_course_id
  })

  if response.status_code == 200:
    file_names = response.json()
    for file_name in file_names:
      st.write(f"{file_name}")
    
    for i, file_name in enumerate(sorted(file_names)):
      st.write(f"{i+1}. {file_name}")
    
    # If there are existing documents, set processed to True and create conversation chain
    st.session_state.processed = True
    if not st.session_state.conversation:
      st.session_state.conversation = get_conversation_chain(collection_name, selected_course_id)

  else: 
    st.error("Error fetching files")

def show_user_question():
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

def main():
  load_dotenv()
  client = chromadb.PersistentClient(path="chroma_db")

  #TODO: add auth
  user_id = "user_1"
  collection_name = f"user_{user_id}_collection"

  response = requests.get(
    f"{backend_url}/chat/collection",
    params={
      'user_id': user_id,
      'client': client
    },
  )
  collection = response.json()

  canvas_api_key = os.getenv("CANVAS_API_KEY")
  canvas_api_url = "https://canvas.instructure.com/api/v1"

  courses = requests.get(f"{backend_url}/courses")
  modules = requests.get(f"{backend_url}/courses/modules", params={
    'course_id': courses[0]["id"]
  })

  st.set_page_config(page_title="Course Assistant", page_icon=":books:")
  st.write(css, unsafe_allow_html=True)

  if "conversation" not in st.session_state:
    st.session_state.conversation = None
  if "chat_history" not in st.session_state:
    st.session_state.chat_history = None
  if "processed" not in st.session_state:
    st.session_state.processed = False

  st.header("Course Assistant")

  # Initialize session state for course and module if not already set
  if 'selected_course' not in st.session_state:
      st.session_state.selected_course = None
  if 'selected_module' not in st.session_state:
      st.session_state.selected_module = None

  # Course selection
  course_options = {course['name']: course['id'] for course in courses}
  selected_course_name = st.selectbox(
      "Select a course",
      options=list(course_options.keys()),
      index=0 if not st.session_state.selected_course else list(course_options.keys()).index(st.session_state.selected_course)
  )

  # Update session state when course changes
  if selected_course_name != st.session_state.selected_course:
      st.session_state.selected_course = selected_course_name
      st.session_state.selected_module = None  # Reset module when course changes

  selected_course_id = course_options[selected_course_name]

  # Module selection
  modules = requests.get(f"{backend_url}/courses/modules", params={
    'course_id': selected_course_id
  })

  with st.sidebar:
    st.subheader("Your documents")
    show_existing_files(collection, selected_course_id, collection_name)

    st.subheader("Download a module")
    module_names = ["No module selected"] + [module["name"] for module in modules]
    selected_module = st.selectbox("Select a module:", options=module_names, index=0 if module_names else None)
    
    all_docs = []
    uploaded_docs = st.file_uploader("Or upload your PDFs here and click on 'Process'", accept_multiple_files=True)
    all_docs.extend(uploaded_docs)
    
    if st.button("Process"):  
      with st.spinner("Processing"): 

        if selected_module != "No module selected":
          module_id = next(module["id"] for module in modules if module["name"] == selected_module)
          file_details = get_module_docs(canvas_api_key, canvas_api_url, selected_course_id, module_id)
          
          if file_details:
            st.write(file_details)
            st.write("Found files:")
            for file in file_details:
                st.write(f"- {file['name']} ({file['content_type']})")
            
            # Download files to the uploads directory
            for file in file_details:
              response = requests.get(file['url'])
              if response.status_code == 200:
                  # Save to the uploads directory
                  file_path = os.path.join(os.path.dirname(__file__), 'uploads', file['name'])
                  os.makedirs(os.path.dirname(file_path), exist_ok=True)
                  
                  # Save the file
                  with open(file_path, 'rb') as f:
                    file_bytes = f.read()

                  uploaded_like_file = io.BytesIO(file_bytes)
                  uploaded_like_file.name = file['name']  # Streamlit uploader sets .name
                  uploaded_like_file.type = mimetypes.guess_type(file['name'])[0] or "application/octet-stream"

                  all_docs.append(uploaded_like_file)

        raw_text = get_pdf_text(all_docs)
        text_chunks = get_text_chunks(raw_text)
        store_docs(collection, all_docs, text_chunks, user_id, selected_course_id)
    
        # create conversation chain
        st.session_state.conversation = get_conversation_chain(collection_name, selected_course_id)
        st.session_state.processed = True
        st.success("Documents processed successfully!")

  # Always create a new conversation chain when the page loads
  if st.session_state.processed:
    show_user_question()
  else:
    st.info("Please upload and process your documents first!")


if __name__ == '__main__':
  main()