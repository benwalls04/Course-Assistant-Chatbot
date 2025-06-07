from fastapi import APIRouter
from services.canvas import CanvasService

router = APIRouter()
canvas_service = CanvasService()

@router.get("")
def get_courses():

  response = canvas_service.get_courses()

  courses = []
  for course in response:
    if "name" in course:
      courses.append({
        "id": course["id"],
        "name": canvas_service.get_course_name(course["name"])
      })

  return courses

@router.get("/modules")
def get_modules(course_id):

  response = canvas_service.get_modules(course_id)
  modules = []

  for module in response.json():
    modules.append({
      "id": module["id"],
      "name": module["name"]
    })

  return modules

@router.get("/items")
def get_module_items(course_id, module_id):
    
    response = canvas_service.get_module_items(course_id, module_id)
    
    if response.status_code == 200:
        # Filter for only file items
        items = response.json()
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

