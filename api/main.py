from fastapi import FastAPI
from mangum import Mangum
from routers import files, courses, chat, auth
from services.vectorstore_instance import vectorstore_service

app = FastAPI()

app.include_router(files.router, prefix="/files")
app.include_router(courses.router, prefix="/courses")
app.include_router(chat.router, prefix="/chat")
app.include_router(auth.router, prefix="/auth")
handler = Mangum(app)