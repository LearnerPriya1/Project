from fastapi import FastAPI, Request, Form, Depends, HTTPException, status
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles 
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm 
from jose import JWTError,jwt
from passlib.context import CryptContext 
from pymongo import MongoClient 
from pymongo.errors import PyMongoError
from pydantic import BaseModel, Field 
from typing import Optional
from datetime import datetime, timedelta, date
import logging
import os
from dotenv import load_dotenv


load_dotenv()

# JWT settings
SECRET_KEY = os.getenv("SECRET_KEY")  # Replace with a secure random key
ALGORITHM = os.getenv("ALGORITHM")
ACCESS_TOKEN_EXPIRE_MINUTES =int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES"))


# Initialize FastAPI app and templates
app = FastAPI()
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

# MongoDB connection
client = MongoClient("mongodb+srv://enukolupriyanka:PriyankaE@empdetails.amw7vfl.mongodb.net/")
db = client.SCMXpertLite
users_collection = db.users

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth2 scheme
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# Pydantic models
class UserInDB(BaseModel):
    username: str
    hashed_password: str
    email: str
    role: str  # Add role field

class Shipment(BaseModel):
    shipment_no: str = Field(..., alias="Shipment-no")
    container_no: str = Field(..., alias="Container-no")
    route_details: str = Field(..., alias="Route-details")
    goods_type: str = Field(..., alias="Goods-type")
    device: str= Field(..., alias="Device")
    expected_delivery_date: date= Field(..., alias="Expected-delivery-date")
    po_number: str = Field(..., alias="PO-number")
    delivery_number: str = Field(..., alias="Delivery-number")
    ndc_number: str = Field(..., alias="NDC-number")
    batch_id: str = Field(..., alias="Batch-id")
    serial_number_of_goods: str = Field(..., alias="Serial-number-of-goods")
    shipment_description: str = Field(..., alias="Shipment-description")

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None

# Utility functions
def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def get_user(username: str, users_collection):
    try:
        user = users_collection.find_one({"username": username})
        if user:
            logging.info(f"User '{username}' found: {user}")
        else:
            logging.warning(f"User '{username}' not found.")
        return user  # Return the user document found
    except PyMongoError as e:
        logging.error(f"PyMongoError fetching user '{username}' from MongoDB: {e}")
        return None
    
def authenticate_user(username: str, password: str):
    user = get_user(username, users_collection)
    if user and verify_password(password, user['hashed_password']):
        return user
    return None

async def get_current_user_from_cookie(request: Request) -> dict:
    COOKIE_NAME = "access_token"
    token = request.cookies.get(COOKIE_NAME)
    user_data = await decode_token(token)
    if user_data is None:
        return None
    return user_data

async def decode_token(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        role: str = payload.get("role")
        if username is None :
            raise credentials_exception
        token_data = TokenData(username=username)
    except JWTError as e:
        logging.error(f"JWT decoding error: {e}")
        raise credentials_exception
    user = get_user(username=token_data.username, users_collection=users_collection)
    logging.info(user)
    logging.debug(f"User details from database: {user}")  # Add this line for debugging

    if user is None :
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
    return user

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

@app.get("/", response_class=HTMLResponse)
async def login_get(request: Request):
    return templates.TemplateResponse("SignIn.html", {"request": request})

@app.post("/login")
async def login(request: Request, form_data: OAuth2PasswordRequestForm = Depends()):
    try:
        user = authenticate_user(form_data.username, form_data.password)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password",
                headers={"WWW-Authenticate": "Bearer"},
            )

        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(data={"sub": user["username"], "email": user["email"], "role": user["role"]}, expires_delta=access_token_expires)
        
        response = RedirectResponse(url=f"/dashboard_", status_code=status.HTTP_303_SEE_OTHER)
        response.set_cookie(key="access_token", value=access_token, httponly=True)
        logging.info(f"Cookie Set: {response.headers.get('set-cookie')}")  # Debugging statement

        return response

    except HTTPException as e:
        error_message = e.detail
        logging.error(f"HTTPException in login: {error_message}")
    except Exception as e:
        error_message = "An error occurred while processing your request."
        logging.error(f"Error in login: {str(e)}")

    return templates.TemplateResponse("SignIn.html", {"request": request, "error_message": error_message})

@app.get("/sign_up", response_class=HTMLResponse)
async def register_get(request: Request):
    return templates.TemplateResponse("SignUp.html", {"request": request})

@app.post("/register")
async def register(request: Request, username: str = Form(...), password: str = Form(...), email: str = Form(...)):
    try:
        form_data = await request.form()
        logging.info(f"Form Data Received: {form_data}")

        # Check if user or email already exists
        if users_collection.find_one({"username": username}) or users_collection.find_one({"email": email}):
            message = "Username or email already exists"
            return templates.TemplateResponse("SignUp.html", {"request": request, "message": message})

        hashed_password = get_password_hash(password)
        # Set the role to "user" by default
        role = "user"
        user = {"username": username, "hashed_password": hashed_password, "email": email, "role": role}
        users_collection.insert_one(user)
        success_message = "Account Created Successfully"
        return templates.TemplateResponse("SignIn.html", {"request": request, "success_message": success_message})

    except PyMongoError as e:
        logging.error(f"PyMongoError registering user '{username}': {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to register user")

@app.get("/dashboard_", response_class=HTMLResponse)
async def dashboard(request: Request):
    return templates.TemplateResponse("dashboard.html", {"request": request})

@app.get("/myAccount", response_class=HTMLResponse)
async def my_account(request: Request,current_user: dict = Depends(get_current_user_from_cookie)):
    if current_user:
        return templates.TemplateResponse("MyAccount.html", {"request": request, "user": current_user})
    else:
        return templates.TemplateResponse("MyAccount.html", {"request": request, "error_message": "User not found"})


@app.get("/shipments", response_class=HTMLResponse)
async def get_shipments(request: Request, user: dict = Depends(get_current_user_from_cookie)):
    try:
        shipments_collection = db.shipments
        current_user_role = user.get("role")
        
        if current_user_role == "admin":
            # Admins can see all shipments
            shipments = list(shipments_collection.find({}))
        else:
            # Users can see only shipments created by users
            shipments = list(shipments_collection.find({"role": "user"}))

        # Ensure dates are converted to string format for display
        for shipment in shipments:
            if "expected_delivery_date" in shipment:
                shipment["expected_delivery_date"] = shipment["expected_delivery_date"].strftime("%Y-%m-%d")

        return templates.TemplateResponse("shipments.html", {"request": request, "shipments": shipments})
    except Exception as e:
        logging.error(f"Error fetching shipments: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to fetch shipments")

@app.get("/newshipment", response_class=HTMLResponse)
async def newshipment(request: Request):
    return templates.TemplateResponse("NewShipment.html", {"request": request})

@app.post("/newshipment")
async def create_shipment(
    request: Request,
    user: dict =Depends(get_current_user_from_cookie),
    Shipment_no: str = Form(...),
    Container_no: str = Form(...),
    Route_details: str = Form(...),
    Goods_type: str = Form(...),
    Device: str = Form(...),
    Expected_delivery_date: date = Form(...),
    PO_number: str = Form(...),
    Delivery_number: str = Form(...),
    NDC_number: str = Form(...),
    Batch_id: str = Form(...),
    Serial_number_of_goods: str = Form(...),
    Shipment_description: str = Form(...)

):
    try:
        # Convert Expected_delivery_date to datetime.datetime
        expected_delivery_datetime = datetime.combine(Expected_delivery_date, datetime.min.time())

        shipment_data = {
            "shipment_no": Shipment_no,
            "container_no": Container_no,
            "route_details": Route_details,
            "goods_type": Goods_type,
            "device": Device,
            "expected_delivery_date": expected_delivery_datetime,
            "po_number": PO_number,
            "delivery_number": Delivery_number,
            "ndc_number": NDC_number,
            "batch_id": Batch_id,
            "serial_number_of_goods": Serial_number_of_goods,
            "shipment_description": Shipment_description,
            "username": user["username"],
            "role": user["role"]
        }

        # Optionally log received data for debugging purposes
        logging.info(f"Received shipment data: {shipment_data}")

        # Continue with your processing logic, e.g., saving to MongoDB
        shipments_collection = db.shipments
        shipments_collection.insert_one(shipment_data)
        successmsg = "New shipment has been successfully created"

        return templates.TemplateResponse("NewShipment.html", {"request": request, "successmsg": successmsg})
    
    except Exception as e:
        logging.error(f"Error processing shipment creation: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to create shipment")
    
@app.get("/device_data")
async def device_data(request: Request, current_user: dict = Depends(get_current_user_from_cookie)):
    # Ensure current_user role is 'admin' to access this endpoint
    if current_user["role"] != "admin":
        return templates.TemplateResponse("forbidden.html", {"request":request})
    
    return templates.TemplateResponse("deviceData.html", {"request": request})

@app.get("/logout", response_class=HTMLResponse)
def logout():
    # Clear session data or cookies
    # For demo, just redirect to login page
    return RedirectResponse(url="/", headers={"Set-Cookie": "session_token=; Path=/; Max-Age=0"})