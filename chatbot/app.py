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
import os
import requests
backend_url = "http://localhost:8000"

def handle_userinput(user_question):
  response = st.session_state.conversation({'question': user_question})
  st.session_state.chat_history = response["chat_history"]

  for i, message in enumerate(st.session_state.chat_history):
    if i % 2 == 0:
      st.write(user_template.replace("{{MSG}}", message.content), unsafe_allow_html=True)
    else: 
      st.write(bot_template.replace("{{MSG}}", message.content), unsafe_allow_html=True)

def handle_course_change(selected_course_name, course_id):
    st.session_state.selected_course = selected_course_name
    st.session_state.course_id = course_id
    st.session_state.chat_history = []
    st.session_state.user_question = ""
    
    if "question_input" in st.session_state:
        del st.session_state["question_input"]

    if st.session_state.processed:
        response = requests.get(f"{backend_url}/chat", params={
            'user_id': st.session_state.user_id,
            'course_id': course_id
        })
        if response.status_code == 200:
            st.session_state.conversation = response.json()
        else:
            st.error("Failed to get conversation chain")

def show_existing_files():    
  # Get existing documents from the collection
  response = requests.get(f"{backend_url}/files", params={
    'user_id': st.session_state.user_id,
    'selected_course_id': st.session_state.course_id
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
      st.session_state.conversation = requests.get(f"{backend_url}/chat", params={
        'user_id': st.session_state.user_id,
        'course_id': st.session_state.course_id
      })

  else: 
    st.error("Error fetching files")

def show_conversation():
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

def download_module(module_id):
  file_details = requests.get(f"{backend_url}/courses/items", params={
    'course_id': st.session_state.course_id,
    'module_id': module_id
  })
  
  if file_details:
    st.write("Found files:")
    for file in file_details:
        st.write(f"- {file['name']} ({file['content_type']})")
    
    # Ingest canvas files first
    requests.post(f"{backend_url}/files/ingest_canvas_files", params={
      'file_details': file_details,
      'user_id': st.session_state.user_id,
      'course_id': st.session_state.course_id
    })

def main():
  load_dotenv()
  #TODO: add auth
  st.session_state.user_id = "user_1"
  
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
  if "course_id" not in st.session_state:
    st.session_state.course_id = None
  if "selected_course" not in st.session_state:
    st.session_state.selected_course = None

  st.header("Course Assistant")

  # Course selection
  course_options = {course['name']: course['id'] for course in courses}
  selected_course_name = st.selectbox(
      "Select a course",
      options=list(course_options.keys()),
      index=0 if not st.session_state.selected_course else list(course_options.keys()).index(st.session_state.selected_course)
  )

  # Update session state when course changes
  if selected_course_name != st.session_state.selected_course:
      handle_course_change(selected_course_name, course_options[selected_course_name])

  # Module selection
  modules = requests.get(f"{backend_url}/courses/modules", params={
    'course_id': st.session_state.course_id
  })

  with st.sidebar:
    st.subheader("Your documents")
    show_existing_files()

    st.subheader("Download a module")
    module_names = ["No module selected"] + [module["name"] for module in modules]
    selected_module = st.selectbox("Select a module:", options=module_names, index=0 if module_names else None)
    
    uploaded_docs = st.file_uploader("Or upload your PDFs here and click on 'Process'", accept_multiple_files=True)
    
    if st.button("Process"):  
      with st.spinner("Processing"): 

        if selected_module != "No module selected":
          module_id = next(module["id"] for module in modules if module["name"] == selected_module)
          download_module(module_id)

        # Ingest uploaded files 
        requests.post(f"{backend_url}/files/ingest_uploaded_files", params={
          'docs': uploaded_docs,
          'user_id': st.session_state.user_id,
          'selected_course_id': st.session_state.course_id
        })
    
        # create conversation chain
        st.session_state.conversation = requests.get(f"{backend_url}/chat", params={
          'user_id': st.session_state.user_id,
          'course_id': st.session_state.course_id
        })
        st.session_state.processed = True
        st.success("Documents processed successfully!")

  # Always create a new conversation chain when the page loads
  if st.session_state.processed:
    show_conversation()
  else:
    st.info("Please upload and process your documents first!")

if __name__ == '__main__':
  main()