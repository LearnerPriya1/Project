from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles 
from fastapi import FastAPI
from Routers.User import user
from Routers.Shipments import shipment
from Routers.MyAccount import myaccount
from Routers.DeviceData import devicedata


# Initialize FastAPI app and templates
app = FastAPI()
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")


app.include_router(user)
app.include_router(shipment)
app.include_router(myaccount)
app.include_router(devicedata)

