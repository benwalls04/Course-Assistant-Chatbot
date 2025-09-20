from fastapi import FastAPI
from mangum import Mangum
from routers import files, courses, chat, auth
from services.vectorstore_instance import vectorstore_service
from services.redis_client import redis_client
import json

app = FastAPI()

app.include_router(files.router, prefix="/files")
app.include_router(courses.router, prefix="/courses")
app.include_router(chat.router, prefix="/chat")
app.include_router(auth.router, prefix="/auth")


@app.get("/init")
async def init(user_id: str):
  user_data = {}

  all_courses = courses.fetch_courses()
  for c in all_courses:
    cid = c["id"]
    user_data[cid] = {
      "name": c["name"]
    }
    
    modules_obj = {}
    modules = courses.fetch_modules(cid)
    for m in modules: 
      modules_obj[m["id"]] = {
        "name": m["name"],
        "files": None
      }

    user_data[cid]["modules"] = modules_obj

      
  return user_data

handler = Mangum(app)