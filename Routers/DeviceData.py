from http import client
from fastapi import Query, Request, Depends, APIRouter
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse
from pymongo import MongoClient 
import os
from dotenv import load_dotenv
from Routers.User import get_current_user


load_dotenv()

# Initialize FastAPI app and templates
devicedata=APIRouter()
templates = Jinja2Templates(directory="templates")


# MongoDB connection
client=MongoClient(os.getenv("MongoClient"))
database = client[os.getenv("Mongodb")]
device_collection = database[os.getenv("DEVICE_COLLECTION")]

@devicedata.get("/device_data")
def get_device_data(
    request: Request,
    current_user: dict = Depends(get_current_user),
    current_page: int = Query(1, alias="page"),
    page_size: int = Query(10, alias="page_size"),
    Device_ID: str = Query(None, alias="Device_ID")  ):
    # Redirect to logout if user is not authenticated
    if not current_user:
        return RedirectResponse(url="/logout")
 
    # Restrict access to only admin and super admin roles
    if current_user["role"] not in ["admin", "super admin"]:
        return templates.TemplateResponse("forbidden.html", {"request": request})
 
    # Construct the filter criteria
    filter_criteria = {}
    if Device_ID:
        filter_criteria["Device_ID"] = int(Device_ID)  

    # Calculate total items and pages
    total_items = device_collection.count_documents(filter_criteria)
    total_pages = (total_items + page_size - 1) // page_size
    page_skips = page_size * (current_page - 1)
   
    # Fetch filtered data from the collection
    device_data = list(device_collection.find(filter_criteria, {"_id": 0}).skip(page_skips).limit(page_size))
   
    # Render the template with data and parameters
    return templates.TemplateResponse("deviceData.html", {
        "request": request,
        "data": device_data,
        "current_page": current_page,
        "page_size": page_size,
        "total_pages": total_pages,
        "selected_device_id": Device_ID  
    })
