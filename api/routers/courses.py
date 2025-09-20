from fastapi import APIRouter
from services.canvas import CanvasService

router = APIRouter()
canvas_service = CanvasService()


def fetch_courses():
  response = canvas_service.get_courses()

  courses = []
  for course in response:
    if "name" in course:
      courses.append({
        "id": course["id"],
        "name": canvas_service.get_course_name(course["name"])
      })

  return courses


def fetch_modules(course_id):
  response = canvas_service.get_modules(course_id)
  modules = []

  for module in response:
    modules.append({
      "id": module["id"],
      "name": module["name"]
    })

  return modules


@router.get("")
def get_courses():

  return fetch_courses()


@router.get("/modules")
def get_modules(course_id):

  return fetch_modules(course_id)


@router.get("/items")
def get_module_items(course_id, module_id):
    
    response = canvas_service.get_module_items(course_id, module_id)
    
    if response.status_code == 200:
        items = response.json()
        file_items = [item for item in items if item.get('type') == 'File']
        
        if not file_items:
            return []
            
        # Get file details for each file item
        file_details = []
        for file_item in file_items:
            res = canvas_service.get_file_details(file_item['content_id'])
            if res:
                file_details.append(res)
        
        return file_details
    else:
        raise HTTPException(status_code=404, detail= f"Error fetching module items")

