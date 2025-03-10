# app/api/__init__.py
from .auth import router as auth_router
from .product import router as product_router

__all__ = ["auth_router","product_router"]