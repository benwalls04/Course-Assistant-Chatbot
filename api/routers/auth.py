from fastapi import APIRouter
router = APIRouter()

@router.post("/signup")
async def signup(username, email, password, password_confirmation):
  pass

@router.post("/login")
async def login(username, password):
  pass

@router.post("/logout")
async def logout():
  pass

@router.post("/forgot-password")
async def forgot_password(email):
  pass

@router.post("/reset-password")
async def reset_password(email, password, password_confirmation):
  pass

@router.post("/verify-email")
async def verify_email(email, token):
  pass
