import random
from fastapi import APIRouter, Depends, HTTPException, status, Request, Query
from typing import List
from app.models.user import User
from app.core.dependencies import get_current_user
from app.schemas.cart import CartItem
from app.models.cart import CartSubmission
from sqlalchemy.orm import Session
from app.core.db import get_db
from app.core.emailer import send_email
from pydantic import BaseModel
import json
import requests
from app.core.config import settings

PRICING_WEBHOOK_URL = settings.pricing_webhook_url

router = APIRouter()

class QuotePriceRequest(BaseModel):
    quoted_price: float

@router.post("/submit-cart")
async def submit_cart(cart_items: List[CartItem], request: Request, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    try:
        serialized_cart_items = [{
            "uuid": str(item.uuid),
            "activity_name": item.activity_name,
            "quantity": item.quantity
        } for item in cart_items]
        
        cart_submission = CartSubmission(user_id=user.id, status="pending", cart_items=serialized_cart_items)
        db.add(cart_submission)
        db.commit()
        db.refresh(cart_submission)
        
        subject = "Cart Submission Confirmation - Jigyasu"
        content = f"Hello {user.name},\n\nYour cart has been successfully submitted. We are processing it now.\n\nThank you!"
        send_email(user.email, subject, content)

        return {"message": "Cart submitted successfully", "items_received": len(cart_items), "status": cart_submission.status}
    
    except Exception as e:
        print(f"Error processing the cart: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to process cart")
    
@router.get("/cart-submissions")
async def get_cart_submissions(
    status: str = Query(None, description="Filter cart submissions by status"),  # Optional query param
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Ensure only superusers can access the resource
    if user.role != "superuser":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to access this resource"
        )

    try:
        # Base query with LEFT JOIN to include all CartSubmission rows
        query = db.query(
            CartSubmission.id,
            CartSubmission.user_id,
            CartSubmission.status,
            CartSubmission.cart_items,
            CartSubmission.created_at,
            User.username,
            User.email,
            User.name,
            User.phone_number,
            User.org_name
        ).join(User, CartSubmission.user_id == User.id)

        # Apply status filter if provided
        if status:
            query = query.filter(CartSubmission.status == status)

        # Execute the query
        cart_submissions = query.all()
        print(f"Fetched rows: {cart_submissions}")  # Debugging purposes

        # Serialize the data
        serialized_data = [
            {
                "id": submission.id,
                "status": submission.status,
                "cart_items" : submission.cart_items,
                "created_at": submission.created_at,
                "user": {
                    "email": submission.email if submission.email else None,
                    "name": submission.name if submission.name else None,
                    "phone_number": submission.phone_number if submission.phone_number else None,
                    "org_name" : submission.org_name if submission.org_name else None
                }
            }
            for submission in cart_submissions
        ]

        return {"cart_submissions": serialized_data}

    except Exception as e:
        print(f"Error fetching cart submissions: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch cart submissions")
    
@router.get("/calculate-price/{cart_submission_id}")
async def calculate_cart_price(cart_submission_id: int,direct_factor: float,indirect_factor: float,db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if user.role != "superuser":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to access this resource"
        )
    try:
        cart_submission = db.query(CartSubmission).filter(CartSubmission.id == cart_submission_id).first()
        
        if not cart_submission:
            raise HTTPException(status_code=404, detail="Cart submission not found")

        serialized_cart_items = cart_submission.cart_items
        
        headers = {
            "Content-Type": "application/json"
        }
        
        response = requests.post(
            f"{PRICING_WEBHOOK_URL}?direct_factor={direct_factor}&indirect_factor={indirect_factor}",
            headers=headers,
            json=serialized_cart_items  # Use the `json` parameter to send JSON
        )
        
        if response.status_code != 200:
            raise HTTPException(status_code=500, detail="Pricing service failed")
        
        data = response.json()
        
        # Return response with total price and components
        return {
            "cart_submission_id": cart_submission_id,
            "total_price": data.get("final", 0),
            "components": data.get("components", [])
        }

    except Exception as e:
        print(f"Error calculating price: {e}")
        raise HTTPException(status_code=500, detail="Failed to calculate cart price")

@router.post("/quote-price/{cart_submission_id}")
async def quote_price(cart_submission_id: int,request: QuotePriceRequest, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if user.role != "superuser":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You do not have permission to quote prices.")
    try:
        cart_submission = db.query(CartSubmission).filter(CartSubmission.id == cart_submission_id).first()
        user = db.query(User).filter(User.id == cart_submission.user_id).first()
        
        if not cart_submission or not user:
            raise HTTPException(status_code=404, detail="Cart submission or user not found")
        
        subject = "Your Cart Quote"
        content = f"Hello {user.name},\n\nYour cart has been reviewed. The quoted price for your cart is ${request.quoted_price}.\n\nThank you for your patience!"
        
        send_email(user.email, subject, content)
        cart_submission.status = "replied"
        db.commit()
        
        return {"message": "Quoted price sent to the user via email", "quoted_price": request.quoted_price}
    
    except Exception as e:
        print(f"Error quoting price: {e}")
        raise HTTPException(status_code=500, detail="Failed to quote price")
    