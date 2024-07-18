from http import client
from fastapi import FastAPI, Query, Request, Form, Depends, HTTPException, status
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
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
from starlette.middleware.base import BaseHTTPMiddleware


load_dotenv()

# JWT settings
SECRET_KEY = os.getenv("SECRET_KEY")  # Replace with a secure random key
ALGORITHM = os.getenv("ALGORITHM")
ACCESS_TOKEN_EXPIRE_MINUTES =int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES"))
MONGO_CLIENT=os.getenv("MongoClient")


# Initialize FastAPI app and templates
app = FastAPI()
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

# MongoDB connection
client=MongoClient(MONGO_CLIENT)
db = client.SCMXpertLite
users_collection = db.users
device_collection = db.device_data

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth2 scheme
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# Pydantic models
class UserInDB(BaseModel):
    username: str
    hashed_password: str
    email: str
    role: str  

class RoleUpdateRequest(BaseModel):
    role: str

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


class TokenData(BaseModel):
    email: Optional[str] = None

# Utility functions
def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def get_user(email: str, users_collection):
    try:
        user = users_collection.find_one({"email": email})
        if user:
            logging.info(f"User '{email}' found: {user}")
        else:
            logging.warning(f"User '{email}' not found.")
        return user  # Return the user document found
    except PyMongoError as e:
        logging.error(f"PyMongoError fetching user '{email}' from MongoDB: {e}")
        return None
    
def authenticate_user(email: str, password: str):
    user = get_user(email, users_collection)
    if user and verify_password(password, user['hashed_password']):
        return user
    return None

def update_user_role(username: str, role: str):
    query = {"username": username}
    update = {"$set": {"role": role}}
    result = users_collection.update_one(query, update)
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="User not found")

# Define a function to delete a user
def delete_user(username: str):
    query = {"username": username}
    users_collection.delete_one(query)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


async def decode_token(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("email")
        token_data = TokenData(email=email)
    except JWTError as e:
        logging.error(f"JWT decoding error: {e}")
        raise credentials_exception
    user = get_user(email=token_data.email, users_collection=users_collection)
    
    if user is None :
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
    return user

async def get_current_user_from_cookie(request: Request) -> dict:
    COOKIE_NAME = "access_token"
    token = request.cookies.get(COOKIE_NAME)
    user_data = await decode_token(token)
    if user_data is None:
        return None
    return user_data

class TokenExpiryMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Paths that require token validation
        protected_paths = ["/dashboard_", "/myAccount", "/shipments", "/newshipment", "/device_data"]
        
        # Check if the request path is in the protected paths
        if any(request.url.path.startswith(path) for path in protected_paths):
            COOKIE_NAME = "access_token"
            token = request.cookies.get(COOKIE_NAME)
            
            if token:
                try:
                    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
                    if datetime.utcnow() > datetime.utcfromtimestamp(payload["exp"]):
                        raise JWTError("Token has expired")
                except JWTError:
                    return RedirectResponse(url="/logout")
        
        response = await call_next(request)
        return response

app.add_middleware(TokenExpiryMiddleware)


@app.get("/", response_class=HTMLResponse)
async def login_get(request: Request):
    return templates.TemplateResponse("SignIn.html", {"request": request})

@app.post("/login")
async def login(request: Request, form_data: OAuth2PasswordRequestForm = Depends()):
    try:
        user = authenticate_user(form_data.email, form_data.password)
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
async def dashboard(request: Request, user: dict=Depends(get_current_user_from_cookie)):
    username=user["username"]
    return templates.TemplateResponse("dashboard.html", {"request": request,"username":username})

@app.get("/myAccount", response_class=HTMLResponse)
async def my_account(request: Request, current_user: dict = Depends(get_current_user_from_cookie)):
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

        # Ensure dates are converted to string format for display, otherwise it will give us date with the timestamp
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

@app.get("/shipments")
async def get_shipments(request: Request, query: str = ""):
    shipments_collection = db.shipments
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
        shipments = list(shipments_collection.find(search_criteria))
    else:
        shipments = list(shipments_collection.find())

    return templates.TemplateResponse("shipments.html", {"request": request, "shipments": shipments})

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

        shipments_collection = db.shipments
        shipments_collection.insert_one(shipment_data)
        successmsg = "New shipment has been successfully created"

        return templates.TemplateResponse("NewShipment.html", {"request": request, "successmsg": successmsg})
    
    except Exception as e:
        logging.error(f"Error processing shipment creation: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to create shipment")
    

@app.get("/device_data")
def read_root(
    request: Request,
    current_user: dict = Depends(get_current_user_from_cookie),
    page: int = Query(1, alias="page"),
    page_size: int = Query(10, alias="page_size")
):
    if current_user["role"] != "admin":
        return templates.TemplateResponse("forbidden.html", {"request": request})

    total_items = device_collection.count_documents({})
    total_pages = (total_items + page_size - 1) // page_size
    skips = page_size * (page - 1)
    
    data = list(device_collection.find({}, {"_id": 0}).skip(skips).limit(page_size))
    
    return templates.TemplateResponse("deviceData.html", {
        "request": request,
        "data": data,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages
    })

@app.get("/logout", response_class=HTMLResponse)
def logout():
    # Clear session data or cookies
    return RedirectResponse(url="/", headers={"Set-Cookie": "session_token=; Path=/; Max-Age=0"})  



# Endpoint to update user role
@app.put("/update-role/{username}")
async def update_user_role_endpoint(username: str, request:RoleUpdateRequest):
    try:
        update_user_role(username, request.role)
        return JSONResponse(content={"message": f"User role updated to {request.role}"})
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Endpoint to delete user
@app.delete("/delete-user/{username}")
async def delete_user_endpoint(username: str):
    try:
        delete_user(username)
        return JSONResponse(content={"message": f"User {username} deleted"})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))