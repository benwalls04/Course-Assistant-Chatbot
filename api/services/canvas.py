import requests
from dotenv import load_dotenv
import os

class CanvasService:
  def __init__(self):
    load_dotenv()
    self.CANVAS_API_KEY = os.getenv("CANVAS_API_KEY")
    self.CANVAS_API_URL = os.getenv("CANVAS_API_URL")
    self.headers = {
      "Authorization": f"Bearer {self.CANVAS_API_KEY}"
    }

  def get_course_name(self, original_course_name):
    if "-" in original_course_name and "(" in original_course_name:
        name_parts = original_course_name.split("-", 1)
        course_name = name_parts[1].split("(")[0]
        return course_name
    else: 
      return original_course_name

  def get_file_details(self, file_id):

    headers = {
      "Authorization": f"Bearer {self.CANVAS_API_KEY}"
    }

    file_response = requests.get(
        f"{self.CANVAS_API_URL}/files/{file_id}",
        headers=headers
    )
    
    if file_response.status_code == 200:
        file_data = file_response.json()
        return {
            'id': file_id,
            'name': file_data['display_name'],
            'url': file_data['url'],
            'content_type': file_data['content-type']
        }
    else:
        return None

  def get_courses(self):
    response = requests.get(f"{self.CANVAS_API_URL}/courses", headers=self.headers)
    return response.json()

  def get_modules(self, course_id):
    response = requests.get(f"{self.CANVAS_API_URL}/courses/{course_id}/modules", headers=self.headers)
    return response.json()

  def get_module_items(self, course_id, module_id):
    response = requests.get(
        f"{self.CANVAS_API_URL}/courses/{course_id}/modules/{module_id}/items",
        headers=self.headers
    )

    return response
    
    
