from http import client
from fastapi import Request, Form, Depends, HTTPException, status, APIRouter
from fastapi.templating import Jinja2Templates
from fastapi.responses import  RedirectResponse, JSONResponse
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm 
from jose import JWTError,jwt
from passlib.context import CryptContext 
from pymongo import MongoClient 
from pymongo.errors import PyMongoError
from typing import Optional
from datetime import datetime, timedelta
import logging
import os
from dotenv import load_dotenv
from Models.models import RoleUpdateRequest, User

load_dotenv()

user=APIRouter()

# ENV settings
SECRET_KEY = os.getenv("SECRET_KEY") 
ALGORITHM = os.getenv("ALGORITHM")
ACCESS_TOKEN_EXPIRE_MINUTES =int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES"))
MONGO_CLIENT=os.getenv("MongoClient")
COOKIE_NAME=os.getenv("COOKIE_NAME")


# Initialize FastAPI app and templates
templates = Jinja2Templates(directory="templates")

# MongoDB connection
client=MongoClient(MONGO_CLIENT)
database = client[os.getenv("Mongodb")]
users_collection = database[os.getenv("USER_COLLECTION")]

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password):
    return pwd_context.hash(password)


def get_user(email: str, users_collection):
    try:
        user = users_collection.find_one({"email": email})
        return user  
    except PyMongoError as e:
        logging.error(f"PyMongoError fetching user '{email}' from MongoDB: {e}")
        return None
    

def authenticate_user(email: str, password: str):
    user = get_user(email, users_collection)
    if user and verify_password(password, user['password']):
        return user
    return None


#function to update user role
def update_user_role(username: str, role: str):
    query = {"username": username}
    update = {"$set": {"role": role}}
    result = users_collection.update_one(query, update)
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="User not found")


#function to delete a user
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


async def decode_token(token: str=Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=ALGORITHM)
        email: str = payload.get("email")
        # token_data = TokenData(email=email)
    except JWTError as e:
        raise credentials_exception
    
    user = get_user(email, users_collection)
    
    if user is None :
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
    return user


async def get_current_user(request: Request) -> dict:
    token = request.cookies.get(COOKIE_NAME)
    if not token:
        return None
    user_data = await decode_token(token)
    return user_data


@user.get("/")
def login_get(request: Request):
    return templates.TemplateResponse("SignIn.html", {"request": request})


@user.post("/token")
def login(request: Request, form_data: OAuth2PasswordRequestForm = Depends()):
    try:
        user = authenticate_user(form_data.username, form_data.password)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect Email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )

        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(data={"sub": user["username"], "email": user["email"], "role": user["role"]}, expires_delta=access_token_expires)
        response = RedirectResponse(url=f"/dashboard_", status_code=status.HTTP_303_SEE_OTHER)
        response.set_cookie(key=COOKIE_NAME, value=access_token, httponly=True)
      
        return response
    except HTTPException as e:
        error_message = e.detail
        logging.error(f"HTTPException in login: {error_message}")

    return templates.TemplateResponse("SignIn.html", {"request": request, "error_message": error_message})


@user.get("/sign_up")
def register_get(request: Request):
    return templates.TemplateResponse("SignUp.html", {"request": request})


@user.post("/sign_up")
def register(request: Request, username: str = Form(...), password: str = Form(...), email: str = Form(...)):
    try:
        
        # Check if user or email already exists
        if users_collection.find_one({"username": username}) and users_collection.find_one({"email": email}):
            message = "Username or email already exists"
            return templates.TemplateResponse("SignUp.html", {"request": request, "message": message})

        hashed_password = get_password_hash(password)
        # Set the role to "user" by default
        user = User(username= username, password= hashed_password, email=email)
        users_collection.insert_one(user.dict())
        success_message = "Account Created Successfully"
        return templates.TemplateResponse("SignIn.html", {"request": request, "success_message": success_message})

    except PyMongoError as e:
        logging.error(f"PyMongoError registering user '{username}': {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to register user")
    
@user.get("/dashboard_")
def dashboard(request: Request, user: dict=Depends(get_current_user)):
    if not user:
        return RedirectResponse(url="/logout")
    username=user["username"]
    return templates.TemplateResponse("dashboard.html", {"request": request,"username":username})


@user.put("/update-role/{username}")
def update_user_role_endpoint(username: str, request:RoleUpdateRequest):
    try:
        update_user_role(username, request.role)
        return JSONResponse(content={"message": f"User role updated to {request.role}"})

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@user.delete("/delete-user/{username}")
def delete_user_endpoint(username: str):
    try:
        delete_user(username)
        return JSONResponse(content={"message": f"User {username} deleted"})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    

@user.get("/logout")
def logout():
    # Clear session data or cookies
    response=RedirectResponse("/") 
    response.delete_cookie(COOKIE_NAME)
    return response