from fastapi import FastAPI
from app.core.db import Base, engine
from app.api import auth,product
from app.core.config import settings
from fastapi.middleware.cors import CORSMiddleware
import os
import uvicorn

Base.metadata.create_all(bind=engine)

app = FastAPI()

origins = [
    "http://localhost:3000",
    "https://jigyasu-frontend.vercel.app",
    "https://www.jigyasu.co.in",
    "https://jigyasu-dev.netlify.app",
    "http://127.0.0.1",
    "*"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins, 
    allow_credentials=True,
    allow_methods=["*"],  
    allow_headers=["*"]
)

app.include_router(auth.router, prefix="/api/auth")
app.include_router(product.router, prefix="/api/cart")

@app.get("/")
def read_root():
    return {"message": "Welcome to the Jigyasu Backend."}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)