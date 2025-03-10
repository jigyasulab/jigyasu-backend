from pydantic import BaseModel
from typing import Optional
class UserCreate(BaseModel):
    username: str
    password: str
    email: str
    phone_number: str
    name: str = "Anonymus User"  
    org_name: Optional[str] = None
    role_request: Optional[str] = None
    internal_role: Optional[str] = None

    class Config:
        # orm_mode = True  # Make sure Pydantic models work well with SQLAlchemy models
        model_config = {
                        "from_attributes": True
                    }

class RoleUpgradeRequest(BaseModel):
    role: str 
class UserLogin(BaseModel):
    email: str
    password: str

class APIKeyResponse(BaseModel):
    api_key: str

class RefreshTokenRequest(BaseModel):
    refresh_token: str