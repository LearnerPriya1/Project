from http import client
from fastapi import APIRouter, Request, Form, Depends, HTTPException, status
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse
from pymongo import MongoClient 
import logging
import os
from dotenv import load_dotenv
from Models.models import Shipment
from Routers.User import get_current_user

load_dotenv()
shipment=APIRouter()
templates = Jinja2Templates(directory="templates")

client=MongoClient(os.getenv("MongoClient"))
database = client[os.getenv("Mongodb")]
shipments_collection=database[os.getenv("SHIPMENTS_COLLECTION")]

@shipment.get("/shipments", response_class=HTMLResponse)
async def get_shipments(request: Request, query: str = "",user: dict = Depends(get_current_user)):
    if not user:
        return RedirectResponse(url="/logout")
    
    try:
       
        current_user_role = user.get("role")
        username=user.get("username")
        
        if current_user_role == "super admin":
            # Super Admins can see all shipments
            shipments_list = list(shipments_collection.find({}))
        elif current_user_role == "admin":
            # Admins can see shipments created by admin and user
            shipments_list = list(shipments_collection.find({"$or": [{"role": "admin"}, {"role": "user"}]}))
        else:
            # Users can see only shipments created by users
            shipments_list = list(shipments_collection.find({"username":username}))
        if query:
            search_criteria = {"$or": [
                {"username": {"$regex": query, "$options": "i"}},
                {"container_no": {"$regex": query, "$options": "i"}},
                {"route_details": {"$regex": query, "$options": "i"}},
                {"goods_type": {"$regex": query, "$options": "i"}},
                {"device": {"$regex": query, "$options": "i"}},
                {"expected_delivery_date": {"$regex": query, "$options": "i"}},
                {"po_number": {"$regex": query, "$options": "i"}},
                {"delivery_number": {"$regex": query, "$options": "i"}},
                {"ndc_number": {"$regex": query, "$options": "i"}},
                {"batch_id": {"$regex": query, "$options": "i"}},
                {"serial_number_of_goods": {"$regex": query, "$options": "i"}},
                {"shipment_description": {"$regex": query, "$options": "i"}}
            ]}
            shipments_list= list(shipments_collection.find(search_criteria))
            # shipments_list = list(shipments_collection.find())

        return templates.TemplateResponse("shipments.html", {"request": request, "shipments": shipments_list})
    
    except Exception as e:
        logging.error(f"Error fetching shipments: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to fetch shipments")

@shipment.get("/newshipment", response_class=HTMLResponse)
def newshipment(request: Request,user: dict=Depends(get_current_user)):
    if not user:
        return RedirectResponse(url="/logout")
    return templates.TemplateResponse("NewShipment.html", {"request": request})

@shipment.post("/newshipment")
def create_shipment(
    request: Request,
    user: dict =Depends(get_current_user),
    user_role:str=Depends(get_current_user),
    Shipment_no: str = Form(...),
    Container_no: str = Form(...),
    Route_details: str = Form(...),
    Goods_type: str = Form(...),
    Device: str = Form(...),
    Expected_delivery_date: str = Form(...),
    PO_number: str = Form(...),
    Delivery_number: str = Form(...),
    NDC_number: str = Form(...),
    Batch_id: str = Form(...),
    Serial_number_of_goods: str = Form(...),
    Shipment_description: str = Form(...)
):
  
    try:
        # Convert Expected_delivery_date to datetime.datetime
        # expected_delivery_datetime = datetime.combine(Expected_delivery_date, datetime.min.time())
        shipment_data = Shipment(
            username=user.get("username"),
            role=user_role.get("role"),
            shipment_no= Shipment_no,
            container_no= Container_no,
            route_details= Route_details,
            goods_type= Goods_type,
            device= Device,
            expected_delivery_date= Expected_delivery_date,
            po_number= PO_number,
            delivery_number= Delivery_number,
            ndc_number= NDC_number,
            batch_id= Batch_id,
            serial_number_of_goods= Serial_number_of_goods,
            shipment_description= Shipment_description,
        )
        shipment_data=shipment_data.dict()
        duplicate=shipments_collection.find_one({"shipment_no":shipment_data.get("shipment_no")})
        if duplicate:
            message = "Shipment with the same number already exists"
            message_type = "failed"
        else:
            shipments_collection.insert_one(shipment_data)
            message = "New shipment has been successfully created"
            message_type="success"

        return templates.TemplateResponse("NewShipment.html", {"request": request, "message": message, "message_type":message_type})
    
    except Exception as e:
        logging.error(f"Error processing shipment creation: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to create shipment")

