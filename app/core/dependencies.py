from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.db import get_db
from app.models.user import User
from app.core.auth_utils import verify_token
from fastapi.security import OAuth2PasswordBearer
from fastapi import Depends, HTTPException, Header, status

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    payload = verify_token(token)
    if not payload:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    username = payload.get("sub")
    user = db.query(User).filter(User.username == username).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user