from pydantic import BaseModel

class RoleUpdateRequest(BaseModel):
    role: str

class User(BaseModel):
    username:str
    email: str
    password: str
    role:str="user"


class Shipment(BaseModel):
    username: str
    role:str
    shipment_no: str 
    container_no: str
    route_details: str 
    goods_type: str 
    device: str
    expected_delivery_date: str
    po_number: str 
    delivery_number: str 
    ndc_number: str 
    batch_id: str 
    serial_number_of_goods: str 
    shipment_description: str 