from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.router import *

app = FastAPI(title="Perp connect - partial backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Declare Routers
app.include_router(tokens.router)

