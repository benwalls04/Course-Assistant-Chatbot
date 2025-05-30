from fastapi import APIRouter
import requests
from services.canvas import CanvasService
from dotenv import load_dotenv
import os

router = APIRouter()

@router.get("/courses")
def get_courses():
  canvas_service = CanvasService()
  CANVAS_API_KEY = os.getenv("CANVAS_API_KEY")
  CANVAS_API_URL = os.getenv("CANVAS_API_URL")

  headers = {
    "Authorization": f"Bearer {CANVAS_API_KEY}"
  }
  response = requests.get(f"{CANVAS_API_URL}/courses", headers=headers)

  courses = []
  for course in response.json():
    if "name" in course:
      courses.append({
        "id": course["id"],
        "name": canvas_service.get_course_name(course["name"])
      })
  return courses

@router.get("/courses/{course_id}/modules")
def get_modules(course_id):

  load_dotenv()

  CANVAS_API_KEY = os.getenv("CANVAS_API_KEY")
  CANVAS_API_URL = os.getenv("CANVAS_API_URL")

  headers = {
    "Authorization": f"Bearer {CANVAS_API_KEY}"
  }
  response = requests.get(f"{CANVAS_API_URL}/courses/{course_id}/modules", headers=headers)

  modules = []

  for module in response.json():
    modules.append({
      "id": module["id"],
      "name": module["name"]
    })

  return modules

@router.get("/courses/{course_id}/modules/{module_id}/items")
def get_module_items(course_id, module_id):

    load_dotenv()

    canvas_api_key = os.getenv("CANVAS_API_KEY")
    canvas_api_url = os.getenv("CANVAS_API_URL")

    canvas_service = CanvasService()
  
    headers = {
        "Authorization": f"Bearer {canvas_api_key}"
    }
    
    response = requests.get(
        f"{canvas_api_url}/courses/{course_id}/modules/{module_id}/items", 
        headers=headers
    )
    
    if response.status_code == 200:
        items = response.json()
        
        # Filter for only file items
        file_items = [item for item in items if item.get('type') == 'File']
        
        if not file_items:
            return f"No files found in module {module_id}"
            
        # Get file details for each file item
        file_details = []
        for file_item in file_items:
            res = canvas_service.get_file_details(file_item['content_id'])
            if res:
                file_details.append(res)
        
        return file_details
        
    elif response.status_code == 404:
        return f"Module not found. Please check if the module ID {module_id} is correct."
    elif response.status_code == 401:
        return "Authentication failed. Please check your API key."
    else:
        return f"Error fetching module items: {response.status_code}"

