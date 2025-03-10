from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session, joinedload
from app.schemas.auth import UserCreate, UserLogin, RoleUpgradeRequest, RefreshTokenRequest
from app.core.auth_utils import create_access_token, get_password_hash, verify_password, create_refresh_token
from app.core.db import get_db
from app.models.user import User, RoleUpgradeRequestTable
from app.core.dependencies import get_current_user
from jose import JWTError, jwt
from app.core.config import settings

router = APIRouter()


@router.post("/register")
def register(user: UserCreate, db: Session = Depends(get_db)):
    try:
        db_user = db.query(User).filter(User.username == user.username).first()
        if db_user:
            raise HTTPException(
                status_code=400, detail="Username already registered")

        hashed_password = get_password_hash(user.password)
        new_user = User(username=user.username, 
                        hashed_password=hashed_password, 
                        email=user.email, 
                        phone_number=user.phone_number, 
                        name=user.name, 
                        org_name=user.org_name)
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        
        if user.role_request and user.role_request in ["organisation", "internal-staff"]:
            role_request = RoleUpgradeRequestTable(
                user_id=new_user.id,
                requested_role=user.role_request,
                internal_role=user.internal_role if user.role_request == "internal-staff" else None
            )
            db.add(role_request)
            db.commit()

        return new_user
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error in Register API: {e}")


@router.post("/login", status_code=status.HTTP_200_OK)
def login(user: UserLogin, db: Session = Depends(get_db)):
    try:
        db_user = db.query(User).filter(User.email == user.email).first()
        if not db_user or not verify_password(user.password, db_user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
        
        access_token = create_access_token({"sub": db_user.username, "role": db_user.role})
        refresh_token = create_refresh_token({"sub": db_user.username})
        
        # Store the refresh token in the database
        db_user.refresh_token = refresh_token
        db.commit()
        
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "role": db_user.role,
            "name": db_user.name
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error in LoginAPI: {e}")


    
@router.post("/refresh", status_code=status.HTTP_200_OK)
def refresh_token(request_data: RefreshTokenRequest, db: Session = Depends(get_db)):
    """
    Refresh the access token using a valid refresh token.
    """
    try:
        # Decode the provided refresh token
        payload = jwt.decode(
            request_data.refresh_token, 
            settings.jwt_secret_key, 
            algorithms=['HS256']
        )
        username: str = payload.get("sub")
        if not username:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, 
                detail="Invalid refresh token"
            )
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, 
            detail="Invalid refresh token"
        )

    db_user = db.query(User).filter(User.username == username).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    # Verify that the refresh token matches the one stored for the user.
    if not db_user.refresh_token or db_user.refresh_token != request_data.refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, 
            detail="Refresh token does not match"
        )

    # Generate new tokens
    new_access_token = create_access_token({"sub": db_user.username, "role": db_user.role})
    new_refresh_token = create_refresh_token({"sub": db_user.username})
    
    # Update the user with the new refresh token (token rotation)
    db_user.refresh_token = new_refresh_token
    db.commit()

    return {
        "access_token": new_access_token,
        "refresh_token": new_refresh_token,
        "role": db_user.role,
        "name": db_user.name
    }
    

@router.get("/get-role")
async def get_user_role(current_user: User = Depends(get_current_user)):
    try:
        return {"role": current_user.role}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error in GETRole API: {e}")

@router.put("/update-role/{username}")
def upgrade_user_role(username: str, role_request: RoleUpgradeRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    try:
        if current_user.role != "superuser":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have the necessary permissions to perform this action"
            )

        user_to_upgrade = db.query(User).filter(User.username == username).first()

        if not user_to_upgrade:
            raise HTTPException(status_code=404, detail="User not found")
        
        if user_to_upgrade.role == role_request.role:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"User is already assigned the role '{role_request.role}'"
            )

        user_to_upgrade.role = role_request.role
        db.commit()
        db.refresh(user_to_upgrade)
        
        return {"message": f"User {username} has been successfully upgraded to '{role_request.role}'."}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error upgrading user role: {e}")
    

@router.get("/role-requests", dependencies=[Depends(get_current_user)])
def get_role_requests(
    status: str = Query("pending", enum=["pending", "approved", "rejected"]), 
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_user)
):
    if current_user.role != "superuser":
        raise HTTPException(status_code=403, detail="Admin access required")

    # Fetch role requests dynamically based on status
    role_requests = (
        db.query(RoleUpgradeRequestTable)
        .options(joinedload(RoleUpgradeRequestTable.user))
        .filter(RoleUpgradeRequestTable.status == status)
        .all()
    )

    # Build response safely with checks for null user
    result = []
    for request in role_requests:
        if request.user:
            result.append({
                "id": request.id,
                "requested_role": request.requested_role,
                "internal_role": request.internal_role,
                "status": request.status,
                "user_id": request.user_id,
                "user": {
                    "username": request.user.username if request.user else "N/A",
                    "email": request.user.email if request.user else "N/A",
                    "name": request.user.name if request.user else "N/A",
                    "phone_number": request.user.phone_number if request.user else "N/A",
                }
            })
    return result

@router.put("/role-requests/{request_id}")
def approve_or_reject_role_request(
    request_id: int, approve: bool, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    if current_user.role != "superuser":
        raise HTTPException(status_code=403, detail="Admin access required")

    role_request = db.query(RoleUpgradeRequestTable).filter(RoleUpgradeRequestTable.id == request_id).first()
    if not role_request:
        raise HTTPException(status_code=404, detail="Role request not found")

    user = db.query(User).filter(User.id == role_request.user_id).first()
    if approve:
        user.role = role_request.requested_role
        role_request.status = "approved"
    else:
        role_request.status = "rejected"

    db.commit()
    return {"message": f"Role request {'approved' if approve else 'rejected'} successfully"}


@router.get("/role-requests/search", dependencies=[Depends(get_current_user)])
def search_role_requests(
    search: str = Query(..., title="Search Term", description="Search by name, email, or phone number"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Search role requests based on user name, email, or phone number.
    """
    if current_user.role != "superuser":
        raise HTTPException(status_code=403, detail="Admin access required")

    # Join User and RoleUpgradeRequestTable for search
    query = (
        db.query(RoleUpgradeRequestTable)
        .join(User)
        .options(joinedload(RoleUpgradeRequestTable.user))
        .filter(
            (User.name.ilike(f"%{search}%")) | 
            (User.email.ilike(f"%{search}%")) |
            (User.phone_number.ilike(f"%{search}%"))  # Filter by phone number
        )
    )

    role_requests = query.all()

    # Build response safely
    result = []
    for request in role_requests:
        if request.user:
            result.append({
                "id": request.id,
                "requested_role": request.requested_role,
                "internal_role": request.internal_role,
                "status": request.status,
                "user_id": request.user_id,
                "user": {
                    "username": request.user.username if request.user else "N/A",
                    "email": request.user.email if request.user else "N/A",
                    "name": request.user.name if request.user else "N/A",
                    "phone_number": request.user.phone_number if request.user else "N/A",
                }
            })
    return result