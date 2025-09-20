import streamlit as st 
from dotenv import load_dotenv
from htmlTemplates import css, bot_template, user_template
import requests

backend_url = "http://localhost:8000"

def handle_submit():
  user_question = st.session_state.user_question
  if user_question:
    handle_userinput(user_question)
    # Clear the input after processing
    st.session_state.user_question = ""

def handle_userinput(user_question):
    payload = {
        "user_id": st.session_state.user_id,
        "course_id": st.session_state.course_id,
        "question": user_question
    }

    response = requests.post(f"{backend_url}/chat/query", json=payload)

    if response.status_code == 200:
      data = response.json()
      chat_history = data.get("chat_history", [])
      st.session_state.chat_history = chat_history

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
            'course_id': course_id,
        })
        if response.status_code == 200:
            st.session_state.chat_history = response.json()
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
    if len(file_names) > 0:
      for file_name in file_names:
        st.write(f"{file_name}")
    else:
       st.write("No documents found")
    

  elif response.status_code == 404:
    st.write("No documents found for this course")
  else: 
    st.error("Error fetching files")

def show_conversation():
    st.session_state.chat_history = requests.get(f"{backend_url}/chat", params={
        'user_id': st.session_state.user_id,
        'course_id': st.session_state.course_id
      }).json()

    # Text input with automatic submit on Enter or focus loss
    st.text_input(
        "Ask a question about your documents:",
        key="user_question",
        on_change=handle_submit
    )

    # Display chat history
    if st.session_state.chat_history and len(st.session_state.chat_history) > 0:
        for i, message in enumerate(st.session_state.chat_history[::-1]):
            if i % 2 == 0:
                st.write(bot_template.replace("{{MSG}}", message['content']), unsafe_allow_html=True)
            else:
                st.write(user_template.replace("{{MSG}}", message['content']), unsafe_allow_html=True)

def download_module(module_id):
  response = requests.get(f"{backend_url}/courses/items", params={
    'course_id': st.session_state.course_id,
    'module_id': module_id
  })
  
  if response.status_code == 200:
    file_details = response.json()

    if len(file_details) > 0: 
      st.write("Found files:")
      for file in file_details:
          st.write(f"- {file['name']} ({file['content_type']})")
      
      # Ingest canvas files first
      requests.post(f"{backend_url}/files/ingest_canvas_files",
      params={
          'user_id': st.session_state.user_id,
          'course_id': st.session_state.course_id
      },
      json=file_details 
      )
    else:
      st.write("No downloadable files found in this module")

def main():
  load_dotenv()

  st.set_page_config(page_title="Course Assistant", page_icon=":books:")
  st.write(css, unsafe_allow_html=True)

  # Initialize session state variables
  if "user_id" not in st.session_state:
    st.session_state.user_id = "user1"
  if "init" not in st.session_state:
    st.session_state.init = False
  if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
  if "processed" not in st.session_state:
    st.session_state.processed = False
  if "course_id" not in st.session_state:
    st.session_state.course_id = None
  if "selected_course" not in st.session_state:
    st.session_state.selected_course = None

  # get user_data
  if not st.session_state.init:
    user_data = requests.get(f"{backend_url}/init", params={
      'user_id': st.session_state.user_id
    }).json()
    st.session_state.init = True
    st.session_state.user_data = user_data

  st.header("Course Assistant")

  # Course selection
  courses = {data["name"]: cid for cid, data in st.session_state.user_data.items()}
  selected_course_name = st.selectbox(
      "Select a course",
      options=list(courses.keys()),
      index=0 if not st.session_state.selected_course else list(courses.keys()).index(st.session_state.selected_course)
  )

  # Update session state when course changes
  if selected_course_name != st.session_state.selected_course:
      handle_course_change(selected_course_name, courses[selected_course_name])

  with st.sidebar:
    st.subheader("Your documents")
    show_existing_files()

    st.subheader("Download a module")
    modules = {mdata["name"] : mid for mid, mdata in st.session_state.user_data[st.session_state.course_id]["modules"].items()}
    module_list = ["No module selected"] + list(modules.keys())
    selected_module = st.selectbox("Select a module:", options=list(modules.keys()), index=0 if modules else None)
    
    #uploaded_docs = st.file_uploader("Or upload your PDFs here and click on 'Process'", accept_multiple_files=True)
    
    if st.button("Process"):  
      with st.spinner("Processing"): 

        if selected_module != "No module selected":
          module_id = modules[selected_module]
          download_module(module_id)

        # Ingest uploaded files 
        # if uploaded_docs and len(uploaded_docs) > 0:
        #   requests.post(f"{backend_url}/files/ingest_uploaded_files", params={
        #     'docs': uploaded_docs,
        #     'user_id': st.session_state.user_id,
        #     'selected_course_id': st.session_state.course_id
        #   })
    
        st.session_state.processed = True

  # Always create a new conversation chain when the page loads
  if not st.session_state.processed:
    st.info("Please download some documents first!")

  show_conversation()

if __name__ == '__main__':
  main()