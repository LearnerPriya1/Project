from fastapi import Request, Depends, APIRouter
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from Routers.User import get_current_user
from pymongo import MongoClient 
import os
from dotenv import load_dotenv

myaccount=APIRouter()

load_dotenv()
templates = Jinja2Templates(directory="templates")

# MongoDB connection
client=MongoClient(os.getenv("MongoClient"))
database = client[os.getenv("Mongodb")]
users_collection = database[os.getenv("USER_COLLECTION")]

@myaccount.get("/myAccount", response_class=HTMLResponse)
async def my_account(request: Request, current_user: dict = Depends(get_current_user)):
    if not current_user:
        return RedirectResponse(url="/logout")
    
    users = None
    admins = None

    if current_user["role"] == "super admin":
        users = list(users_collection.find({"role": "user"}))
        admins = list(users_collection.find({"role": "admin"}))
    elif current_user["role"] == "admin":
        users = list(users_collection.find({"role": "user"}))

    return templates.TemplateResponse("MyAccount.html", {
        "request": request,
        "user": current_user,
        "users": users,
        "admins": admins
    })