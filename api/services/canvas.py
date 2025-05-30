import requests
from dotenv import load_dotenv
import os

class CanvasService:
  def __init__(self):
    pass

  def get_course_name(self, original_course_name):
    if "-" in original_course_name and "(" in original_course_name:
        name_parts = original_course_name.split("-", 1)
        course_name = name_parts[1].split("(")[0]
        return course_name
    else: 
      return original_course_name

  def get_file_details(self, file_id):
    CANVAS_API_KEY = os.getenv("CANVAS_API_KEY")
    CANVAS_API_URL = os.getenv("CANVAS_API_URL")

    headers = {
      "Authorization": f"Bearer {CANVAS_API_KEY}"
    }

    file_response = requests.get(
        f"{CANVAS_API_URL}/files/{file_id}",
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
