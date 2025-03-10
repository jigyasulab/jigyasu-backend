from pydantic import BaseModel
from typing import List
from uuid import UUID

class CartItem(BaseModel):
    uuid: UUID
    activity_name: str
    quantity: int

class CartItemsRequest(BaseModel):
    items: List[CartItem]