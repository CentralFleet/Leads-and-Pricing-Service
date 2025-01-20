from pydantic import BaseModel, Field
from typing import Optional


class Order(BaseModel):
    Deal_Name : Optional[str] = None
    Customer_id : Optional[str] = None
    Customer_Name: Optional[str] = None
    Drop_off_Location : Optional[str] = None
    PickupLocation : Optional[str] = None
    Stage : Optional[str] = "Shop for Quotes"
    Order_Status : Optional[str] = "Quote Requested"
    Carrier_Payment_Status	: Optional[str] = "Unpaid"
    Customer_Payment_Status	 : Optional[str] = "Unpaid"
    Name : Optional[str] = None
    Orders : Optional[list] = None
    special_instructon : Optional[str] = None
    Tax_Province : Optional[str] = None



class Clead(BaseModel):
    Carrier_Score	: Optional[str] = None
    Progress_Status : Optional[str] = "To Be Contacted"
    Zoho_Job_ID: Optional[str] = None
    Name : Optional[str] = None
    Pickup_Location : Optional[str] = None
    Dropoff_Location : Optional[str] = None
    Vehicle_Details : Optional[dict] = None
