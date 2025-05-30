from fastapi import FastAPI
from mangum import Mangum
from api.routers import files, courses, chat, auth

app = FastAPI()
app.include_router(files.router, prefix="/files")
app.include_router(courses.router, prefix="/courses")
app.include_router(chat.router, prefix="/chat")
app.include_router(auth.router, prefix="/auth")
handler = Mangum(app)