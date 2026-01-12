# Course Chatbot

A conversational AI assistant that helps students interact with their course materials from Canvas LMS. The application integrates with Canvas to fetch course documents, processes them using RAG (Retrieval Augmented Generation), and provides an intelligent chat interface for answering questions about course content.

## What It Does

This project enables students to:
- **Connect to Canvas LMS** - Fetch courses, modules, and downloadable files from their Canvas account
- **Ingest Course Materials** - Automatically download and process PDF files from Canvas modules
- **Chat with Course Content** - Ask questions about course materials and get AI-powered answers based on the actual documents
- **Maintain Conversation Context** - Each user has isolated chat histories per course, stored persistently

## Tech Stack

### Backend
- **FastAPI** - Modern Python web framework for the REST API
- **LangChain** - Framework for building LLM applications with RAG capabilities
- **OpenAI GPT-3.5-turbo** - Large language model for generating responses
- **ChromaDB** - Vector database for storing and retrieving document embeddings
- **HuggingFace Embeddings** - `sentence-transformers/all-MiniLM-L6-v2` for text embeddings
- **Redis** - In-memory data store for chat history and session management
- **PyPDF2** - PDF text extraction and processing
- **Mangum** - ASGI adapter for deploying FastAPI to AWS Lambda

### Frontend
- **Streamlit** - Python-based web application framework for the user interface

### Integrations
- **Canvas LMS API** - Integration for fetching courses, modules, and files

## Architecture

The application follows a modular architecture with clear separation of concerns:

```
┌─────────────────┐
│  Streamlit UI   │  (Frontend)
└────────┬────────┘
         │ HTTP Requests
         ▼
┌─────────────────┐
│   FastAPI API   │  (Backend)
│  ┌───────────┐  │
│  │  Routers  │  │  - /files (document ingestion)
│  │           │  │  - /courses (Canvas integration)
│  │           │  │  - /chat (conversational AI)
│  │           │  │  - /auth (authentication)
│  └─────┬─────┘  │
│        │        │
│  ┌─────▼─────┐  │
│  │ Services  │  │
│  │           │  │  - VectorStoreService
│  │           │  │  - CanvasService
│  │           │  │  - TextService
│  └─────┬─────┘  │
└────────┼────────┘
         │
    ┌────┴────┬──────────┬──────────┐
    ▼         ▼          ▼          ▼
┌────────┐ ┌──────┐ ┌─────────┐ ┌──────────┐
│ChromaDB│ │Redis │ │ Canvas  │ │  OpenAI  │
│        │ │      │ │   API   │ │   API    │
└────────┘ └──────┘ └─────────┘ └──────────┘
```

### Key Components

1. **API Routers** (`api/routers/`)
   - Handle HTTP requests and route to appropriate services
   - Manage request/response validation with Pydantic models

2. **Services Layer** (`api/services/`)
   - **VectorStoreService**: Manages ChromaDB collections (one per user), creates conversation chains with LangChain
   - **CanvasService**: Interfaces with Canvas LMS API to fetch courses, modules, and files
   - **TextService**: Extracts text from PDFs and splits into chunks for embedding
   - **Redis Client**: Stores chat history and file metadata

3. **Vector Database**
   - ChromaDB stores document embeddings with metadata (user_id, course_id, file_name)
   - Each user has their own collection for data isolation
   - Documents are filtered by course_id during retrieval

4. **Conversation Management**
   - Chat history stored in Redis with keys: `{user_id}-{course_id}-chat`
   - LangChain's ConversationBufferMemory maintains context within a session
   - ConversationalRetrievalChain combines retrieval and conversation

## How It's Used

### Setup

1. **Install Dependencies**
   ```bash
   cd api
   pip install -r requirements.txt
   ```

2. **Environment Variables**
   Create a `.env` file in the `api/` directory with:
   ```
   CANVAS_API_KEY=your_canvas_api_key
   CANVAS_API_URL=your_canvas_instance_url
   OPENAI_API_KEY=your_openai_api_key
   REDIS_URL=redis://localhost:6379
   ```

3. **Start Services**
   - Start Redis server
   - Start the FastAPI backend:
     ```bash
     cd api
     uvicorn main:app --reload
     ```
   - Start the Streamlit frontend:
     ```bash
     cd chatbot
     streamlit run app.py
     ```

### Usage Flow

1. **Access the Application**
   - Open the Streamlit app (typically at `http://localhost:8501`)

2. **Select a Course**
   - The app fetches your Canvas courses on initialization
   - Select a course from the dropdown

3. **Download Course Materials**
   - In the sidebar, select a module from the course
   - Click "Process" to download and ingest PDF files from that module
   - Files are automatically processed, chunked, and stored in the vector database

4. **Chat with Your Documents**
   - Once documents are processed, you can ask questions in the chat interface
   - The AI retrieves relevant context from your course documents and generates answers
   - Chat history is maintained per course and persists across sessions

### API Endpoints

- `GET /init` - Initialize user data (courses and modules)
- `GET /courses` - Fetch all courses
- `GET /courses/modules` - Get modules for a course
- `GET /courses/items` - Get files from a module
- `POST /files/ingest_canvas_files` - Process and store Canvas files
- `GET /files` - List stored files for a user/course
- `GET /chat` - Retrieve chat history
- `POST /chat/query` - Send a question and get an AI response

## Deployment

The application is containerized with Docker and can be deployed to AWS Lambda using the Mangum adapter. The Dockerfile in `api/Dockerfile` sets up the backend service.

## Notes

- Authentication endpoints (`/auth/*`) are currently placeholders and not implemented
- The application uses per-user vector collections for data isolation
- Chat history is stored in Redis and should be configured for persistence if needed
- Currently supports PDF files only from Canvas modules

